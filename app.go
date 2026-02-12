package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"

	"justfit/internal/analyzer"
	"justfit/internal/connector"
	"justfit/internal/etl"
	"justfit/internal/report"
	"justfit/internal/security"
	"justfit/internal/service"
	"justfit/internal/storage"
	"justfit/internal/task"
)

// App 应用主结构
type App struct {
	ctx           context.Context
	connMgr       *connector.ConnectorManager
	repos         *storage.Repositories
	collector     *etl.Collector
	analyzer      *analyzer.Engine
	credentialMgr *security.CredentialManager
	resultStorage *analyzer.ResultStorage
	taskScheduler *task.Scheduler
	taskLogger    *task.Logger
}

// NewApp 创建新的应用实例
func NewApp() *App {
	return &App{}
}

// startup 应用启动时调用
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx

	// 初始化数据库
	if err := storage.Init(&storage.Config{}); err != nil {
		fmt.Printf("FATAL: 初始化数据库失败: %v\n", err)
		// 在实际生产环境中，这里应该记录日志并可能退出，或者在前端显示错误
		// 为防止 panic，这里我们尽量保证 a.repos 不为空，或者后续操作检查 Connection
	}

	// 创建连接器管理器
	a.connMgr = connector.NewConnectorManager()

	// 创建数据仓储
	// 注意: 如果 DB 初始化失败，NewRepositories 内可能会 panic 或者创建不可用的 repo
	// 更好的做法是在 NewRepositories 内部处理 nil DB
	a.repos = storage.NewRepositories()

	// 创建采集器
	a.collector = etl.NewCollector(a.connMgr, a.repos)

	// 创建分析引擎
	a.analyzer = analyzer.NewEngine(a.repos)

	// 创建凭据管理器
	credMgr, err := security.NewCredentialManager("")
	if err != nil {
		fmt.Printf("ERROR: 创建凭据管理器失败: %v. 密码加密功能将不可用。\n", err)
		// 我们可以创建一个内存版的或者空的 manager，或者在 CreateConnection 时处理 nil
	}
	a.credentialMgr = credMgr

	// 创建结果存储服务
	a.resultStorage = analyzer.NewResultStorage(a.repos)

	// 创建任务日志记录器
	logDir := filepath.Join(os.Getenv("HOME"), ".justfit", "logs")
	taskLogger, err := task.NewLogger(logDir, 1000)
	if err != nil {
		fmt.Printf("WARNING: 创建任务日志记录器失败: %v，使用临时目录\n", err)
		taskLogger, _ = task.NewLogger(os.TempDir(), 100)
	}
	a.taskLogger = taskLogger

	// 创建任务调度器
	a.taskScheduler = task.NewScheduler(3) // 3个worker

	// 注册任务执行器
	collectionExecutor := service.NewCollectionExecutor(a.collector, a.repos)
	analysisExecutor := service.NewAnalysisExecutor(a.analyzer, a.repos)

	a.taskScheduler.RegisterExecutor(task.TypeCollection, collectionExecutor)
	a.taskScheduler.RegisterExecutor(task.TypeAnalysis, analysisExecutor)
}

// shutdown 应用关闭时调用
func (a *App) shutdown(ctx context.Context) {
	// 关闭任务调度器
	if a.taskScheduler != nil {
		_ = a.taskScheduler.Shutdown(5 * time.Second)
	}

	// 关闭所有连接
	if a.connMgr != nil {
		a.connMgr.CloseAll()
	}

	// 关闭数据库
	storage.Close()
}

// GetDashboardStats 获取仪表盘数据
type DashboardStats struct {
	HealthScore  float64 `json:"health_score"`
	ZombieCount  int64   `json:"zombie_count"`
	TotalSavings string  `json:"total_savings"` // 字符串展示，如 "¥12,400/月"
	TotalVMs     int64   `json:"total_vms"`
}

func (a *App) GetDashboardStats() (*DashboardStats, error) {
	// 1. 获取所有连接的 VM 总数
	var totalVMs int64
	// a.repos.VM.Count() 需要自己实现或者直接用 GORM
	if err := storage.DB.Model(&storage.VM{}).Count(&totalVMs).Error; err != nil {
		fmt.Printf("GetDashboardStats error counting VMs: %v\n", err)
	}

	// 2. 获取最新的健康评分 (取最近一条)
	var latestHealth storage.AnalysisResult
	var healthScore float64 = 0 // 默认 0

	// 从 AnalysisResult 表中查找 type=health_score 的最新记录
	err := storage.DB.Where("analysis_type = ?", "health_score").Order("created_at desc").First(&latestHealth).Error
	if err == nil {
		// 解析 Data 字段
		var healthData HealthScoreResult
		if json.Unmarshal([]byte(latestHealth.Data), &healthData) == nil {
			healthScore = healthData.OverallScore
		}
	} else {
		// 如果没有分析过，返回 0 或者默认值
		healthScore = 0
	}

	// 3. 统计僵尸 VM 数量 (这里简单统计最近一次分析的结果)
	// 在实际场景中，可能需要关联到最近的一次 Report。
	// 这里简化：统计所有未解决的 'zombie_vm' 类型的 Alert，或者 AnalysisResult 中去重
	var zombieCount int64
	// 统计 Alert 中类型为 zombie_vm 且未确认的
	// 或者统计最近 7 天生成的 analysis result
	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "zombie_vm", time.Now().AddDate(0, 0, -7)).
		Count(&zombieCount)

	// 4. 计算节省
	// 基于配置的每单位资源成本进行估算，这里简化为固定成本
	var monthlySaving float64 = 0
	if zombieCount > 0 {
		// 估算：假设每个僵尸 VM 平均浪费 2 vCPU + 4GB 内存
		// 假设 vCPU 的月成本为 50 元，1GB 内存月成本为 20 元
		// 则单台 VM 节省 = 2*50 + 4*20 = 180 元
		monthlySaving = float64(zombieCount) * 180
	}

	savings := fmt.Sprintf("¥%.0f/月", monthlySaving)

	return &DashboardStats{
		HealthScore:  healthScore,
		ZombieCount:  zombieCount,
		TotalSavings: savings,
		TotalVMs:     totalVMs,
	}, nil
}


// ========== 连接管理服务 ==========

// ConnectionInfo 连接信息（不包含密码）
type ConnectionInfo struct {
	ID       uint   `json:"id"`
	Name     string `json:"name"`
	Platform string `json:"platform"`
	Host     string `json:"host"`
	Port     int    `json:"port"`
	Username string `json:"username"`
	Insecure bool   `json:"insecure"`
	Status   string `json:"status"`
	LastSync string `json:"last_sync"`
}

// CreateConnectionRequest 创建连接请求
type CreateConnectionRequest struct {
	Name     string `json:"name"`
	Platform string `json:"platform"`
	Host     string `json:"host"`
	Port     int    `json:"port"`
	Username string `json:"username"`
	Password string `json:"password"`
	Insecure bool   `json:"insecure"`
}

// CreateConnection 创建连接
func (a *App) CreateConnection(req CreateConnectionRequest) (uint, error) {
	// 安全检查：如果凭据管理器不可用，不允许创建连接，防止密码以此明文存储
	if a.credentialMgr == nil {
		return 0, fmt.Errorf("安全服务未初始化，无法安全保存凭据")
	}

	conn := &storage.Connection{
		Name:     req.Name,
		Platform: req.Platform,
		Host:     req.Host,
		Port:     req.Port,
		Username: req.Username,
		Password: "", // 关键修复：数据库中不存储明文密码，保持为空
		Insecure: req.Insecure,
		Status:   "disconnected",
	}

	// 暂存明文密码用于加密服务
	plainPassword := req.Password

	// 1. 创建连接记录 (密码为空)
	if err := a.repos.Connection.Create(conn); err != nil {
		return 0, fmt.Errorf("创建连接失败: %w", err)
	}

	// 构造用于加密的临时对象（带有 ID 和明文密码）
	connForEncryption := *conn
	connForEncryption.Password = plainPassword

	// 2. 保存到凭据管理器（加密）
	if err := a.credentialMgr.SaveConnection(&connForEncryption); err != nil {
		// 加密失败，物理删除已创建的连接
		a.repos.Connection.Delete(conn.ID)
		return 0, fmt.Errorf("保存凭据失败(加密服务): %w", err)
	}

	// 3. 内存中也确保不残留
	plainPassword = ""
	connForEncryption.Password = ""

	return conn.ID, nil
}

// ListConnections 获取连接列表
func (a *App) ListConnections() ([]ConnectionInfo, error) {
	conns, err := a.repos.Connection.List()
	if err != nil {
		return nil, fmt.Errorf("获取连接列表失败: %w", err)
	}

	result := make([]ConnectionInfo, len(conns))
	for i, c := range conns {
		result[i] = ConnectionInfo{
			ID:       c.ID,
			Name:     c.Name,
			Platform: c.Platform,
			Host:     c.Host,
			Port:     c.Port,
			Username: c.Username,
			Insecure: c.Insecure,
			Status:   c.Status,
		}
		if c.LastSync != nil {
			result[i].LastSync = c.LastSync.Format("2006-01-02 15:04:05")
		}
	}

	return result, nil
}

// TestConnection 测试连接
func (a *App) TestConnection(id uint) (string, error) {
	conn, err := a.repos.Connection.GetByID(id)
	if err != nil {
		return "", fmt.Errorf("获取连接失败: %w", err)
	}

	// 从凭据管理器加载密码
	if a.credentialMgr != nil {
		if err := a.credentialMgr.LoadConnection(conn); err != nil {
			return "", fmt.Errorf("加载凭据失败: %w", err)
		}
	}

	config := &connector.ConnectionConfig{
		ID:       conn.ID,
		Name:     conn.Name,
		Platform: connector.PlatformType(conn.Platform),
		Host:     conn.Host,
		Port:     conn.Port,
		Username: conn.Username,
		Password: conn.Password,
		Insecure: conn.Insecure,
	}

	client, err := connector.NewConnector(config)
	if err != nil {
		a.repos.Connection.UpdateStatus(id, "error")
		return "", fmt.Errorf("创建连接失败: %w", err)
	}
	defer client.Close()

	if err := client.TestConnection(); err != nil {
		a.repos.Connection.UpdateStatus(id, "error")
		return "", fmt.Errorf("连接测试失败: %w", err)
	}

	a.repos.Connection.UpdateStatus(id, "connected")
	return "connected", nil
}

// DeleteConnection 删除连接
func (a *App) DeleteConnection(id uint) error {
	// 移除连接器
	a.connMgr.Remove(id)

	// 删除数据库记录
	if err := a.repos.Connection.Delete(id); err != nil {
		return fmt.Errorf("删除连接失败: %w", err)
	}

	return nil
}

// GetConnection 获取单个连接详情
func (a *App) GetConnection(id uint) (*ConnectionInfo, error) {
	conn, err := a.repos.Connection.GetByID(id)
	if err != nil {
		return nil, fmt.Errorf("获取连接失败: %w", err)
	}

	result := &ConnectionInfo{
		ID:       conn.ID,
		Name:     conn.Name,
		Platform: conn.Platform,
		Host:     conn.Host,
		Port:     conn.Port,
		Username: conn.Username,
		Insecure: conn.Insecure,
		Status:   conn.Status,
	}
	if conn.LastSync != nil {
		result.LastSync = conn.LastSync.Format("2006-01-02 15:04:05")
	}

	return result, nil
}

// UpdateConnectionRequest 更新连接请求
type UpdateConnectionRequest struct {
	ID       uint   `json:"id"`
	Name     string `json:"name"`
	Platform string `json:"platform"`
	Host     string `json:"host"`
	Port     int    `json:"port"`
	Username string `json:"username"`
	Password string `json:"password"` // 可选，为空则不更新
	Insecure bool   `json:"insecure"`
}

// UpdateConnection 更新连接
func (a *App) UpdateConnection(req UpdateConnectionRequest) error {
	conn, err := a.repos.Connection.GetByID(req.ID)
	if err != nil {
		return fmt.Errorf("获取连接失败: %w", err)
	}

	// 更新字段
	conn.Name = req.Name
	conn.Platform = req.Platform
	conn.Host = req.Host
	conn.Port = req.Port
	conn.Username = req.Username
	conn.Insecure = req.Insecure

	// 如果提供了新密码，更新凭据
	if req.Password != "" && a.credentialMgr != nil {
		conn.Password = req.Password // 临时设置用于加密
		if err := a.credentialMgr.SaveConnection(conn); err != nil {
			return fmt.Errorf("更新凭据失败: %w", err)
		}
		conn.Password = "" // 清除明文
	}

	// 更新数据库
	if err := a.repos.Connection.Update(conn); err != nil {
		return fmt.Errorf("更新连接失败: %w", err)
	}

	// 移除内存中的连接缓存，下次使用时重新建立
	a.connMgr.Remove(req.ID)

	return nil
}

// ========== 数据采集服务 ==========

// CollectionConfig 采集配置
type CollectionConfig struct {
	ConnectionID uint     `json:"connection_id"`
	DataTypes    []string `json:"data_types"` // clusters, hosts, vms, metrics
	MetricsDays  int      `json:"metrics_days"`
}

// CollectionResult 采集结果
type CollectionResult struct {
	Success  bool   `json:"success"`
	Message  string `json:"message"`
	Clusters int    `json:"clusters"`
	Hosts    int    `json:"hosts"`
	VMs      int    `json:"vms"`
	Metrics  int    `json:"metrics"`
	Duration int64  `json:"duration"` // 毫秒
}

// CollectData 采集数据
func (a *App) CollectData(config CollectionConfig) (*CollectionResult, error) {
	// 尝试加载连接凭据(密码)
	var password string
	if a.credentialMgr != nil {
		conn, err := a.repos.Connection.GetByID(config.ConnectionID)
		if err == nil {
			a.credentialMgr.LoadConnection(conn)
			password = conn.Password
		}
	}

	collectConfig := &etl.CollectionConfig{
		ConnectionID: config.ConnectionID,
		DataTypes:    config.DataTypes,
		MetricsDays:  config.MetricsDays,
		Concurrency:  3,
		Password:     password,
	}

	result, err := a.collector.Collect(a.ctx, collectConfig)
	if err != nil {
		return nil, err
	}

	// 如果需要采集性能指标
	metricCount := 0
	if contains(config.DataTypes, "metrics") && config.MetricsDays > 0 {
		// 采集性能指标
		metricCount, err = a.collector.CollectMetrics(a.ctx, config.ConnectionID, config.MetricsDays, password)
		if err != nil {
			// 性能指标采集失败不影响基础数据采集结果
			fmt.Printf("采集性能指标失败: %v\n", err)
		}
	}

	return &CollectionResult{
		Success:  result.Success,
		Message:  result.Message,
		Clusters: result.Clusters,
		Hosts:    result.Hosts,
		VMs:      result.VMs,
		Metrics:  metricCount,
		Duration: result.Duration.Milliseconds(),
	}, nil
}

// contains 检查字符串切片是否包含指定元素
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// ========== 采集任务管理 ==========

// TaskInfo 任务信息
type TaskInfo struct {
	ID          uint    `json:"id"`
	Type        string  `json:"type"`
	Name        string  `json:"name"`
	Status      string  `json:"status"`
	Progress    float64 `json:"progress"`
	Error       string  `json:"error,omitempty"`
	CreatedAt   string  `json:"created_at"`
	StartedAt   *string `json:"started_at,omitempty"`
	CompletedAt *string `json:"completed_at,omitempty"`
}

// CreateCollectTask 创建采集任务
func (a *App) CreateCollectTask(config CollectionConfig) (uint, error) {
	// 尝试加载连接凭据(密码)
	var password string
	if a.credentialMgr != nil {
		conn, err := a.repos.Connection.GetByID(config.ConnectionID)
		if err == nil {
			a.credentialMgr.LoadConnection(conn)
			password = conn.Password
		}
	}

	taskConfig := map[string]interface{}{
		"connection_id": config.ConnectionID,
		"data_types":    config.DataTypes,
		"metrics_days":  config.MetricsDays,
		"password":      password,
	}

	taskName := fmt.Sprintf("采集任务 - 连接ID: %d", config.ConnectionID)
	t, err := a.taskScheduler.Create(task.TypeCollection, taskName, taskConfig)
	if err != nil {
		return 0, fmt.Errorf("创建任务失败: %w", err)
	}

	// 提交执行
	go func() {
		_ = a.taskScheduler.Submit(a.ctx, t.ID)
	}()

	return t.ID, nil
}

// ListTasks 获取任务列表
func (a *App) ListTasks(status string, limit, offset int) ([]TaskInfo, error) {
	var taskStatus task.TaskStatus
	if status != "" {
		taskStatus = task.TaskStatus(status)
	}

	tasks, err := a.taskScheduler.List(taskStatus, limit, offset)
	if err != nil {
		return nil, err
	}

	result := make([]TaskInfo, len(tasks))
	for i, t := range tasks {
		result[i] = TaskInfo{
			ID:        t.ID,
			Type:      string(t.Type),
			Name:      t.Name,
			Status:    string(t.Status),
			Progress:  t.Progress,
			Error:     t.Error,
			CreatedAt: t.CreatedAt.Format("2006-01-02 15:04:05"),
		}
		if t.StartedAt != nil {
			s := t.StartedAt.Format("2006-01-02 15:04:05")
			result[i].StartedAt = &s
		}
		if t.CompletedAt != nil {
			c := t.CompletedAt.Format("2006-01-02 15:04:05")
			result[i].CompletedAt = &c
		}
	}

	return result, nil
}

// GetTask 获取任务详情
func (a *App) GetTask(id uint) (*TaskInfo, error) {
	t, err := a.taskScheduler.Get(id)
	if err != nil {
		return nil, err
	}

	result := &TaskInfo{
		ID:        t.ID,
		Type:      string(t.Type),
		Name:      t.Name,
		Status:    string(t.Status),
		Progress:  t.Progress,
		Error:     t.Error,
		CreatedAt: t.CreatedAt.Format("2006-01-02 15:04:05"),
	}
	if t.StartedAt != nil {
		s := t.StartedAt.Format("2006-01-02 15:04:05")
		result.StartedAt = &s
	}
	if t.CompletedAt != nil {
		c := t.CompletedAt.Format("2006-01-02 15:04:05")
		result.CompletedAt = &c
	}

	return result, nil
}

// StopTask 停止任务
func (a *App) StopTask(id uint) error {
	return a.taskScheduler.Cancel(id)
}

// RetryTask 重试任务
func (a *App) RetryTask(id uint) (uint, error) {
	oldTask, err := a.taskScheduler.Get(id)
	if err != nil {
		return 0, err
	}

	// 创建新任务，复制配置
	taskName := oldTask.Name + " (重试)"
	newTask, err := a.taskScheduler.Create(oldTask.Type, taskName, oldTask.Config)
	if err != nil {
		return 0, err
	}

	go func() {
		_ = a.taskScheduler.Submit(a.ctx, newTask.ID)
	}()

	return newTask.ID, nil
}

// TaskLogEntry 任务日志条目
type TaskLogEntry struct {
	Timestamp string `json:"timestamp"`
	Level     string `json:"level"`
	Message   string `json:"message"`
}

// GetTaskLogs 获取任务日志
func (a *App) GetTaskLogs(id uint, limit int) ([]TaskLogEntry, error) {
	if a.taskLogger == nil {
		return []TaskLogEntry{}, nil
	}

	entries := a.taskLogger.GetEntries(id, limit)

	result := make([]TaskLogEntry, len(entries))
	for i, e := range entries {
		result[i] = TaskLogEntry{
			Timestamp: e.Timestamp.Format("2006-01-02 15:04:05"),
			Level:     string(e.Level),
			Message:   e.Message,
		}
	}

	return result, nil
}

// ========== 分析服务 ==========

// ZombieVMConfig 僵尸 VM 检测配置
type ZombieVMConfig struct {
	AnalysisDays    int     `json:"analysis_days"`
	CPUThreshold    float64 `json:"cpu_threshold"`
	MemoryThreshold float64 `json:"memory_threshold"`
	MinConfidence   float64 `json:"min_confidence"`
}

// ZombieVMResult 僵尸 VM 检测结果
type ZombieVMResult struct {
	VMName         string   `json:"vm_name"`
	Datacenter     string   `json:"datacenter"`
	Host           string   `json:"host"`
	CPUCount       int32    `json:"cpu_count"`
	MemoryMB       int32    `json:"memory_mb"`
	CPUUsage       float64  `json:"cpu_usage"`
	MemoryUsage    float64  `json:"memory_usage"`
	Confidence     float64  `json:"confidence"`
	DaysLowUsage   int      `json:"days_low_usage"`
	Evidence       []string `json:"evidence"`
	Recommendation string   `json:"recommendation"`
}

// DetectZombieVMs 检测僵尸虚拟机
func (a *App) DetectZombieVMs(connectionID uint, config ZombieVMConfig) ([]ZombieVMResult, error) {
	zombieConfig := &analyzer.ZombieVMConfig{
		AnalysisDays:    config.AnalysisDays,
		CPUThreshold:    config.CPUThreshold,
		MemoryThreshold: config.MemoryThreshold,
		MinConfidence:   config.MinConfidence,
	}

	if zombieConfig.AnalysisDays == 0 {
		zombieConfig = analyzer.DefaultZombieVMConfig()
	}

	results, err := a.analyzer.DetectZombieVMs(connectionID, zombieConfig)
	if err != nil {
		return nil, fmt.Errorf("检测僵尸 VM 失败: %w", err)
	}

	// 转换结果格式
	output := make([]ZombieVMResult, len(results))
	for i, r := range results {
		output[i] = ZombieVMResult{
			VMName:         r.VMName,
			Datacenter:     r.Datacenter,
			Host:           r.Host,
			CPUCount:       r.CPUCount,
			MemoryMB:       r.MemoryMB,
			CPUUsage:       r.CPUUsage,
			MemoryUsage:    r.MemoryUsage,
			Confidence:     r.Confidence,
			DaysLowUsage:   r.DaysLowUsage,
			Evidence:       r.Evidence,
			Recommendation: r.Recommendation,
		}
	}

	return output, nil
}

// RightSizeConfig Right Size 配置
type RightSizeConfig struct {
	AnalysisDays int     `json:"analysis_days"`
	BufferRatio  float64 `json:"buffer_ratio"`
}

// RightSizeResult Right Size 结果
type RightSizeResult struct {
	VMName              string  `json:"vm_name"`
	Datacenter          string  `json:"datacenter"`
	CurrentCPU          int32   `json:"current_cpu"`
	CurrentMemoryMB     int32   `json:"current_memory_mb"`
	RecommendedCPU      int32   `json:"recommended_cpu"`
	RecommendedMemoryMB int32   `json:"recommended_memory_mb"`
	AdjustmentType      string  `json:"adjustment_type"`
	RiskLevel           string  `json:"risk_level"`
	EstimatedSaving     string  `json:"estimated_saving"`
	Confidence          float64 `json:"confidence"`
}

// AnalyzeRightSize 分析资源配置
func (a *App) AnalyzeRightSize(connectionID uint, config RightSizeConfig) ([]RightSizeResult, error) {
	rightSizeConfig := &analyzer.RightSizeConfig{
		AnalysisDays: config.AnalysisDays,
		BufferRatio:  config.BufferRatio,
	}

	if rightSizeConfig.AnalysisDays == 0 {
		rightSizeConfig = analyzer.DefaultRightSizeConfig()
	}

	results, err := a.analyzer.AnalyzeRightSize(connectionID, rightSizeConfig)
	if err != nil {
		return nil, fmt.Errorf("Right Size 分析失败: %w", err)
	}

	// 转换结果格式
	output := make([]RightSizeResult, len(results))
	for i, r := range results {
		output[i] = RightSizeResult{
			VMName:              r.VMName,
			Datacenter:          r.Datacenter,
			CurrentCPU:          r.CurrentCPU,
			CurrentMemoryMB:     r.CurrentMemoryMB,
			RecommendedCPU:      r.RecommendedCPU,
			RecommendedMemoryMB: r.RecommendedMemoryMB,
			AdjustmentType:      r.AdjustmentType,
			RiskLevel:           r.RiskLevel,
			EstimatedSaving:     r.EstimatedSaving,
			Confidence:          r.Confidence,
		}
	}

	return output, nil
}

// TidalConfig 潮汐检测配置
type TidalConfig struct {
	AnalysisDays int     `json:"analysis_days"`
	MinStability float64 `json:"min_stability"`
}

// TidalResult 潮汐检测结果
type TidalResult struct {
	VMName          string  `json:"vm_name"`
	Datacenter      string  `json:"datacenter"`
	Pattern         string  `json:"pattern"`
	StabilityScore  float64 `json:"stability_score"`
	PeakHours       []int   `json:"peak_hours"`
	PeakDays        []int   `json:"peak_days"`
	Recommendation  string  `json:"recommendation"`
	EstimatedSaving string  `json:"estimated_saving"`
}

// DetectTidalPattern 检测潮汐模式
func (a *App) DetectTidalPattern(connectionID uint, config TidalConfig) ([]TidalResult, error) {
	tidalConfig := &analyzer.TidalConfig{
		AnalysisDays: config.AnalysisDays,
		MinStability: config.MinStability,
	}

	if tidalConfig.AnalysisDays == 0 {
		tidalConfig = analyzer.DefaultTidalConfig()
	}

	results, err := a.analyzer.DetectTidalPattern(connectionID, tidalConfig)
	if err != nil {
		return nil, fmt.Errorf("潮汐检测失败: %w", err)
	}

	// 转换结果格式
	output := make([]TidalResult, len(results))
	for i, r := range results {
		output[i] = TidalResult{
			VMName:          r.VMName,
			Datacenter:      r.Datacenter,
			Pattern:         string(r.Pattern),
			StabilityScore:  r.StabilityScore,
			PeakHours:       r.PeakHours,
			PeakDays:        r.PeakDays,
			Recommendation:  r.Recommendation,
			EstimatedSaving: r.EstimatedSaving,
		}
	}

	return output, nil
}

// HealthScoreResult 健康评分结果
type HealthScoreResult struct {
	ConnectionID         uint     `json:"connection_id"`
	ConnectionName       string   `json:"connection_name"`
	OverallScore         float64  `json:"overall_score"`
	HealthLevel          string   `json:"health_level"`
	ResourceBalance      float64  `json:"resource_balance"`
	OvercommitRisk       float64  `json:"overcommit_risk"`
	HotspotConcentration float64  `json:"hotspot_concentration"`
	TotalClusters        int      `json:"total_clusters"`
	TotalHosts           int      `json:"total_hosts"`
	TotalVMs             int      `json:"total_vms"`
	RiskItems            []string `json:"risk_items"`
	Recommendations      []string `json:"recommendations"`
}

// AnalyzeHealthScore 分析健康度
func (a *App) AnalyzeHealthScore(connectionID uint) (*HealthScoreResult, error) {
	result, err := a.analyzer.AnalyzeHealthScore(connectionID, nil)
	if err != nil {
		return nil, fmt.Errorf("健康度分析失败: %w", err)
	}

	return &HealthScoreResult{
		ConnectionID:         result.ConnectionID,
		ConnectionName:       result.ConnectionName,
		OverallScore:         result.OverallScore,
		HealthLevel:          result.HealthLevel,
		ResourceBalance:      result.ResourceBalance,
		OvercommitRisk:       result.OvercommitRisk,
		HotspotConcentration: result.HotspotConcentration,
		TotalClusters:        result.TotalClusters,
		TotalHosts:           result.TotalHosts,
		TotalVMs:             result.TotalVMs,
		RiskItems:            result.RiskItems,
		Recommendations:      result.Recommendations,
	}, nil
}

// ========== 分析结果存储服务 ==========

// SaveZombieVMResults 保存僵尸 VM 分析结果
func (a *App) SaveZombieVMResults(connectionID uint, results []ZombieVMResult) error {
	if a.resultStorage == nil {
		return fmt.Errorf("结果存储服务未初始化")
	}

	// 转换为内部格式
	internalResults := make([]analyzer.ZombieVMResult, len(results))
	for i, r := range results {
		vmResult := analyzer.VMAnalysisResult{
			VMName:     r.VMName,
			Datacenter: r.Datacenter,
			Host:       r.Host,
			CPUCount:   r.CPUCount,
			MemoryMB:   r.MemoryMB,
		}
		internalResults[i] = analyzer.ZombieVMResult{
			VMAnalysisResult: vmResult,
			CPUUsage:         r.CPUUsage,
			MemoryUsage:      r.MemoryUsage,
			Confidence:       r.Confidence,
			DaysLowUsage:     r.DaysLowUsage,
			Evidence:         r.Evidence,
			Recommendation:   r.Recommendation,
		}
	}

	return a.resultStorage.SaveZombieVMResults(connectionID, internalResults)
}

// SaveRightSizeResults 保存 Right Size 分析结果
func (a *App) SaveRightSizeResults(connectionID uint, results []RightSizeResult) error {
	if a.resultStorage == nil {
		return fmt.Errorf("结果存储服务未初始化")
	}

	// 转换为内部格式
	internalResults := make([]analyzer.RightSizeResult, len(results))
	for i, r := range results {
		vmResult := analyzer.VMAnalysisResult{
			VMName:     r.VMName,
			Datacenter: r.Datacenter,
		}
		internalResults[i] = analyzer.RightSizeResult{
			VMAnalysisResult:    vmResult,
			CurrentCPU:          r.CurrentCPU,
			CurrentMemoryMB:     r.CurrentMemoryMB,
			RecommendedCPU:      r.RecommendedCPU,
			RecommendedMemoryMB: r.RecommendedMemoryMB,
			AdjustmentType:      r.AdjustmentType,
			RiskLevel:           r.RiskLevel,
			EstimatedSaving:     r.EstimatedSaving,
			Confidence:          r.Confidence,
		}
	}

	return a.resultStorage.SaveRightSizeResults(connectionID, internalResults)
}

// SaveTidalResults 保存潮汐分析结果
func (a *App) SaveTidalResults(connectionID uint, results []TidalResult) error {
	if a.resultStorage == nil {
		return fmt.Errorf("结果存储服务未初始化")
	}

	// 转换为内部格式
	internalResults := make([]analyzer.TidalResult, len(results))
	for i, r := range results {
		vmResult := analyzer.VMAnalysisResult{
			VMName:     r.VMName,
			Datacenter: r.Datacenter,
		}
		pattern := analyzer.TidalPattern(r.Pattern)
		internalResults[i] = analyzer.TidalResult{
			VMAnalysisResult: vmResult,
			Pattern:          pattern,
			StabilityScore:   r.StabilityScore,
			PeakHours:        r.PeakHours,
			PeakDays:         r.PeakDays,
			Recommendation:   r.Recommendation,
			EstimatedSaving:  r.EstimatedSaving,
		}
	}

	return a.resultStorage.SaveTidalResults(connectionID, internalResults)
}

// SaveHealthScoreResult 保存健康评分结果
func (a *App) SaveHealthScoreResult(result HealthScoreResult) error {
	if a.resultStorage == nil {
		return fmt.Errorf("结果存储服务未初始化")
	}

	internalResult := analyzer.HealthScoreResult{
		ConnectionID:         result.ConnectionID,
		ConnectionName:       result.ConnectionName,
		OverallScore:         result.OverallScore,
		HealthLevel:          result.HealthLevel,
		ResourceBalance:      result.ResourceBalance,
		OvercommitRisk:       result.OvercommitRisk,
		HotspotConcentration: result.HotspotConcentration,
		TotalClusters:        result.TotalClusters,
		TotalHosts:           result.TotalHosts,
		TotalVMs:             result.TotalVMs,
		RiskItems:            result.RiskItems,
		Recommendations:      result.Recommendations,
	}

	return a.resultStorage.SaveHealthScoreResult(internalResult)
}

// CreateAlert 创建告警
type CreateAlertRequest struct {
	TargetType string `json:"target_type"` // cluster, host, vm
	TargetKey  string `json:"target_key"`
	TargetName string `json:"target_name"`
	AlertType  string `json:"alert_type"` // zombie_vm, overprovisioned, etc.
	Severity   string `json:"severity"`   // info, warning, critical
	Title      string `json:"title"`
	Message    string `json:"message"`
	Data       string `json:"data"` // JSON string
}

// CreateAlert 创建告警
func (a *App) CreateAlert(req CreateAlertRequest) error {
	if a.resultStorage == nil {
		return fmt.Errorf("结果存储服务未初始化")
	}

	var data interface{}
	if req.Data != "" {
		if err := json.Unmarshal([]byte(req.Data), &data); err != nil {
			return fmt.Errorf("解析数据失败: %w", err)
		}
	}

	return a.resultStorage.CreateAlert(
		req.TargetType,
		req.TargetKey,
		req.TargetName,
		req.AlertType,
		req.Severity,
		req.Title,
		req.Message,
		data,
	)
}

// ========== 工具方法 ==========

// GetVMList 获取虚拟机列表
func (a *App) GetVMList(connectionID uint) (string, error) {
	vms, err := a.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return "", fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	data, err := json.Marshal(vms)
	if err != nil {
		return "", fmt.Errorf("序列化失败: %w", err)
	}

	return string(data), nil
}

// GetHostList 获取主机列表
func (a *App) GetHostList(connectionID uint) (string, error) {
	hosts, err := a.repos.Host.ListByConnectionID(connectionID)
	if err != nil {
		return "", fmt.Errorf("获取主机列表失败: %w", err)
	}

	data, err := json.Marshal(hosts)
	if err != nil {
		return "", fmt.Errorf("序列化失败: %w", err)
	}

	return string(data), nil
}

// GetClusterList 获取集群列表
func (a *App) GetClusterList(connectionID uint) (string, error) {
	clusters, err := a.repos.Cluster.ListByConnectionID(connectionID)
	if err != nil {
		return "", fmt.Errorf("获取集群列表失败: %w", err)
	}

	data, err := json.Marshal(clusters)
	if err != nil {
		return "", fmt.Errorf("序列化失败: %w", err)
	}

	return string(data), nil
}

// Greet 返回问候语（保留默认方法）
func (a *App) Greet(name string) string {
	return fmt.Sprintf("Hello %s, It's show time!", name)
}

// ========== 资源查询 API（标准化） ==========

// ClusterListItem 标准化的集群列表项
type ClusterListItem struct {
	ID            uint    `json:"id"`
	Name          string  `json:"name"`
	Datacenter    string  `json:"datacenter"`
	TotalCPU      int64   `json:"total_cpu"`
	TotalMemoryGB float64 `json:"total_memory_gb"`
	NumHosts      int32   `json:"num_hosts"`
	NumVMs        int     `json:"num_vms"`
	Status        string  `json:"status"`
	CollectedAt   string  `json:"collected_at"`
}

// ListClusters 获取集群列表（标准化）
func (a *App) ListClusters(connectionID uint) ([]ClusterListItem, error) {
	clusters, err := a.repos.Cluster.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取集群列表失败: %w", err)
	}

	result := make([]ClusterListItem, len(clusters))
	for i, c := range clusters {
		result[i] = ClusterListItem{
			ID:            c.ID,
			Name:          c.Name,
			Datacenter:    c.Datacenter,
			TotalCPU:      c.TotalCpu,
			TotalMemoryGB: float64(c.TotalMemory) / 1024 / 1024 / 1024,
			NumHosts:      c.NumHosts,
			NumVMs:        c.NumVMs,
			Status:        c.Status,
			CollectedAt:   c.CollectedAt.Format("2006-01-02 15:04:05"),
		}
	}

	return result, nil
}

// HostListItem 标准化的主机列表项
type HostListItem struct {
	ID            uint    `json:"id"`
	Name          string  `json:"name"`
	Datacenter    string  `json:"datacenter"`
	IPAddress     string  `json:"ip_address"`
	CPUCores      int32   `json:"cpu_cores"`
	CPUMHz        int32   `json:"cpu_mhz"`
	MemoryGB      float64 `json:"memory_gb"`
	NumVMs        int     `json:"num_vms"`
	PowerState    string  `json:"power_state"`
	OverallStatus string  `json:"overall_status"`
	CollectedAt   string  `json:"collected_at"`
}

// ListHosts 获取主机列表（标准化）
func (a *App) ListHosts(connectionID uint) ([]HostListItem, error) {
	hosts, err := a.repos.Host.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取主机列表失败: %w", err)
	}

	result := make([]HostListItem, len(hosts))
	for i, h := range hosts {
		result[i] = HostListItem{
			ID:            h.ID,
			Name:          h.Name,
			Datacenter:    h.Datacenter,
			IPAddress:     h.IPAddress,
			CPUCores:      h.CpuCores,
			CPUMHz:        h.CpuMhz,
			MemoryGB:      float64(h.Memory) / 1024 / 1024 / 1024,
			NumVMs:        h.NumVMs,
			PowerState:    h.PowerState,
			OverallStatus: h.OverallStatus,
			CollectedAt:   h.CollectedAt.Format("2006-01-02 15:04:05"),
		}
	}

	return result, nil
}

// VMListItem 标准化的虚拟机列表项
type VMListItem struct {
	ID            uint    `json:"id"`
	Name          string  `json:"name"`
	Datacenter    string  `json:"datacenter"`
	UUID          string  `json:"uuid"`
	CPUCount      int32   `json:"cpu_count"`
	MemoryGB      float64 `json:"memory_gb"`
	PowerState    string  `json:"power_state"`
	IPAddress     string  `json:"ip_address"`
	GuestOS       string  `json:"guest_os"`
	HostName      string  `json:"host_name"`
	OverallStatus string  `json:"overall_status"`
	CollectedAt   string  `json:"collected_at"`
}

// ListVMs 获取虚拟机列表（标准化）
func (a *App) ListVMs(connectionID uint) ([]VMListItem, error) {
	vms, err := a.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	result := make([]VMListItem, len(vms))
	for i, v := range vms {
		result[i] = VMListItem{
			ID:            v.ID,
			Name:          v.Name,
			Datacenter:    v.Datacenter,
			UUID:          v.UUID,
			CPUCount:      v.CpuCount,
			MemoryGB:      float64(v.MemoryMB) / 1024,
			PowerState:    v.PowerState,
			IPAddress:     v.IPAddress,
			GuestOS:       v.GuestOS,
			HostName:      v.HostName,
			OverallStatus: v.OverallStatus,
			CollectedAt:   v.CollectedAt.Format("2006-01-02 15:04:05"),
		}
	}

	return result, nil
}

// MetricPoint 指标数据点
type MetricPoint struct {
	Timestamp int64   `json:"timestamp"`
	Value     float64 `json:"value"`
}

// MetricsData 指标数据
type MetricsData struct {
	VMID       uint          `json:"vm_id"`
	VMName     string        `json:"vm_name"`
	MetricType string        `json:"metric_type"`
	StartTime  string        `json:"start_time"`
	EndTime    string        `json:"end_time"`
	Data       []MetricPoint `json:"data"`
}

// GetMetrics 获取指标数据
func (a *App) GetMetrics(vmID uint, metricType string, days int) (*MetricsData, error) {
	// 获取 VM 信息
	vm, err := a.repos.VM.GetByID(vmID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机失败: %w", err)
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -days)

	metrics, err := a.repos.Metric.ListByVMAndType(vmID, metricType, startTime, endTime)
	if err != nil {
		return nil, fmt.Errorf("获取指标失败: %w", err)
	}

	data := make([]MetricPoint, len(metrics))
	for i, m := range metrics {
		data[i] = MetricPoint{
			Timestamp: m.Timestamp.Unix(),
			Value:     m.Value,
		}
	}

	return &MetricsData{
		VMID:       vmID,
		VMName:     vm.Name,
		MetricType: metricType,
		StartTime:  startTime.Format("2006-01-02 15:04:05"),
		EndTime:    endTime.Format("2006-01-02 15:04:05"),
		Data:       data,
	}, nil
}

// EntityType 实体类型
type EntityType string

const (
	EntityTypeCluster EntityType = "cluster"
	EntityTypeHost    EntityType = "host"
	EntityTypeVM      EntityType = "vm"
)

// EntityDetail 实体详情
type EntityDetail struct {
	Type       EntityType             `json:"type"`
	ID         uint                   `json:"id"`
	Name       string                 `json:"name"`
	Attributes map[string]interface{} `json:"attributes"`
}

// GetEntityDetail 获取实体详情
func (a *App) GetEntityDetail(entityType EntityType, id uint) (*EntityDetail, error) {
	detail := &EntityDetail{Type: entityType, ID: id}

	switch entityType {
	case EntityTypeCluster:
		clusters, err := a.repos.Cluster.ListByConnectionID(0)
		if err != nil {
			return nil, err
		}
		var cluster *storage.Cluster
		for i := range clusters {
			if clusters[i].ID == id {
				cluster = &clusters[i]
				break
			}
		}
		if cluster == nil {
			return nil, fmt.Errorf("集群不存在")
		}
		detail.Name = cluster.Name
		detail.Attributes = map[string]interface{}{
			"datacenter":   cluster.Datacenter,
			"total_cpu":    cluster.TotalCpu,
			"total_memory": cluster.TotalMemory,
			"num_hosts":    cluster.NumHosts,
			"num_vms":      cluster.NumVMs,
			"status":       cluster.Status,
			"collected_at": cluster.CollectedAt.Format("2006-01-02 15:04:05"),
		}

	case EntityTypeHost:
		hosts, err := a.repos.Host.ListByConnectionID(0)
		if err != nil {
			return nil, err
		}
		var host *storage.Host
		for i := range hosts {
			if hosts[i].ID == id {
				host = &hosts[i]
				break
			}
		}
		if host == nil {
			return nil, fmt.Errorf("主机不存在")
		}
		detail.Name = host.Name
		detail.Attributes = map[string]interface{}{
			"datacenter":       host.Datacenter,
			"ip_address":       host.IPAddress,
			"cpu_cores":        host.CpuCores,
			"cpu_mhz":          host.CpuMhz,
			"memory":           host.Memory,
			"num_vms":          host.NumVMs,
			"connection_state": host.ConnectionState,
			"power_state":      host.PowerState,
			"overall_status":   host.OverallStatus,
		}

	case EntityTypeVM:
		vm, err := a.repos.VM.GetByID(id)
		if err != nil {
			return nil, err
		}
		detail.Name = vm.Name
		detail.Attributes = map[string]interface{}{
			"datacenter":     vm.Datacenter,
			"uuid":           vm.UUID,
			"cpu_count":      vm.CpuCount,
			"memory_mb":      vm.MemoryMB,
			"power_state":    vm.PowerState,
			"ip_address":     vm.IPAddress,
			"guest_os":       vm.GuestOS,
			"host_name":      vm.HostName,
			"overall_status": vm.OverallStatus,
		}
	}

	return detail, nil
}

// ========== 报告服务 ==========

// ReportRequest 报告生成请求
type ReportRequest struct {
	Title        string   `json:"title"`
	ConnectionID uint     `json:"connection_id"`
	ReportTypes  []string `json:"report_types"` // json, html
}

// ReportResponse 报告生成响应
type ReportResponse struct {
	Success bool     `json:"success"`
	Message string   `json:"message"`
	Files   []string `json:"files"` // 生成的文件路径
}

// GenerateReport 生成报告
func (a *App) GenerateReport(req ReportRequest) (*ReportResponse, error) {
	if len(req.ReportTypes) == 0 {
		req.ReportTypes = []string{"json"}
	}

	var generatedFiles []string

	for _, reportType := range req.ReportTypes {
		var generator *report.Generator

		switch reportType {
		case "json":
			generator = report.NewGenerator(&report.ReportConfig{
				Type:      report.ReportTypeJSON,
				OutputDir: os.TempDir(),
			})
		case "html":
			generator = report.NewGenerator(&report.ReportConfig{
				Type:      report.ReportTypeHTML,
				OutputDir: os.TempDir(),
			})
		default:
			continue
		}

		// 构建报告数据
		reportData := &report.ReportData{
			Title:        req.Title,
			ConnectionID: req.ConnectionID,
			Metadata:     make(map[string]interface{}),
			Sections:     buildReportSections(req.ConnectionID),
		}

		filepath, err := generator.Generate(reportData)
		if err != nil {
			return &ReportResponse{
				Success: false,
				Message: fmt.Sprintf("生成 %s 报告失败: %v", reportType, err),
			}, nil
		}

		generatedFiles = append(generatedFiles, filepath)
	}

	return &ReportResponse{
		Success: true,
		Message: "报告生成成功",
		Files:   generatedFiles,
	}, nil
}

// buildReportSections 构建报告章节
func buildReportSections(connectionID uint) []report.ReportSection {
	// TODO: 从数据库获取实际数据构建报告章节
	return []report.ReportSection{
		{
			Title:   "概述",
			Content: "本报告由 JustFit 云平台资源评估工具自动生成",
			Type:    "text",
		},
		{
			Title: "数据汇总",
			Type:  "summary",
			Data: map[string]interface{}{
				"total_vms":   0,
				"total_hosts": 0,
			},
		},
	}
}

// ========== 分析服务（统一入口） ==========

// AnalysisRequest 分析请求
type AnalysisRequest struct {
	ConnectionID  uint                   `json:"connection_id"`
	AnalysisTypes []string               `json:"analysis_types"` // zombie_vm, right_size, tidal, health_score
	Config        map[string]interface{} `json:"config"`
}

// AnalysisResponse 分析响应
type AnalysisResponse struct {
	TaskID  uint                   `json:"task_id"`
	Status  string                 `json:"status"`
	Results map[string]interface{} `json:"results,omitempty"`
}

// RunAnalysis 统一分析入口（同步执行）
func (a *App) RunAnalysis(req AnalysisRequest) (*AnalysisResponse, error) {
	connectionID := req.ConnectionID
	results := make(map[string]interface{})

	for _, analysisType := range req.AnalysisTypes {
		switch analysisType {
		case "zombie_vm":
			config := parseZombieVMConfigFromMap(req.Config)
			result, err := a.DetectZombieVMs(connectionID, config)
			if err != nil {
				return nil, fmt.Errorf("僵尸 VM 检测失败: %w", err)
			}
			results["zombie_vm"] = result

		case "right_size":
			config := parseRightSizeConfigFromMap(req.Config)
			result, err := a.AnalyzeRightSize(connectionID, config)
			if err != nil {
				return nil, fmt.Errorf("Right Size 分析失败: %w", err)
			}
			results["right_size"] = result

		case "tidal":
			config := parseTidalConfigFromMap(req.Config)
			result, err := a.DetectTidalPattern(connectionID, config)
			if err != nil {
				return nil, fmt.Errorf("潮汐检测失败: %w", err)
			}
			results["tidal"] = result

		case "health_score":
			result, err := a.AnalyzeHealthScore(connectionID)
			if err != nil {
				return nil, fmt.Errorf("健康度分析失败: %w", err)
			}
			results["health_score"] = result
		}
	}

	return &AnalysisResponse{
		Status:  "completed",
		Results: results,
	}, nil
}

// 辅助解析函数
func parseZombieVMConfigFromMap(config map[string]interface{}) ZombieVMConfig {
	result := ZombieVMConfig{}
	if v, ok := config["analysis_days"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["cpu_threshold"].(float64); ok {
		result.CPUThreshold = v
	}
	if v, ok := config["memory_threshold"].(float64); ok {
		result.MemoryThreshold = v
	}
	if v, ok := config["min_confidence"].(float64); ok {
		result.MinConfidence = v
	}
	return result
}

func parseRightSizeConfigFromMap(config map[string]interface{}) RightSizeConfig {
	result := RightSizeConfig{}
	if v, ok := config["analysis_days"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["buffer_ratio"].(float64); ok {
		result.BufferRatio = v
	}
	return result
}

func parseTidalConfigFromMap(config map[string]interface{}) TidalConfig {
	result := TidalConfig{}
	if v, ok := config["analysis_days"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["min_stability"].(float64); ok {
		result.MinStability = v
	}
	return result
}

// GetAnalysisResult 获取分析结果
func (a *App) GetAnalysisResult(resultID uint) (map[string]interface{}, error) {
	var analysisResult storage.AnalysisResult
	err := storage.DB.First(&analysisResult, resultID).Error
	if err != nil {
		return nil, fmt.Errorf("获取分析结果失败: %w", err)
	}

	var data map[string]interface{}
	if analysisResult.Data != "" {
		if err := json.Unmarshal([]byte(analysisResult.Data), &data); err != nil {
			return nil, fmt.Errorf("解析结果数据失败: %w", err)
		}
	}

	return map[string]interface{}{
		"id":             analysisResult.ID,
		"analysis_type":  analysisResult.AnalysisType,
		"target_type":    analysisResult.TargetType,
		"target_key":     analysisResult.TargetKey,
		"target_name":    analysisResult.TargetName,
		"data":           data,
		"recommendation": analysisResult.Recommendation,
		"saved_amount":   analysisResult.SavedAmount,
		"created_at":     analysisResult.CreatedAt.Format("2006-01-02 15:04:05"),
	}, nil
}

// AnalysisSummary 分析汇总
type AnalysisSummary struct {
	ConnectionID     uint            `json:"connection_id"`
	TotalVMs         int64           `json:"total_vms"`
	ZombieVMs        int             `json:"zombie_vms"`
	RightSizeVMs     int             `json:"right_size_vms"`
	TidalVMs         int             `json:"tidal_vms"`
	HealthScore      float64         `json:"health_score"`
	TotalSavings     string          `json:"total_savings"`
	LastAnalyzed     string          `json:"last_analyzed"`
	RiskDistribution map[string]int  `json:"risk_distribution"`
}

// GetAnalysisSummary 获取分析汇总
func (a *App) GetAnalysisSummary(connectionID uint) (*AnalysisSummary, error) {
	// 获取 VM 总数
	var totalVMs int64
	storage.DB.Model(&storage.VM{}).Where("connection_id = ?", connectionID).Count(&totalVMs)

	// 统计各类分析结果
	var zombieCount, rightSizeCount, tidalCount int64
	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "zombie_vm", time.Now().AddDate(0, 0, -7)).
		Count(&zombieCount)

	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "right_size", time.Now().AddDate(0, 0, -7)).
		Count(&rightSizeCount)

	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "tidal", time.Now().AddDate(0, 0, -7)).
		Count(&tidalCount)

	// 获取最新健康评分
	var latestHealth storage.AnalysisResult
	var healthScore float64 = 0
	storage.DB.Where("analysis_type = ? AND created_at > ?", "health_score", time.Now().AddDate(0, 0, -30)).
		Order("created_at desc").First(&latestHealth)

	if latestHealth.ID > 0 {
		var healthData HealthScoreResult
		if json.Unmarshal([]byte(latestHealth.Data), &healthData) == nil {
			healthScore = healthData.OverallScore
		}
	}

	// 估算总节省
	totalSavings := fmt.Sprintf("约 %.0f 元/月", float64(zombieCount)*180)

	return &AnalysisSummary{
		ConnectionID:     connectionID,
		TotalVMs:         totalVMs,
		ZombieVMs:        int(zombieCount),
		RightSizeVMs:     int(rightSizeCount),
		TidalVMs:         int(tidalCount),
		HealthScore:      healthScore,
		TotalSavings:     totalSavings,
		LastAnalyzed:     latestHealth.CreatedAt.Format("2006-01-02 15:04:05"),
		RiskDistribution: map[string]int{
			"high":   int(zombieCount),
			"medium": int(rightSizeCount),
			"low":    int(totalVMs - zombieCount - rightSizeCount),
		},
	}, nil
}

// ========== 报告服务扩展 ==========

// ReportListItem 报告列表项
type ReportListItem struct {
	ID           uint   `json:"id"`
	Type         string `json:"type"`
	Name         string `json:"name"`
	ConnectionID uint   `json:"connection_id"`
	Status       string `json:"status"`
	Format       string `json:"format"`
	FilePath     string `json:"file_path"`
	FileSize     int64  `json:"file_size"`
	CreatedAt    string `json:"created_at"`
}

// ListReports 获取报告列表
func (a *App) ListReports(limit, offset int) ([]ReportListItem, error) {
	reports, err := a.repos.Report.List(limit, offset)
	if err != nil {
		return nil, fmt.Errorf("获取报告列表失败: %w", err)
	}

	result := make([]ReportListItem, len(reports))
	for i, r := range reports {
		result[i] = ReportListItem{
			ID:           r.ID,
			Type:         r.Type,
			Name:         r.Name,
			ConnectionID: r.ConnectionID,
			Status:       r.Status,
			Format:       r.Format,
			FilePath:     r.FilePath,
			FileSize:     r.FileSize,
			CreatedAt:    r.CreatedAt.Format("2006-01-02 15:04:05"),
		}
	}

	return result, nil
}

// ReportDetail 报告详情
type ReportDetail struct {
	ID           uint                   `json:"id"`
	Type         string                 `json:"type"`
	Name         string                 `json:"name"`
	ConnectionID uint                   `json:"connection_id"`
	Status       string                 `json:"status"`
	Format       string                 `json:"format"`
	FilePath     string                 `json:"file_path"`
	FileSize     int64                  `json:"file_size"`
	CreatedAt    string                 `json:"created_at"`
	Sections     []report.ReportSection `json:"sections,omitempty"`
}

// GetReport 获取报告详情
func (a *App) GetReport(id uint) (*ReportDetail, error) {
	r, err := a.repos.Report.GetByID(id)
	if err != nil {
		return nil, fmt.Errorf("获取报告失败: %w", err)
	}

	detail := &ReportDetail{
		ID:           r.ID,
		Type:         r.Type,
		Name:         r.Name,
		ConnectionID: r.ConnectionID,
		Status:       r.Status,
		Format:       r.Format,
		FilePath:     r.FilePath,
		FileSize:     r.FileSize,
		CreatedAt:    r.CreatedAt.Format("2006-01-02 15:04:05"),
	}

	// 如果报告已完成，尝试读取内容
	if r.Status == "completed" && r.FilePath != "" {
		if data, err := os.ReadFile(r.FilePath); err == nil {
			var reportData report.ReportData
			if json.Unmarshal(data, &reportData) == nil {
				detail.Sections = reportData.Sections
			}
		}
	}

	return detail, nil
}

// ExportReportRequest 导出报告请求
type ExportReportRequest struct {
	ReportID  uint   `json:"report_id"`
	Format    string `json:"format"`    // json, html, xlsx
	OutputDir string `json:"output_dir"` // 可选，默认使用系统临时目录
}

// ExportReport 导出报告
func (a *App) ExportReport(req ExportReportRequest) (string, error) {
	// 获取原报告
	originalReport, err := a.repos.Report.GetByID(req.ReportID)
	if err != nil {
		return "", fmt.Errorf("获取报告失败: %w", err)
	}

	// 确定输出目录
	outputDir := req.OutputDir
	if outputDir == "" {
		outputDir = os.TempDir()
	}

	// 读取原报告数据
	var reportData report.ReportData
	if originalReport.FilePath != "" {
		data, err := os.ReadFile(originalReport.FilePath)
		if err != nil {
			return "", fmt.Errorf("读取报告文件失败: %w", err)
		}
		if err := json.Unmarshal(data, &reportData); err != nil {
			return "", fmt.Errorf("解析报告数据失败: %w", err)
		}
	} else {
		// 从数据库重建报告数据
		reportData = a.buildReportDataFromDB(originalReport.ConnectionID)
	}

	// 创建生成器
	var reportType report.ReportType
	switch req.Format {
	case "json":
		reportType = report.ReportTypeJSON
	case "html":
		reportType = report.ReportTypeHTML
	case "xlsx":
		reportType = report.ReportTypeExcel
	default:
		return "", fmt.Errorf("不支持的导出格式: %s", req.Format)
	}

	generator := report.NewGenerator(&report.ReportConfig{
		Type:      reportType,
		OutputDir: outputDir,
	})

	filepath, err := generator.Generate(&reportData)
	if err != nil {
		return "", fmt.Errorf("生成报告失败: %w", err)
	}

	return filepath, nil
}

// buildReportDataFromDB 从数据库重建报告数据
func (a *App) buildReportDataFromDB(connectionID uint) report.ReportData {
	// 获取最新的分析结果
	var results []storage.AnalysisResult
	storage.DB.Where("connection_id = ?", connectionID).
		Order("created_at DESC").
		Limit(100).
		Find(&results)

	sections := []report.ReportSection{
		{
			Title:   "概述",
			Content: "本报告由 JustFit 云平台资源评估工具自动生成",
			Type:    "text",
		},
	}

	// 根据分析结果构建章节
	for _, r := range results {
		section := report.ReportSection{
			Title: r.AnalysisType + " - " + r.TargetName,
			Type:  "data",
			Data: map[string]interface{}{
				"analysis_type":  r.AnalysisType,
				"target_type":    r.TargetType,
				"target_name":    r.TargetName,
				"recommendation": r.Recommendation,
				"saved_amount":   r.SavedAmount,
			},
		}
		sections = append(sections, section)
	}

	return report.ReportData{
		Title:       fmt.Sprintf("JustFit 分析报告 - 连接ID: %d", connectionID),
		ConnectionID: connectionID,
		Sections:     sections,
	}
}

// ========== 系统配置服务 ==========

// SystemSettings 系统配置
type SystemSettings struct {
	// 分析配置
	DefaultAnalysisDays    int     `json:"default_analysis_days"`
	DefaultCPUThreshold    float64 `json:"default_cpu_threshold"`
	DefaultMemoryThreshold float64 `json:"default_memory_threshold"`
	DefaultBufferRatio     float64 `json:"default_buffer_ratio"`

	// 采集配置
	DefaultMetricsDays    int    `json:"default_metrics_days"`
	CollectionConcurrency int    `json:"collection_concurrency"`

	// 报告配置
	DefaultReportFormat string `json:"default_report_format"`
	ReportOutputDir     string `json:"report_output_dir"`

	// 界面配置
	Theme               string `json:"theme"`
	Language            string `json:"language"`
	AutoRefreshInterval int    `json:"auto_refresh_interval"`
}

// GetSettings 获取系统配置
func (a *App) GetSettings() (*SystemSettings, error) {
	settings := &SystemSettings{
		DefaultAnalysisDays:    7,
		DefaultCPUThreshold:    5.0,
		DefaultMemoryThreshold: 10.0,
		DefaultBufferRatio:     1.2,
		DefaultMetricsDays:     7,
		CollectionConcurrency:  3,
		DefaultReportFormat:    "json",
		ReportOutputDir:        "",
		Theme:                  "light",
		Language:               "zh-CN",
		AutoRefreshInterval:    60,
	}

	// 从数据库读取配置覆盖默认值
	if configData, err := a.repos.Settings.Get("system_config"); err == nil {
		if err := json.Unmarshal([]byte(configData.Value), settings); err == nil {
			return settings, nil
		}
	}

	return settings, nil
}

// UpdateSettings 更新系统配置
func (a *App) UpdateSettings(settings SystemSettings) error {
	data, err := json.Marshal(settings)
	if err != nil {
		return fmt.Errorf("序列化配置失败: %w", err)
	}

	return a.repos.Settings.Set("system_config", string(data), "json")
}

// ExportDiagnosticPackage 导出诊断包
func (a *App) ExportDiagnosticPackage() (string, error) {
	// 让用户选择保存位置
	filename, err := runtime.SaveFileDialog(a.ctx, runtime.SaveDialogOptions{
		Title:           "导出诊断包",
		DefaultFilename: fmt.Sprintf("justfit_diagnostic_%s.zip", time.Now().Format("20060102_150405")),
		Filters: []runtime.FileFilter{
			{DisplayName: "Zip Files (*.zip)", Pattern: "*.zip"},
		},
	})

	if err != nil {
		return "", err
	}

	if filename == "" {
		return "", nil // 用户取消
	}

	// 创建临时目录
	tmpDir, err := os.MkdirTemp("", "justfit_diagnostic_*")
	if err != nil {
		return "", fmt.Errorf("创建临时目录失败: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	// 收集诊断信息
	// 1. 系统信息
	sysInfo := map[string]interface{}{
		"version":    "1.0.0",
		"go_version": "go1.24",
		"os":         runtime.Environment(a.ctx).Platform,
		"arch":       "amd64",
		"timestamp":  time.Now().Format(time.RFC3339),
	}
	sysInfoData, _ := json.MarshalIndent(sysInfo, "", "  ")
	_ = os.WriteFile(filepath.Join(tmpDir, "system_info.json"), sysInfoData, 0644)

	// 2. 数据库信息（不包含敏感数据）
	homeDir := os.Getenv("HOME")
	dbPath := filepath.Join(homeDir, ".justfit", "justfit.db")
	if _, err := os.Stat(dbPath); err == nil {
		// 复制数据库文件到临时目录（用于诊断）
		// 实际生产中应该脱敏处理
		_ = filepath.Join(tmpDir, "justfit.db")
	}

	// TODO: 添加日志文件、配置文件等

	// 这里简化处理，实际应该使用 archive/zip 打包
	// 为了兼容性，我们只创建一个包含系统信息的 JSON 文件
	// 用户可以根据需要手动收集其他文件
	diagnosticFile := filepath.Join(tmpDir, "diagnostic.json")
	_ = os.WriteFile(diagnosticFile, sysInfoData, 0644)

	// 将文件移动到用户选择的位置
	_ = os.Rename(diagnosticFile, filename)

	return filename, nil
}

// ========== 告警服务 ==========

// AlertListItem 告警列表项
type AlertListItem struct {
	ID             uint    `json:"id"`
	TargetType     string  `json:"target_type"`
	TargetKey      string  `json:"target_key"`
	TargetName     string  `json:"target_name"`
	AlertType      string  `json:"alert_type"`
	Severity       string  `json:"severity"`
	Title          string  `json:"title"`
	Message        string  `json:"message"`
	Acknowledged   bool    `json:"acknowledged"`
	AcknowledgedAt *string `json:"acknowledged_at,omitempty"`
	CreatedAt      string  `json:"created_at"`
}

// ListAlerts 获取告警列表
func (a *App) ListAlerts(acknowledged *bool, limit, offset int) ([]AlertListItem, error) {
	var alerts []storage.Alert
	query := storage.DB.Model(&storage.Alert{}).Order("created_at DESC")

	if acknowledged != nil {
		query = query.Where("acknowledged = ?", *acknowledged)
	}

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	err := query.Find(&alerts).Error
	if err != nil {
		return nil, fmt.Errorf("获取告警列表失败: %w", err)
	}

	result := make([]AlertListItem, len(alerts))
	for i, a := range alerts {
		result[i] = AlertListItem{
			ID:           a.ID,
			TargetType:   a.TargetType,
			TargetKey:    a.TargetKey,
			TargetName:   a.TargetName,
			AlertType:    a.AlertType,
			Severity:     a.Severity,
			Title:        a.Title,
			Message:      a.Message,
			Acknowledged: a.Acknowledged,
			CreatedAt:    a.CreatedAt.Format("2006-01-02 15:04:05"),
		}
		if a.AcknowledgedAt != nil {
			t := a.AcknowledgedAt.Format("2006-01-02 15:04:05")
			result[i].AcknowledgedAt = &t
		}
	}

	return result, nil
}

// MarkAlertRequest 标记告警请求
type MarkAlertRequest struct {
	ID           uint  `json:"id"`
	Acknowledged bool  `json:"acknowledged"`
}

// MarkAlert 标记告警
func (a *App) MarkAlert(req MarkAlertRequest) error {
	if req.Acknowledged {
		return a.repos.Alert.Acknowledge(req.ID)
	}

	// 取消确认
	return storage.DB.Model(&storage.Alert{}).
		Where("id = ?", req.ID).
		Updates(map[string]interface{}{
			"acknowledged":     false,
			"acknowledged_at":  nil,
		}).Error
}

// AlertStats 告警统计
type AlertStats struct {
	Total          int64           `json:"total"`
	Unacknowledged int64           `json:"unacknowledged"`
	BySeverity     map[string]int64 `json:"by_severity"`
	ByType         map[string]int64 `json:"by_type"`
}

// GetAlertStats 获取告警统计
func (a *App) GetAlertStats() (*AlertStats, error) {
	stats := &AlertStats{
		BySeverity: make(map[string]int64),
		ByType:     make(map[string]int64),
	}

	storage.DB.Model(&storage.Alert{}).Count(&stats.Total)
	storage.DB.Model(&storage.Alert{}).Where("acknowledged = ?", false).Count(&stats.Unacknowledged)

	// 按严重程度统计
	var severityStats []struct {
		Severity string
		Count    int64
	}
	storage.DB.Model(&storage.Alert{}).
		Select("severity, count(*) as count").
		Group("severity").
		Scan(&severityStats)
	for _, s := range severityStats {
		stats.BySeverity[s.Severity] = s.Count
	}

	// 按类型统计
	var typeStats []struct {
		AlertType string
		Count     int64
	}
	storage.DB.Model(&storage.Alert{}).
		Select("alert_type, count(*) as count").
		Group("alert_type").
		Scan(&typeStats)
	for _, t := range typeStats {
		stats.ByType[t.AlertType] = t.Count
	}

	return stats, nil
}
