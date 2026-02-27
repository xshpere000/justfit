package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	stdruntime "runtime"
	"strings"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
	"gorm.io/gorm"

	"justfit/internal/analyzer"
	"justfit/internal/appdir"
	"justfit/internal/connector"
	"justfit/internal/etl"
	applogger "justfit/internal/logger"
	"justfit/internal/report"
	"justfit/internal/security"
	"justfit/internal/service"
	"justfit/internal/storage"
	"justfit/internal/task"
	"justfit/internal/version"
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
	versionMgr    *version.Manager // 版本管理器
	log           applogger.Logger // 结构化日志器
}

// NewApp 创建新的应用实例
func NewApp() *App {
	return &App{}
}

// startup 应用启动时调用
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx

	// 确保应用目录存在
	if err := appdir.EnsureAppDirs(); err != nil {
		// 在日志初始化前只能用 fmt
		fmt.Printf("WARNING: 创建应用目录失败: %v\n", err)
	}

	// 初始化日志系统
	logDir := appdir.MustGetLogDir()
	logFilePath := filepath.Join(logDir, "app.log")
	fileOutput, err := applogger.NewFileOutput(logFilePath)
	if err != nil {
		fmt.Printf("WARNING: 创建文件日志输出失败: %v\n", err)
	}
	// 开发模式下使用 DEBUG 级别，生产环境建议使用 INFO
	logConfig := &applogger.Config{
		Level: applogger.DEBUG,
		Outputs: []applogger.Output{
			applogger.NewConsoleOutput(applogger.FormatText),
			fileOutput,
		},
		CallerSkip: 1,
	}
	a.log = applogger.New(logConfig)

	// 设置为全局日志器，确保其他模块（如 task）使用相同的日志配置
	applogger.SetGlobal(a.log)

	a.log.Info("应用启动", applogger.String("logDir", logDir))

	// 初始化数据库
	if err := storage.Init(&storage.Config{}); err != nil {
		a.log.Error("初始化数据库失败", applogger.Err(err))
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
		a.log.Warn("创建凭据管理器失败，密码加密功能将不可用", applogger.Err(err))
	}
	a.credentialMgr = credMgr

	// 创建结果存储服务
	a.resultStorage = analyzer.NewResultStorage(a.repos)

	// 创建任务日志记录器
	taskLogger, err := task.NewLogger(logDir, 1000)
	if err != nil {
		a.log.Warn("创建任务日志记录器失败，使用临时目录", applogger.Err(err))
		taskLogger, _ = task.NewLogger(os.TempDir(), 100)
	}
	a.taskLogger = taskLogger

	// 创建任务调度器
	a.taskScheduler = task.NewScheduler(3, a.repos) // 3个worker

	// 注册任务执行器
	collectionExecutor := service.NewCollectionExecutor(a.collector, a.repos)
	analysisExecutor := service.NewAnalysisExecutor(a.analyzer, a.repos)

	a.taskScheduler.RegisterExecutor(task.TypeCollection, collectionExecutor)
	a.taskScheduler.RegisterExecutor(task.TypeAnalysis, analysisExecutor)

	// 创建版本管理器
	db := storage.GetDB()
	a.versionMgr = version.NewManager(db)

	// 执行版本检查
	a.checkVersion()

	a.log.Info("应用初始化完成",
		applogger.Int("workerCount", 3),
		applogger.String("logDir", logDir))
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

// checkVersion 检查版本并处理大版本升级
func (a *App) checkVersion() {
	log := a.log.With(applogger.String("method", "checkVersion"))

	needsRebuild, currentVersion, err := a.versionMgr.CheckVersion()
	if err != nil {
		log.Warn("版本检查失败", applogger.Err(err))
		return
	}

	if currentVersion == "" {
		// 首次安装，保存当前版本
		if err := a.versionMgr.SaveVersion(); err != nil {
			log.Warn("保存版本信息失败", applogger.Err(err))
		} else {
			log.Info("首次安装，已保存版本信息",
				applogger.String("version", version.Version))
		}
		return
	}

	if needsRebuild {
		log.Warn("检测到大版本，需要重建数据库",
			applogger.String("currentVersion", currentVersion),
			applogger.String("latestVersion", version.Version))
		// 注意：实际的重建操作需要用户在前端确认
		// 这里只是记录日志，具体的重建逻辑通过 RebuildDatabase API 暴露给前端
	} else {
		log.Info("版本检查通过",
			applogger.String("currentVersion", currentVersion),
			applogger.String("latestVersion", version.Version))
	}
}

// VersionCheckResult 版本检查结果（供前端使用）
type VersionCheckResult struct {
	NeedsRebuild   bool   `json:"needsRebuild"`
	CurrentVersion string `json:"currentVersion"`
	DatabaseSize   int64  `json:"databaseSize"`
	HasData        bool   `json:"hasData"`
	LatestVersion  string `json:"latestVersion"`
	Message        string `json:"message"`
}

// CheckVersion 检查版本信息（Wails 绑定）
func (a *App) CheckVersion() *VersionCheckResult {
	log := a.log.With(applogger.String("method", "CheckVersion"))

	result := &VersionCheckResult{
		LatestVersion: version.Version,
	}

	needsRebuild, currentVersion, err := a.versionMgr.CheckVersion()
	if err != nil {
		log.Error("版本检查失败", applogger.Err(err))
		result.Message = "版本检查失败: " + err.Error()
		return result
	}

	result.NeedsRebuild = needsRebuild
	result.CurrentVersion = currentVersion

	// 检查是否有实际数据
	if a.versionMgr != nil {
		result.HasData = a.versionMgr.HasData()
	}

	// 获取数据库大小
	if size, err := a.versionMgr.GetDatabaseSize(); err == nil {
		result.DatabaseSize = size
	}

	if needsRebuild {
		if result.HasData {
			result.Message = fmt.Sprintf("检测到大版本升级 (%s → %s)，历史数据将不会保留",
				currentVersion, version.Version)
		} else {
			result.Message = fmt.Sprintf("检测到大版本升级 (%s → %s)，但无历史数据需要清理",
				currentVersion, version.Version)
		}
	} else if currentVersion == "" {
		result.Message = "首次安装"
	} else {
		result.Message = "版本正常"
	}

	log.Info("版本检查完成",
		applogger.Bool("needsRebuild", needsRebuild),
		applogger.String("currentVersion", currentVersion),
		applogger.Bool("hasData", result.HasData),
		applogger.Int64("databaseSize", result.DatabaseSize))

	return result
}

// RebuildDatabase 重建数据库（Wails 绑定）
func (a *App) RebuildDatabase() error {
	log := a.log.With(applogger.String("method", "RebuildDatabase"))

	log.Warn("开始重建数据库",
		applogger.String("oldVersion", a.getStoredVersion()),
		applogger.String("newVersion", version.Version))

	// 关闭数据库连接
	storage.Close()
	log.Debug("已关闭数据库连接")

	// 删除数据库文件
	if err := a.versionMgr.RebuildDatabase(); err != nil {
		log.Error("重建数据库失败", applogger.Err(err))
		return fmt.Errorf("重建数据库失败: %w", err)
	}
	log.Debug("已删除数据库文件")

	// 重新初始化数据库
	log.Info("重新初始化数据库")
	if err := storage.Init(&storage.Config{}); err != nil {
		log.Error("重新初始化数据库失败", applogger.Err(err))
		return fmt.Errorf("重新初始化数据库失败: %w", err)
	}
	log.Debug("数据库重新初始化完成")

	// 更新仓储实例
	a.repos = storage.NewRepositories()
	log.Debug("已更新仓储实例")

	// 更新版本管理器的数据库实例
	db := storage.GetDB()
	a.versionMgr = version.NewManager(db)

	// 保存当前版本
	if err := a.versionMgr.SaveVersion(); err != nil {
		log.Warn("保存版本信息失败", applogger.Err(err))
	} else {
		log.Info("已保存新版本信息", applogger.String("version", version.Version))
	}

	// 注意：由于重建后数据为空，collector、analyzer、resultStorage 等组件
	// 使用的是新的 repos 实例，会自动引用新的数据库连接，无需重新创建

	log.Info("数据库重建完成，建议重启应用以加载所有组件")
	return nil
}

// getStoredVersion 获取存储的版本信息（辅助方法）
func (a *App) getStoredVersion() string {
	if a.versionMgr == nil {
		return ""
	}
	_, version, _ := a.versionMgr.CheckVersion()
	return version
}

// AppVersionInfo 应用版本信息（供前端使用）
type AppVersionInfo struct {
	Version       string   `json:"version"`       // 当前版本
	StoredVersion string   `json:"storedVersion"` // 数据库中存储的版本
	MajorVersions []string `json:"majorVersions"` // 大版本列表
	IsDevelopment bool     `json:"isDevelopment"` // 是否开发版本
}

// GetAppVersion 获取应用版本信息（Wails 绑定）
// 前端通过此 API 获取版本号，实现统一版本显示
func (a *App) GetAppVersion() *AppVersionInfo {
	log := a.log.With(applogger.String("method", "GetAppVersion"))

	// 从 version 包获取版本信息
	versionInfo := version.GetVersionInfo()

	// 获取数据库中存储的版本
	storedVersion := a.getStoredVersion()

	result := &AppVersionInfo{
		Version:       versionInfo.Version,
		StoredVersion: storedVersion,
		MajorVersions: versionInfo.MajorVersions,
		IsDevelopment: versionInfo.IsDevelopment,
	}

	log.Debug("获取应用版本信息",
		applogger.String("version", result.Version),
		applogger.String("storedVersion", storedVersion))

	return result
}

// GetDashboardStats 获取仪表盘数据
type DashboardStats struct {
	HealthScore  float64 `json:"healthScore"`
	ZombieCount  int64   `json:"zombieCount"`
	TotalSavings string  `json:"totalSavings"` // 字符串展示，如 "¥12,400/月"
	VMCount      int64   `json:"vmCount"`
}

func (a *App) GetDashboardStats() (*DashboardStats, error) {
	log := a.log.With(applogger.String("method", "GetDashboardStats"))

	// 1. 获取所有连接的 VM 总数
	var vmCount int64
	if err := storage.DB.Model(&storage.VM{}).Count(&vmCount).Error; err != nil {
		log.Warn("统计虚拟机总数失败", applogger.Err(err))
	}

	// 2. 获取最新的健康评分 (取最近一条)
	var latestHealth storage.AnalysisResult
	var healthScore float64 = 0 // 默认 0

	// 从 AnalysisResult 表中查找 type=health 的最新记录
	err := storage.DB.Where("analysis_type = ?", "health").Order("created_at desc").First(&latestHealth).Error
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
	var zombieCount int64
	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "zombie", time.Now().AddDate(0, 0, -7)).
		Count(&zombieCount)

	// 4. 计算节省
	var monthlySaving float64 = 0
	if zombieCount > 0 {
		// 估算：假设每个僵尸 VM 平均浪费 2 vCPU + 4GB 内存
		// 假设 vCPU 的月成本为 50 元，1GB 内存月成本为 20 元
		// 则单台 VM 节省 = 2*50 + 4*20 = 180 元
		monthlySaving = float64(zombieCount) * 180
	}

	savings := fmt.Sprintf("¥%.0f/月", monthlySaving)

	log.Debug("获取仪表盘统计数据",
		applogger.Int64("vmCount", vmCount),
		applogger.Int64("zombieCount", zombieCount),
		applogger.Float64("healthScore", healthScore))

	return &DashboardStats{
		HealthScore:  healthScore,
		ZombieCount:  zombieCount,
		TotalSavings: savings,
		VMCount:      vmCount,
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
	LastSync string `json:"lastSync"`
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
	Name           string   `json:"name"` // 任务名称
	ConnectionID   uint     `json:"connectionId"`
	ConnectionName string   `json:"connectionName"` // 连接名称
	Platform       string   `json:"platform"`       // 平台类型: vcenter, h3c-uis
	DataTypes      []string `json:"dataTypes"`      // clusters, hosts, vms, metrics
	MetricsDays    int      `json:"metricsDays"`
	VMCount        int      `json:"vmCount"`     // 虚拟机总数
	SelectedVMs    []string `json:"selectedVMs"` // 用户选择的虚拟机列表（vmKey 格式）
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

// CollectData 快速采集（不创建任务记录）
// 用途：Collection 页面的"开始采集"按钮，即时查看资源状态
// 特点：
//   - 不创建 AssessmentTask 记录
//   - 采集的数据不持久化（仅用于实时展示）
//   - taskID = 0（表示无任务上下文的临时采集）
//   - 立即返回结果，不使用任务调度器
//
// 与评估任务（CreateCollectTask）的区别：
//   - 评估任务会创建持久化任务记录，数据长期存储用于分析
//   - 快速采集是一次性操作，数据临时展示
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
		// 手动采集不关联任务，传递 taskID=0
		metricStats, metricErr := a.collector.CollectMetrics(a.ctx, 0, config.ConnectionID, config.MetricsDays, password, nil, nil)
		if metricStats != nil {
			metricCount = metricStats.CollectedMetricCount
		}
		if metricErr != nil {
			// 性能指标采集失败不影响基础数据采集结果
			a.log.Warn("采集性能指标失败", applogger.Err(metricErr))
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
	CreatedAt   string  `json:"createdAt"`
	StartedAt   *string `json:"startedAt,omitempty"`
	CompletedAt *string `json:"completedAt,omitempty"`

	// 扩展字段
	ConnectionID     *uint           `json:"connectionId,omitempty"`
	ConnectionName   string          `json:"connectionName,omitempty"`
	Host             string          `json:"host,omitempty"`
	Platform         string          `json:"platform,omitempty"`
	SelectedVMs      []string        `json:"selectedVMs,omitempty"`
	VMCount          int             `json:"vmCount,omitempty"`
	CollectedVMCount int             `json:"collectedVMCount,omitempty"`
	CurrentStep      string          `json:"currentStep,omitempty"`
	AnalysisResults  map[string]bool `json:"analysisResults,omitempty"`
}

// TaskDetail 任务详情（任务维度）
type TaskDetail struct {
	TaskInfo
	ConnectionID     uint                   `json:"connectionId"`
	Platform         string                 `json:"platform"`
	SelectedVMs      []string               `json:"selectedVMs"`
	VMCount          int                    `json:"vmCount"`
	CollectedVMCount int                    `json:"collectedVMCount"`
	CurrentStep      string                 `json:"currentStep"`
	AnalysisResults  map[string]bool        `json:"analysisResults"`
	Result           map[string]interface{} `json:"result,omitempty"`
}

// CreateCollectTask 创建采集任务
func (a *App) CreateCollectTask(config CollectionConfig) (uint, error) {
	log := a.log.With(applogger.String("method", "CreateCollectTask"))

	log.Info("开始创建采集任务",
		applogger.String("name", config.Name),
		applogger.Uint("connectionID", config.ConnectionID),
		applogger.String("connectionName", config.ConnectionName),
		applogger.String("platform", config.Platform),
		applogger.Int("vmCount", config.VMCount),
		applogger.Int("selectedVMsCount", len(config.SelectedVMs)))

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
		"connectionId":   config.ConnectionID,
		"connectionName": config.ConnectionName,
		"platform":       config.Platform,
		"dataTypes":      config.DataTypes,
		"metricsDays":    config.MetricsDays,
		"password":       password,
		"vmCount":        config.VMCount,
		"selectedVMs":    config.SelectedVMs,
	}

	// 调试：记录放入 map 后的类型和值
	log.Info("[DEBUG] taskConfig 创建完成",
		applogger.Any("connectionId_raw", taskConfig["connectionId"]),
		applogger.String("connectionId_type", fmt.Sprintf("%T", taskConfig["connectionId"])),
		applogger.Any("vmCount", taskConfig["vmCount"]),
		applogger.String("vmCount_type", fmt.Sprintf("%T", taskConfig["vmCount"])),
		applogger.Any("selectedVMs", taskConfig["selectedVMs"]),
		applogger.String("selectedVMs_type", fmt.Sprintf("%T", taskConfig["selectedVMs"])))

	// 使用前端传来的任务名称，如果为空则使用默认名称
	taskName := config.Name
	if taskName == "" {
		taskName = fmt.Sprintf("采集任务 - 连接ID: %d", config.ConnectionID)
	}
	t, err := a.taskScheduler.Create(task.TypeCollection, taskName, taskConfig)
	if err != nil {
		log.Error("创建任务失败", applogger.Err(err))
		return 0, fmt.Errorf("创建任务失败: %w", err)
	}

	log.Info("任务创建成功", applogger.Uint("taskID", t.ID))

	// 同步提交执行（不使用 goroutine），确保 status 在前端同步前变成 running
	if err := a.taskScheduler.Submit(a.ctx, t.ID); err != nil {
		log.Error("提交任务执行失败", applogger.Uint("taskID", t.ID), applogger.Err(err))
		return 0, fmt.Errorf("提交任务执行失败: %w", err)
	}

	return t.ID, nil
}

// RunAnalysisJob 在评估任务下执行分析子任务
// 参数: taskID - 评估任务ID, analysisType - 分析类型 (zombie, rightsize, tidal, health), config - 分析配置
// 返回: jobID - 分析子任务ID
func (a *App) RunAnalysisJob(taskID uint, analysisType string, config map[string]interface{}) (uint, error) {
	log := a.log.With(
		applogger.String("method", "RunAnalysisJob"),
		applogger.Uint("taskID", taskID),
		applogger.String("analysisType", analysisType))

	log.Info("收到运行分析子任务请求",
		applogger.Any("config", config))

	// 验证评估任务是否存在
	assessmentTask, err := a.repos.AssessmentTask.GetByID(taskID)
	if err != nil {
		log.Warn("评估任务不存在", applogger.Err(err))
		return 0, fmt.Errorf("评估任务不存在: %w", err)
	}
	log.Debug("找到评估任务",
		applogger.String("name", assessmentTask.Name),
		applogger.String("status", assessmentTask.Status))

	// 前端使用: zombie, rightsize, tidal, health
	// 后端使用: zombie, rightsize, tidal, health
	var backendJobType string
	switch analysisType {
	case "zombie":
		backendJobType = "zombie"
	case "rightsize":
		backendJobType = "rightsize"
	case "health":
		backendJobType = "health"
	default:
		backendJobType = analysisType
	}
	log.Debug("类型转换",
		applogger.String("frontend", analysisType),
		applogger.String("backend", backendJobType))

	// 创建分析子任务
	job := &storage.TaskAnalysisJob{
		TaskID:   taskID,
		JobType:  backendJobType,
		Status:   "pending",
		Progress: 0,
	}

	if err := a.repos.TaskAnalysisJob.Create(job); err != nil {
		log.Error("创建分析子任务失败", applogger.Err(err))
		return 0, fmt.Errorf("创建分析子任务失败: %w", err)
	}
	log.Info("分析子任务创建成功", applogger.Uint("jobID", job.ID))

	// 记录日志
	a.repos.TaskLog.CreateLog(taskID, &job.ID, "analysis_started", "system",
		fmt.Sprintf("开始%s分析", backendJobType),
		fmt.Sprintf("在评估任务 '%s' 下执行 %s 分析", assessmentTask.Name, backendJobType),
		config, nil, 0)

	// 异步执行分析
	go a.executeAnalysisJob(taskID, job.ID, backendJobType, assessmentTask.ConnectionID, config)

	return job.ID, nil
}

// GetAnalysisJobs 获取任务的所有分析子任务
func (a *App) GetAnalysisJobs(taskID uint) ([]map[string]interface{}, error) {
	log := a.log.With(
		applogger.String("method", "GetAnalysisJobs"),
		applogger.Uint("taskID", taskID))

	log.Debug("获取任务分析子任务")

	jobs, err := a.repos.TaskAnalysisJob.ListByTaskID(taskID)
	if err != nil {
		log.Warn("查询分析子任务失败", applogger.Err(err))
		return nil, err
	}

	result := make([]map[string]interface{}, len(jobs))
	for i, job := range jobs {
		result[i] = map[string]interface{}{
			"id":          job.ID,
			"taskId":      job.TaskID,
			"jobType":     job.JobType,
			"status":      job.Status,
			"progress":    job.Progress,
			"error":       job.Error,
			"resultCount": job.ResultCount,
			"createdAt":   job.CreatedAt.Format("2006-01-02 15:04:05"),
		}
		if job.StartedAt != nil {
			result[i]["startedAt"] = job.StartedAt.Format("2006-01-02 15:04:05")
		}
		if job.CompletedAt != nil {
			result[i]["completedAt"] = job.CompletedAt.Format("2006-01-02 15:04:05")
		}
	}

	log.Debug("获取分析子任务成功", applogger.Int("count", len(result)))
	return result, nil
}

// GetAnalysisJobStatus 获取单个分析子任务状态
func (a *App) GetAnalysisJobStatus(jobID uint) (map[string]interface{}, error) {
	log := a.log.With(
		applogger.String("method", "GetAnalysisJobStatus"),
		applogger.Uint("jobID", jobID))

	log.Debug("获取分析子任务状态")

	job, err := a.repos.TaskAnalysisJob.GetByID(jobID)
	if err != nil {
		log.Warn("查询分析子任务失败", applogger.Err(err))
		return nil, err
	}

	result := map[string]interface{}{
		"id":          job.ID,
		"taskId":      job.TaskID,
		"jobType":     job.JobType,
		"status":      job.Status,
		"progress":    job.Progress,
		"error":       job.Error,
		"resultCount": job.ResultCount,
		"createdAt":   job.CreatedAt.Format("2006-01-02 15:04:05"),
	}
	if job.StartedAt != nil {
		result["startedAt"] = job.StartedAt.Format("2006-01-02 15:04:05")
	}
	if job.CompletedAt != nil {
		result["completedAt"] = job.CompletedAt.Format("2006-01-02 15:04:05")
	}

	return result, nil
}

// CreateAnalysisTask 向后兼容方法 (已废弃，建议使用 RunAnalysisJob)
// 此方法保留用于向后兼容，内部创建一个临时的评估任务
func (a *App) CreateAnalysisTask(analysisType string, connectionID uint, config map[string]interface{}) (uint, error) {
	log := a.log.With(
		applogger.String("method", "CreateAnalysisTask"),
		applogger.String("analysisType", analysisType),
		applogger.Uint("connectionID", connectionID))

	log.Info("收到创建分析任务请求(已废弃方法)")

	// 前端使用: zombie, rightsize, tidal, health
	// 后端使用: zombie, rightsize, tidal, health
	var backendAnalysisType string
	switch analysisType {
	case "zombie":
		backendAnalysisType = "zombie"
	case "rightsize":
		backendAnalysisType = "rightsize"
	case "health":
		backendAnalysisType = "health"
	default:
		backendAnalysisType = analysisType
	}

	// 创建一个临时的评估任务来容纳分析任务
	assessmentTask := &storage.AssessmentTask{
		Name:         fmt.Sprintf("临时分析任务 - %s", backendAnalysisType),
		ConnectionID: connectionID,
		Status:       "analyzing",
		Progress:     0,
		CurrentStep:  fmt.Sprintf("执行 %s 分析", backendAnalysisType),
		MetricsDays:  30,
	}

	if err := a.repos.AssessmentTask.Create(assessmentTask); err != nil {
		log.Error("创建临时评估任务失败", applogger.Err(err))
		return 0, fmt.Errorf("创建临时评估任务失败: %w", err)
	}
	log.Info("临时评估任务创建成功", applogger.Uint("taskID", assessmentTask.ID))

	// 创建分析子任务
	job := &storage.TaskAnalysisJob{
		TaskID:   assessmentTask.ID,
		JobType:  backendAnalysisType,
		Status:   "pending",
		Progress: 0,
	}

	if err := a.repos.TaskAnalysisJob.Create(job); err != nil {
		log.Error("创建分析子任务失败", applogger.Err(err))
		return 0, fmt.Errorf("创建分析子任务失败: %w", err)
	}

	// 异步执行分析
	go a.executeAnalysisJob(assessmentTask.ID, job.ID, backendAnalysisType, connectionID, config)

	// 返回评估任务ID (兼容旧接口)
	return assessmentTask.ID, nil
}

// executeAnalysisJob 执行分析子任务
func (a *App) executeAnalysisJob(taskID uint, jobID uint, jobType string, connectionID uint, config map[string]interface{}) {
	log := a.log.With(
		applogger.String("method", "executeAnalysisJob"),
		applogger.Uint("taskID", taskID),
		applogger.Uint("jobID", jobID),
		applogger.String("jobType", jobType),
		applogger.Uint("connectionID", connectionID))

	log.Info("开始执行分析子任务")

	// 验证 connectionID
	if connectionID == 0 {
		err := fmt.Errorf("无效的连接ID: connectionID 为 0")
		log.Error("连接ID无效", applogger.Uint("connectionID", connectionID))
		a.repos.TaskAnalysisJob.UpdateStatus(jobID, "failed", 0)
		a.repos.TaskLog.CreateLog(taskID, &jobID, "analysis_failed", "error",
			"连接ID无效", err.Error(), nil, nil, 0)
		return
	}

	// 更新状态为运行中
	a.repos.TaskAnalysisJob.UpdateStatus(jobID, "running", 0)
	a.repos.TaskLog.CreateLog(taskID, &jobID, "analysis_running", "system",
		"分析执行中", fmt.Sprintf("正在执行 %s 分析", jobType), nil, nil, 0)

	var result interface{}
	var err error
	var startTime = time.Now()

	// 根据分析类型执行
	switch jobType {
	case "zombie":
		cfg := parseZombieVMConfigFromMap(config)
		analyzerConfig := analyzer.ZombieVMConfig{
			AnalysisDays:    cfg.AnalysisDays,
			CPUThreshold:    cfg.CPUThreshold,
			MemoryThreshold: cfg.MemoryThreshold,
			MinConfidence:   cfg.MinConfidence,
		}
		result, err = a.analyzer.DetectZombieVMs(taskID, connectionID, &analyzerConfig)
	case "rightsize":
		cfg := parseRightSizeConfigFromMap(config)
		analyzerConfig := analyzer.RightSizeConfig{
			AnalysisDays: cfg.AnalysisDays,
			BufferRatio:  cfg.BufferRatio,
		}
		result, err = a.analyzer.AnalyzeRightSize(taskID, connectionID, &analyzerConfig)
	case "tidal":
		cfg := parseTidalConfigFromMap(config)
		analyzerConfig := analyzer.TidalConfig{
			AnalysisDays: cfg.AnalysisDays,
			MinStability: cfg.MinStability,
		}
		result, err = a.analyzer.DetectTidalPattern(taskID, connectionID, &analyzerConfig)
	case "health":
		healthConfig := &analyzer.HealthConfig{}
		result, err = a.analyzer.AnalyzeHealthScore(connectionID, healthConfig)
	default:
		err = fmt.Errorf("不支持的分析类型: %s", jobType)
	}

	duration := time.Since(startTime).Milliseconds()

	if err != nil {
		log.Error("分析执行失败", applogger.Err(err), applogger.Int64("duration", duration))
		a.repos.TaskAnalysisJob.UpdateStatus(jobID, "failed", 0)
		a.repos.TaskLog.CreateLog(taskID, &jobID, "analysis_failed", "error",
			"分析失败", err.Error(), nil, nil, duration)
		return
	}

	// 保存分析结果到 AnalysisFinding
	if result != nil {
		switch jobType {
		case "zombie":
			if zombies, ok := result.([]analyzer.ZombieVMResult); ok {
				a.resultStorage.SaveZombieVMResults(taskID, zombies)
			}
		case "rightsize":
			if results, ok := result.([]analyzer.RightSizeResult); ok {
				a.resultStorage.SaveRightSizeResults(taskID, results)
			}
		case "tidal":
			if results, ok := result.([]analyzer.TidalResult); ok {
				a.resultStorage.SaveTidalResults(taskID, results)
			}
		case "health":
			if health, ok := result.(analyzer.HealthScoreResult); ok {
				a.resultStorage.SaveHealthScoreResult(taskID, health)
			}
		}
	}

	// 保存结果到 Job
	resultJSON, _ := json.Marshal(result)
	resultCount := 0
	if m, ok := result.(map[string]interface{}); ok {
		if c, ok := m["count"].(int); ok {
			resultCount = c
		}
	} else if arr, ok := result.([]interface{}); ok {
		resultCount = len(arr)
	}

	a.repos.TaskAnalysisJob.UpdateResult(jobID, "completed", string(resultJSON), resultCount)
	a.repos.TaskLog.CreateLog(taskID, &jobID, "analysis_completed", "success",
		"分析完成", fmt.Sprintf("%s 分析完成，发现 %d 个结果", jobType, resultCount),
		nil, map[string]interface{}{"count": resultCount}, duration)

	log.Info("分析执行完成",
		applogger.Int("resultCount", resultCount),
		applogger.Int64("duration", duration))

	// 更新评估任务的进度
	a.updateTaskProgressFromJobs(taskID)
}

// updateTaskProgressFromJobs 根据子任务进度更新评估任务进度
func (a *App) updateTaskProgressFromJobs(taskID uint) {
	jobs, err := a.repos.TaskAnalysisJob.ListByTaskID(taskID)
	if err != nil {
		return
	}

	totalJobs := len(jobs)
	completedJobs := 0
	totalProgress := 0

	for _, job := range jobs {
		totalProgress += job.Progress
		if job.Status == "completed" {
			completedJobs++
		}
	}

	avgProgress := 0
	if totalJobs > 0 {
		avgProgress = totalProgress / totalJobs
	}

	// 更新评估任务状态
	assessmentTask, err := a.repos.AssessmentTask.GetByID(taskID)
	if err != nil {
		return // 任务不存在，直接返回
	}

	// 更新状态和进度，保留其他字段
	assessmentTask.Progress = avgProgress
	if assessmentTask.Status == "collecting" || assessmentTask.Status == "pending" {
		assessmentTask.Status = "analyzing"
	}

	// 所有分析完成，更新任务状态（但不覆盖 CompletedAt，保持采集完成时间）
	if completedJobs == totalJobs && totalJobs > 0 {
		assessmentTask.Status = "completed"
		assessmentTask.Progress = 100
		// 不更新 CompletedAt，保持采集任务的原始完成时间
		// 分析子任务有自己独立的 StartedAt/CompletedAt
	}

	// 保存更新（使用已存在的对象，保留所有字段）
	a.repos.AssessmentTask.Update(assessmentTask)
}

// ListTasks 获取任务列表
func (a *App) ListTasks(status string, limit, offset int) ([]TaskInfo, error) {
	log := a.log.With(
		applogger.String("method", "ListTasks"),
		applogger.String("status", status),
		applogger.Int("limit", limit),
		applogger.Int("offset", offset))

	log.Info("查询任务列表开始")

	var dbTasks []storage.AssessmentTask
	query := storage.DB

	if status != "" {
		query = query.Where("status = ?", status)
	}

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	err := query.Order("created_at DESC").Find(&dbTasks).Error
	if err != nil {
		log.Error("查询任务列表失败", applogger.Err(err))
		return nil, err
	}
	log.Info("查询任务列表成功", applogger.Int("count", len(dbTasks)))

	result := make([]TaskInfo, len(dbTasks))
	for i, t := range dbTasks {
		// 解析 selected_vms
		var selectedVMs []string
		if t.SelectedVMs != "" {
			json.Unmarshal([]byte(t.SelectedVMs), &selectedVMs)
		}

		result[i] = TaskInfo{
			ID:        t.ID,
			Type:      "assessment", // 固定类型，所有任务都是评估任务
			Name:      t.Name,
			Status:    t.Status,
			Progress:  float64(t.Progress),
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

		// 添加扩展字段
		result[i].ConnectionID = &t.ConnectionID
		result[i].ConnectionName = t.ConnectionName
		result[i].Platform = t.Platform
		result[i].SelectedVMs = selectedVMs
		result[i].VMCount = len(selectedVMs)

		// 获取连接的 Host 信息
		if t.ConnectionID > 0 {
			if conn, err := a.repos.Connection.GetByID(t.ConnectionID); err == nil {
				result[i].Host = conn.Host
			}
		}

		// 从快照表获取实际采集的 VM 数量
		if snapshotCount, err := a.repos.TaskVMSnapshot.CountByTaskID(t.ID); err == nil {
			result[i].CollectedVMCount = int(snapshotCount)
			// 如果 TotalVMs 为 0 但采集到了 VM，更新 TotalVMs
			if result[i].VMCount == 0 && result[i].CollectedVMCount > 0 {
				result[i].VMCount = result[i].CollectedVMCount
			}
		} else {
			result[i].CollectedVMCount = 0
		}
		result[i].CurrentStep = t.CurrentStep

		// 获取分析结果状态
		analysisResults := make(map[string]bool)
		if analysisJobs, err := a.repos.TaskAnalysisJob.ListByTaskID(t.ID); err == nil {
			for _, job := range analysisJobs {
				switch job.JobType {
				case "zombie":
					analysisResults["zombie"] = job.Status == "completed"
				case "rightsize":
					analysisResults["rightsize"] = job.Status == "completed"
				case "tidal":
					analysisResults["tidal"] = job.Status == "completed"
				case "health":
					analysisResults["health"] = job.Status == "completed"
				}
			}
		}
		result[i].AnalysisResults = analysisResults
	}

	return result, nil
}

// GetTask 获取任务详情
func (a *App) GetTask(id uint) (*TaskInfo, error) {
	// 直接从数据库获取完整的任务信息
	dbTask, err := a.repos.AssessmentTask.GetByID(id)
	if err != nil {
		return nil, err
	}

	// 解析 selected_vms
	var selectedVMs []string
	if dbTask.SelectedVMs != "" {
		json.Unmarshal([]byte(dbTask.SelectedVMs), &selectedVMs)
	}

	// 从快照表获取实际采集的 VM 数量
	collectedVMs := 0
	if snapshotCount, err := a.repos.TaskVMSnapshot.CountByTaskID(dbTask.ID); err == nil {
		collectedVMs = int(snapshotCount)
	}

	// 获取分析结果状态
	analysisResults := make(map[string]bool)
	if analysisJobs, err := a.repos.TaskAnalysisJob.ListByTaskID(dbTask.ID); err == nil {
		for _, job := range analysisJobs {
			switch job.JobType {
			case "zombie":
				analysisResults["zombie"] = job.Status == "completed"
			case "rightsize":
				analysisResults["rightsize"] = job.Status == "completed"
			case "tidal":
				analysisResults["tidal"] = job.Status == "completed"
			case "health":
				analysisResults["health"] = job.Status == "completed"
			}
		}
	}

	result := &TaskInfo{
		ID:        dbTask.ID,
		Type:      "assessment", // 固定类型，所有任务都是评估任务
		Name:      dbTask.Name,
		Status:    dbTask.Status,
		Progress:  float64(dbTask.Progress),
		Error:     dbTask.Error,
		CreatedAt: dbTask.CreatedAt.Format("2006-01-02 15:04:05"),
		// 扩展字段 - 从数据库获取
		ConnectionID:     &dbTask.ConnectionID,
		ConnectionName:   dbTask.ConnectionName,
		Platform:         dbTask.Platform,
		SelectedVMs:      selectedVMs,
		VMCount:          len(selectedVMs),
		CollectedVMCount: collectedVMs,
		CurrentStep:      dbTask.CurrentStep,
		AnalysisResults:  analysisResults,
	}
	if dbTask.StartedAt != nil {
		s := dbTask.StartedAt.Format("2006-01-02 15:04:05")
		result.StartedAt = &s
	}
	if dbTask.CompletedAt != nil {
		c := dbTask.CompletedAt.Format("2006-01-02 15:04:05")
		result.CompletedAt = &c
	}

	// 获取连接的 Host 信息
	if dbTask.ConnectionID > 0 {
		if conn, err := a.repos.Connection.GetByID(dbTask.ConnectionID); err == nil {
			result.Host = conn.Host
		}
	}

	return result, nil
}

// GetTaskDetail 获取任务详情扩展字段
func (a *App) GetTaskDetail(taskID uint) (*TaskDetail, error) {
	// 从数据库获取完整任务信息
	dbTask, err := a.repos.AssessmentTask.GetByID(taskID)
	if err != nil {
		return nil, err
	}

	// 解析 selected_vms
	var selectedVMs []string
	if dbTask.SelectedVMs != "" {
		json.Unmarshal([]byte(dbTask.SelectedVMs), &selectedVMs)
	}

	// 从快照表获取实际采集的 VM 数量
	collectedVMs := 0
	if snapshotCount, snapshotErr := a.repos.TaskVMSnapshot.CountByTaskID(dbTask.ID); snapshotErr == nil {
		collectedVMs = int(snapshotCount)
	}

	// 获取连接信息
	platform := dbTask.Platform
	connectionID := uint(dbTask.ConnectionID)
	if dbTask.ConnectionID > 0 {
		if conn, connErr := a.repos.Connection.GetByID(dbTask.ConnectionID); connErr == nil {
			platform = conn.Platform
		}
	}

	// 分析结果标志
	analysisFlags := map[string]bool{
		"zombie":    false,
		"rightsize": false,
		"tidal":     false,
		"health":    false,
	}
	if analysisRows, analysisErr := a.repos.TaskAnalysisJob.ListByTaskID(dbTask.ID); analysisErr == nil {
		for _, row := range analysisRows {
			switch row.JobType {
			case "zombie":
				analysisFlags["zombie"] = row.Status == "completed"
			case "rightsize":
				analysisFlags["rightsize"] = row.Status == "completed"
			case "tidal":
				analysisFlags["tidal"] = row.Status == "completed"
			case "health":
				analysisFlags["health"] = row.Status == "completed"
			}
		}
	}

	// 当前步骤
	currentStep := dbTask.CurrentStep
	if currentStep == "" {
		switch dbTask.Status {
		case "pending":
			currentStep = "等待执行"
		case "collecting", "running":
			currentStep = "采集中"
		case "analyzing":
			currentStep = "分析中"
		case "completed":
			currentStep = "已完成"
		case "failed":
			currentStep = "执行失败: " + dbTask.Error
		}
	}

	vmCount := len(selectedVMs)
	if vmCount == 0 && collectedVMs > 0 {
		vmCount = collectedVMs
	}

	return &TaskDetail{
		TaskInfo: TaskInfo{
			ID:               dbTask.ID,
			Type:             "assessment",
			Name:             dbTask.Name,
			Status:           dbTask.Status,
			Progress:         float64(dbTask.Progress),
			Error:            dbTask.Error,
			CreatedAt:        dbTask.CreatedAt.Format("2006-01-02 15:04:05"),
			ConnectionID:     &connectionID,
			ConnectionName:   dbTask.ConnectionName,
			Platform:         platform,
			SelectedVMs:      selectedVMs,
			VMCount:          vmCount,
			CollectedVMCount: collectedVMs,
			CurrentStep:      currentStep,
		},
		ConnectionID:     connectionID,
		Platform:         platform,
		SelectedVMs:      selectedVMs,
		VMCount:          vmCount,
		CollectedVMCount: collectedVMs,
		CurrentStep:      currentStep,
		AnalysisResults:  analysisFlags,
		Result:           make(map[string]interface{}),
	}, nil
}

// ListTaskVMs 获取任务快照维度虚拟机列表
func (a *App) ListTaskVMs(taskID uint, limit, offset int, keyword string) (*TaskVMListResponse, error) {
	log := a.log.With(
		applogger.String("method", "ListTaskVMs"),
		applogger.Uint("taskID", taskID),
		applogger.Int("limit", limit),
		applogger.Int("offset", offset),
		applogger.String("keyword", keyword))

	log.Debug("查询任务快照虚拟机")

	snapshots, total, err := a.repos.TaskVMSnapshot.ListByTaskID(taskID, limit, offset, keyword)
	if err != nil {
		log.Error("查询任务快照失败", applogger.Err(err))
		return nil, fmt.Errorf("获取任务快照虚拟机失败: %w", err)
	}
	log.Debug("查询任务快照成功", applogger.Int("count", len(snapshots)), applogger.Int64("total", total))

	items := make([]VMListItem, len(snapshots))
	for i, row := range snapshots {
		items[i] = VMListItem{
			ID:              row.ID,
			Name:            row.Name,
			Datacenter:      row.Datacenter,
			UUID:            row.UUID,
			CPUCount:        row.CpuCount,
			MemoryGB:        float64(row.MemoryMB) / 1024,
			PowerState:      row.PowerState,
			ConnectionState: row.ConnectionState,
			IPAddress:       row.IPAddress,
			GuestOS:         row.GuestOS,
			HostName:        row.HostName,
			OverallStatus:   row.OverallStatus,
			CollectedAt:     row.CollectedAt.Format("2006-01-02 15:04:05"),
		}
	}

	return &TaskVMListResponse{
		VMs:   items,
		Total: total,
	}, nil
}

// GetTaskAnalysisResult 获取任务分析结果
func (a *App) GetTaskAnalysisResult(taskID uint, analysisType string) (interface{}, error) {
	log := a.log.With(
		applogger.String("method", "GetTaskAnalysisResult"),
		applogger.Uint("taskID", taskID),
		applogger.String("analysisType", analysisType))

	log.Debug("查询任务分析结果")

	if strings.TrimSpace(analysisType) != "" {
		row, err := a.repos.TaskAnalysisJob.GetByTaskAndType(taskID, analysisType)
		if err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				log.Debug("未找到指定类型的分析结果")
				return map[string]interface{}{}, nil
			}
			log.Error("查询任务分析结果失败", applogger.Err(err))
			return nil, fmt.Errorf("获取任务分析结果失败: %w", err)
		}

		var data interface{}
		if err := json.Unmarshal([]byte(row.Result), &data); err != nil {
			log.Error("解析分析结果失败", applogger.Err(err))
			return nil, fmt.Errorf("解析任务分析结果失败: %w", err)
		}
		return data, nil
	}

	rows, err := a.repos.TaskAnalysisJob.ListByTaskID(taskID)
	if err != nil {
		log.Error("查询分析结果列表失败", applogger.Err(err))
		return nil, fmt.Errorf("获取任务分析结果失败: %w", err)
	}

	log.Debug("查询到分析结果", applogger.Int("count", len(rows)))

	// 蛇形转驼峰映射表
	snakeToCamel := map[string]string{
		"zombie":    "zombieVM",
		"rightsize": "rightSize",
		"tidal":     "tidal",
		"health":    "healthScore",
	}

	result := make(map[string]interface{})
	for _, row := range rows {
		// 转换为驼峰格式，如果找不到映射则保持原样
		camelKey := snakeToCamel[row.JobType]
		if camelKey == "" {
			camelKey = row.JobType
		}
		if _, exists := result[camelKey]; exists {
			continue
		}
		var data interface{}
		if err := json.Unmarshal([]byte(row.Result), &data); err == nil {
			result[camelKey] = data
		} else {
			log.Warn("解析分析结果失败",
				applogger.String("jobType", row.JobType),
				applogger.Err(err))
		}
	}

	log.Debug("返回分析结果", applogger.Int("types", len(result)))
	return result, nil
}

// ExportTaskReport 按任务导出报告
func (a *App) ExportTaskReport(taskID uint, format string) (string, error) {
	taskDetail, err := a.GetTaskDetail(taskID)
	if err != nil {
		return "", err
	}

	var reportType report.ReportType
	switch format {
	case "", "json":
		reportType = report.ReportTypeJSON
	case "html":
		reportType = report.ReportTypeHTML
	case "xlsx":
		reportType = report.ReportTypeExcel
	default:
		return "", fmt.Errorf("不支持的导出格式: %s", format)
	}

	vmsResp, _ := a.ListTaskVMs(taskID, 0, 0, "")
	vms := vmsResp.VMs
	analysisData, _ := a.GetTaskAnalysisResult(taskID, "")

	reportData := &report.ReportData{
		Title:        fmt.Sprintf("任务报告-%d", taskID),
		ConnectionID: taskDetail.ConnectionID,
		Metadata: map[string]interface{}{
			"task_id":      taskID,
			"task_name":    taskDetail.Name,
			"task_type":    taskDetail.Type,
			"task_status":  taskDetail.Status,
			"platform":     taskDetail.Platform,
			"created_at":   taskDetail.CreatedAt,
			"completed_at": taskDetail.CompletedAt,
			"selectedVMs":  taskDetail.SelectedVMs,
		},
		Sections: []report.ReportSection{
			{
				Title: "任务概览",
				Type:  "summary",
				Data: map[string]interface{}{
					"task_id":          taskID,
					"vmCount":          taskDetail.VMCount,
					"collectedVMCount": taskDetail.CollectedVMCount,
					"progress":         taskDetail.Progress,
				},
			},
			{
				Title: "虚拟机快照",
				Type:  "table",
				Data:  vms,
			},
			{
				Title: "分析结果",
				Type:  "table",
				Data:  analysisData,
			},
		},
	}

	generator := report.NewGenerator(&report.ReportConfig{
		Type:      reportType,
		OutputDir: os.TempDir(),
	})

	filepath, genErr := generator.Generate(reportData)
	if genErr != nil {
		return "", fmt.Errorf("生成任务报告失败: %w", genErr)
	}

	return filepath, nil
}

// StopTask 停止任务
func (a *App) StopTask(id uint) error {
	log := a.log.With(
		applogger.String("method", "StopTask"),
		applogger.Uint("taskID", id))

	log.Info("停止任务")
	if err := a.taskScheduler.Cancel(id); err != nil {
		log.Error("停止任务失败", applogger.Err(err))
		return err
	}

	log.Info("停止任务成功")
	return nil
}

// RetryTask 重试任务
func (a *App) RetryTask(id uint) (uint, error) {
	log := a.log.With(
		applogger.String("method", "RetryTask"),
		applogger.Uint("originalTaskID", id))

	log.Info("重试任务")

	// 从数据库获取任务信息
	dbTask, err := a.repos.AssessmentTask.GetByID(id)
	if err != nil {
		log.Error("任务不存在", applogger.Err(err))
		return 0, fmt.Errorf("任务不存在: %w", err)
	}

	log.Info("找到原任务",
		applogger.Uint("connectionID", dbTask.ConnectionID),
		applogger.String("name", dbTask.Name),
		applogger.String("platform", dbTask.Platform))

	// 重构配置（从数据库字段构建 config）
	config := map[string]interface{}{
		"connection_id":   dbTask.ConnectionID,
		"connection_name": dbTask.ConnectionName,
		"platform":        dbTask.Platform,
	}

	// 如果有虚拟机快照，添加 selectedVMs
	if dbTask.SelectedVMs != "" {
		var vms []string
		json.Unmarshal([]byte(dbTask.SelectedVMs), &vms)
		config["selectedVMs"] = vms
	}

	// 创建新任务
	taskName := dbTask.Name + " (重试)"
	newTask, err := a.taskScheduler.Create(task.TypeCollection, taskName, config)
	if err != nil {
		log.Error("创建重试任务失败", applogger.Err(err))
		return 0, fmt.Errorf("创建重试任务失败: %w", err)
	}

	log.Info("重试任务创建成功", applogger.Uint("newTaskID", newTask.ID))

	go func() {
		_ = a.taskScheduler.Submit(a.ctx, newTask.ID)
	}()

	return newTask.ID, nil
}

// DeleteTask 删除任务
func (a *App) DeleteTask(id uint) error {
	log := a.log.With(
		applogger.String("method", "DeleteTask"),
		applogger.Uint("taskID", id))

	log.Info("删除任务")

	// 先停止任务（如果正在运行）
	_ = a.taskScheduler.Cancel(id)

	// 删除相关的指标数据
	if err := a.repos.Metric.DeleteByTaskID(id); err != nil {
		log.Warn("删除任务指标数据失败", applogger.Err(err))
	}

	// 删除相关的快照数据
	if err := a.repos.TaskVMSnapshot.DeleteByTaskID(id); err != nil {
		log.Warn("删除任务快照失败", applogger.Err(err))
	}

	// 删除相关的分析结果
	if err := a.repos.AnalysisFinding.DeleteByTaskID(id); err != nil {
		log.Warn("删除分析结果失败", applogger.Err(err))
	}

	// 删除任务
	if err := a.repos.AssessmentTask.Delete(id); err != nil {
		log.Error("删除任务失败", applogger.Err(err))
		return err
	}

	log.Info("删除任务成功")
	return nil
}

// TaskLogEntry 任务日志条目
type TaskLogEntry struct {
	Timestamp string `json:"timestamp"`
	Level     string `json:"level"`
	Message   string `json:"message"`
}

// GetTaskLogs 获取任务日志（从数据库读取）
func (a *App) GetTaskLogs(id uint, limit int) ([]TaskLogEntry, error) {
	// 从数据库读取日志
	logs, _, err := a.repos.TaskLog.ListByTaskID(id, limit, 0)
	if err != nil {
		return []TaskLogEntry{}, err
	}

	result := make([]TaskLogEntry, len(logs))
	for i, log := range logs {
		// 使用 Category 作为级别
		level := log.Category
		if level == "" {
			level = "info"
		}

		// 组合标题和消息作为显示内容
		message := log.Message
		if log.Title != "" {
			message = fmt.Sprintf("[%s] %s", log.Title, log.Message)
		}

		result[i] = TaskLogEntry{
			Timestamp: log.CreatedAt.Format("2006-01-02 15:04:05"),
			Level:     level,
			Message:   message,
		}
	}

	return result, nil
}

// ========== 分析服务 ==========

// ZombieVMConfig 僵尸 VM 检测配置
type ZombieVMConfig struct {
	AnalysisDays    int     `json:"analysisDays"`
	CPUThreshold    float64 `json:"cpuThreshold"`
	MemoryThreshold float64 `json:"memoryThreshold"`
	MinConfidence   float64 `json:"minConfidence"`
}

// ZombieVMResult 僵尸 VM 检测结果
type ZombieVMResult struct {
	VMName         string   `json:"vmName"`
	Datacenter     string   `json:"datacenter"`
	Host           string   `json:"host"`
	CPUCount       int32    `json:"cpuCount"`
	MemoryMB       int32    `json:"memoryMb"`
	CPUUsage       float64  `json:"cpuUsage"`
	MemoryUsage    float64  `json:"memoryUsage"`
	Confidence     float64  `json:"confidence"`
	DaysLowUsage   int      `json:"daysLowUsage"`
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

	results, err := a.analyzer.DetectZombieVMs(0, connectionID, zombieConfig)
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
	AnalysisDays int     `json:"analysisDays"`
	BufferRatio  float64 `json:"bufferRatio"`
}

// RightSizeResult Right Size 结果
type RightSizeResult struct {
	VMName              string  `json:"vmName"`
	Datacenter          string  `json:"datacenter"`
	CurrentCPU          int32   `json:"currentCpu"`
	CurrentMemoryMB     int32   `json:"currentMemoryMb"`
	RecommendedCPU      int32   `json:"recommendedCpu"`
	RecommendedMemoryMB int32   `json:"recommendedMemoryMb"`
	AdjustmentType      string  `json:"adjustmentType"`
	RiskLevel           string  `json:"riskLevel"`
	EstimatedSaving     string  `json:"estimatedSaving"`
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

	results, err := a.analyzer.AnalyzeRightSize(0, connectionID, rightSizeConfig)
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
	AnalysisDays int     `json:"analysisDays"`
	MinStability float64 `json:"minStability"`
}

// TidalResult 潮汐检测结果
type TidalResult struct {
	VMName          string  `json:"vmName"`
	Datacenter      string  `json:"datacenter"`
	Pattern         string  `json:"pattern"`
	StabilityScore  float64 `json:"stabilityScore"`
	PeakHours       []int   `json:"peakHours"`
	PeakDays        []int   `json:"peakDays"`
	Recommendation  string  `json:"recommendation"`
	EstimatedSaving string  `json:"estimatedSaving"`
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

	results, err := a.analyzer.DetectTidalPattern(0, connectionID, tidalConfig)
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
	ConnectionID         uint     `json:"connectionId"`
	ConnectionName       string   `json:"connectionName"`
	OverallScore         float64  `json:"overallScore"`
	HealthLevel          string   `json:"healthLevel"`
	ResourceBalance      float64  `json:"resourceBalance"`
	OvercommitRisk       float64  `json:"overcommitRisk"`
	HotspotConcentration float64  `json:"hotspotConcentration"`
	ClusterCount         int      `json:"clusterCount"`
	HostCount            int      `json:"hostCount"`
	VMCount              int      `json:"vmCount"`
	RiskItems            []string `json:"riskItems"`
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
		ClusterCount:         result.ClusterCount,
		HostCount:            result.HostCount,
		VMCount:              result.VMCount,
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
		ClusterCount:         result.ClusterCount,
		HostCount:            result.HostCount,
		VMCount:              result.VMCount,
		RiskItems:            result.RiskItems,
		Recommendations:      result.Recommendations,
	}

	return a.resultStorage.SaveHealthScoreResult(0, internalResult)
}

// CreateAlert 创建告警
type CreateAlertRequest struct {
	TargetType string `json:"targetType"` // cluster, host, vm
	TargetKey  string `json:"targetKey"`
	TargetName string `json:"targetName"`
	AlertType  string `json:"alertType"` // zombie, overprovisioned, etc.
	Severity   string `json:"severity"`  // info, warning, critical
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

// GetVMList 获取虚拟机列表（返回标准格式 JSON 字符串）
func (a *App) GetVMList(connectionID uint) (string, error) {
	vms, err := a.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return "", fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	// 转换为 VMListItem 格式（与 ListVMs 保持一致）
	result := make([]VMListItem, len(vms))
	for i, v := range vms {
		result[i] = VMListItem{
			ID:              v.ID,
			Name:            v.Name,
			Datacenter:      v.Datacenter,
			UUID:            v.UUID,
			CPUCount:        v.CpuCount,
			MemoryGB:        float64(v.MemoryMB) / 1024, // MB -> GB
			PowerState:      v.PowerState,
			ConnectionState: v.ConnectionState,
			IPAddress:       v.IPAddress,
			GuestOS:         v.GuestOS,
			HostName:        v.HostName,
			OverallStatus:   v.OverallStatus,
			CollectedAt:     v.CollectedAt.Format("2006-01-02 15:04:05"),
		}
	}

	data, err := json.Marshal(result)
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
	TotalCPU      int64   `json:"totalCpu"`
	TotalMemoryGB float64 `json:"totalMemoryGb"`
	NumHosts      int32   `json:"numHosts"`
	NumVMs        int     `json:"numVMs"`
	Status        string  `json:"status"`
	CollectedAt   string  `json:"collectedAt"`
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
	IPAddress     string  `json:"ipAddress"`
	CPUCores      int32   `json:"cpuCores"`
	CPUMHz        int32   `json:"cpuMhz"`
	MemoryGB      float64 `json:"memoryGb"`
	NumVMs        int     `json:"numVMs"`
	PowerState    string  `json:"powerState"`
	OverallStatus string  `json:"overallStatus"`
	CollectedAt   string  `json:"collectedAt"`
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
	ID              uint    `json:"id"`
	Name            string  `json:"name"`
	Datacenter      string  `json:"datacenter"`
	UUID            string  `json:"uuid"`
	CPUCount        int32   `json:"cpuCount"`
	MemoryGB        float64 `json:"memoryGb"`
	PowerState      string  `json:"powerState"`
	ConnectionState string  `json:"connectionState"`
	IPAddress       string  `json:"ipAddress"`
	GuestOS         string  `json:"guestOs"`
	HostName        string  `json:"hostName"`
	OverallStatus   string  `json:"overallStatus"`
	CollectedAt     string  `json:"collectedAt"`
}

// TaskVMListResponse 任务虚拟机列表响应（包含分页信息）
type TaskVMListResponse struct {
	VMs   []VMListItem `json:"vms"`
	Total int64        `json:"total"`
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
			ID:              v.ID,
			Name:            v.Name,
			Datacenter:      v.Datacenter,
			UUID:            v.UUID,
			CPUCount:        v.CpuCount,
			MemoryGB:        float64(v.MemoryMB) / 1024,
			PowerState:      v.PowerState,
			ConnectionState: v.ConnectionState,
			IPAddress:       v.IPAddress,
			GuestOS:         v.GuestOS,
			HostName:        v.HostName,
			OverallStatus:   v.OverallStatus,
			CollectedAt:     v.CollectedAt.Format("2006-01-02 15:04:05"),
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
	VMID       uint          `json:"vmId"`
	VMName     string        `json:"vmName"`
	MetricType string        `json:"metricType"`
	StartTime  string        `json:"startTime"`
	EndTime    string        `json:"endTime"`
	Data       []MetricPoint `json:"data"`
}

// GetMetrics 获取指标数据
func (a *App) GetMetrics(taskID, vmID uint, metricType string, days int) (*MetricsData, error) {
	// 获取 VM 信息
	vm, err := a.repos.VM.GetByID(vmID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机失败: %w", err)
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -days)

	// 使用带 TaskID 的查询方法
	metrics, err := a.repos.Metric.ListByTaskAndVMAndType(taskID, vmID, metricType, startTime, endTime)
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
	ConnectionID uint     `json:"connectionId"`
	ReportTypes  []string `json:"reportTypes"` // json, html
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
				"vmCount":   0,
				"hostCount": 0,
			},
		},
	}
}

// ========== 分析服务（统一入口） ==========

// AnalysisRequest 分析请求
type AnalysisRequest struct {
	ConnectionID  uint                   `json:"connectionId"`
	AnalysisTypes []string               `json:"analysisTypes"` // zombie, rightsize, tidal, health
	Config        map[string]interface{} `json:"config"`
}

// AnalysisResponse 分析响应
type AnalysisResponse struct {
	TaskID  uint                   `json:"taskId"`
	Status  string                 `json:"status"`
	Results map[string]interface{} `json:"results,omitempty"`
}

// RunAnalysis 统一分析入口（同步执行）
func (a *App) RunAnalysis(req AnalysisRequest) (*AnalysisResponse, error) {
	connectionID := req.ConnectionID
	results := make(map[string]interface{})

	for _, analysisType := range req.AnalysisTypes {
		switch analysisType {
		case "zombie":
			config := parseZombieVMConfigFromMap(req.Config)
			result, err := a.DetectZombieVMs(connectionID, config)
			if err != nil {
				return nil, fmt.Errorf("僵尸 VM 检测失败: %w", err)
			}
			results["zombie"] = result

		case "rightsize":
			config := parseRightSizeConfigFromMap(req.Config)
			result, err := a.AnalyzeRightSize(connectionID, config)
			if err != nil {
				return nil, fmt.Errorf("Right Size 分析失败: %w", err)
			}
			results["rightsize"] = result

		case "tidal":
			config := parseTidalConfigFromMap(req.Config)
			result, err := a.DetectTidalPattern(connectionID, config)
			if err != nil {
				return nil, fmt.Errorf("潮汐检测失败: %w", err)
			}
			results["tidal"] = result

		case "health":
			result, err := a.AnalyzeHealthScore(connectionID)
			if err != nil {
				return nil, fmt.Errorf("健康度分析失败: %w", err)
			}
			results["health"] = result
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
	if v, ok := config["analysisDays"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["cpuThreshold"].(float64); ok {
		result.CPUThreshold = v
	}
	if v, ok := config["memoryThreshold"].(float64); ok {
		result.MemoryThreshold = v
	}
	if v, ok := config["minConfidence"].(float64); ok {
		result.MinConfidence = v
	}
	return result
}

func parseRightSizeConfigFromMap(config map[string]interface{}) RightSizeConfig {
	result := RightSizeConfig{}
	if v, ok := config["analysisDays"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["bufferRatio"].(float64); ok {
		result.BufferRatio = v
	}
	return result
}

func parseTidalConfigFromMap(config map[string]interface{}) TidalConfig {
	result := TidalConfig{}
	if v, ok := config["analysisDays"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["minStability"].(float64); ok {
		result.MinStability = v
	}
	return result
}

func configUint(config map[string]interface{}, key string) uint {
	v, ok := config[key]
	if !ok {
		return 0
	}

	switch val := v.(type) {
	case uint:
		return val
	case int:
		if val > 0 {
			return uint(val)
		}
	case int64:
		if val > 0 {
			return uint(val)
		}
	case float64:
		if val > 0 {
			return uint(val)
		}
	}

	return 0
}

func configInt(config map[string]interface{}, key string) int {
	v, ok := config[key]
	if !ok {
		return 0
	}

	switch val := v.(type) {
	case int:
		return val
	case int32:
		return int(val)
	case int64:
		return int(val)
	case float64:
		return int(val)
	default:
		return 0
	}
}

func configStringSlice(config map[string]interface{}, key string) []string {
	v, ok := config[key]
	if !ok {
		return []string{}
	}

	if direct, ok := v.([]string); ok {
		return direct
	}

	if rawList, ok := v.([]interface{}); ok {
		result := make([]string, 0, len(rawList))
		for _, item := range rawList {
			if s, ok := item.(string); ok {
				result = append(result, s)
			}
		}
		return result
	}

	return []string{}
}

// AnalysisSummary 分析汇总
type AnalysisSummary struct {
	ConnectionID     uint           `json:"connectionId"`
	VMCount          int64          `json:"vmCount"`
	ZombieVMs        int            `json:"zombieVMs"`
	RightSizeVMs     int            `json:"rightSizeVMs"`
	TidalVMs         int            `json:"tidalVMs"`
	HealthScore      float64        `json:"healthScore"`
	TotalSavings     string         `json:"totalSavings"`
	LastAnalyzed     string         `json:"lastAnalyzed"`
	RiskDistribution map[string]int `json:"riskDistribution"`
}

// GetAnalysisSummary 获取分析汇总
func (a *App) GetAnalysisSummary(connectionID uint) (*AnalysisSummary, error) {
	// 获取 VM 总数
	var vmCount int64
	storage.DB.Model(&storage.VM{}).Where("connection_id = ?", connectionID).Count(&vmCount)

	// 统计各类分析结果
	var zombieCount, rightSizeCount, tidalCount int64
	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "zombie", time.Now().AddDate(0, 0, -7)).
		Count(&zombieCount)

	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "rightsize", time.Now().AddDate(0, 0, -7)).
		Count(&rightSizeCount)

	storage.DB.Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "tidal", time.Now().AddDate(0, 0, -7)).
		Count(&tidalCount)

	// 获取最新健康评分
	var latestHealth storage.AnalysisResult
	var healthScore float64 = 0
	storage.DB.Where("analysis_type = ? AND created_at > ?", "health", time.Now().AddDate(0, 0, -30)).
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
		ConnectionID: connectionID,
		VMCount:      vmCount,
		ZombieVMs:    int(zombieCount),
		RightSizeVMs: int(rightSizeCount),
		TidalVMs:     int(tidalCount),
		HealthScore:  healthScore,
		TotalSavings: totalSavings,
		LastAnalyzed: latestHealth.CreatedAt.Format("2006-01-02 15:04:05"),
		RiskDistribution: map[string]int{
			"high":   int(zombieCount),
			"medium": int(rightSizeCount),
			"low":    int(vmCount - zombieCount - rightSizeCount),
		},
	}, nil
}

// ========== 报告服务扩展 ==========

// ReportListItem 报告列表项
type ReportListItem struct {
	ID           uint   `json:"id"`
	Type         string `json:"type"`
	Name         string `json:"name"`
	ConnectionID uint   `json:"connectionId"`
	Status       string `json:"status"`
	Format       string `json:"format"`
	FilePath     string `json:"filePath"`
	FileSize     int64  `json:"fileSize"`
	CreatedAt    string `json:"createdAt"`
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
			Type:         r.ReportType,
			Name:         r.Title,
			ConnectionID: r.TaskID, // 改为 TaskID
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
	ConnectionID uint                   `json:"connectionId"`
	Status       string                 `json:"status"`
	Format       string                 `json:"format"`
	FilePath     string                 `json:"filePath"`
	FileSize     int64                  `json:"fileSize"`
	CreatedAt    string                 `json:"createdAt"`
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
		Type:         r.ReportType,
		Name:         r.Title,
		ConnectionID: r.TaskID,
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
	ReportID  uint   `json:"reportId"`
	Format    string `json:"format"`    // json, html, xlsx
	OutputDir string `json:"outputDir"` // 可选，默认使用系统临时目录
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
		reportData = a.buildReportDataFromDB(originalReport.TaskID)
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
		Title:        fmt.Sprintf("JustFit 分析报告 - 连接ID: %d", connectionID),
		ConnectionID: connectionID,
		Sections:     sections,
	}
}

// ========== 系统配置服务 ==========

// SystemSettings 系统配置
type SystemSettings struct {
	// 分析配置
	DefaultAnalysisDays    int     `json:"defaultAnalysisDays"`
	DefaultCPUThreshold    float64 `json:"defaultCpuThreshold"`
	DefaultMemoryThreshold float64 `json:"defaultMemoryThreshold"`
	DefaultBufferRatio     float64 `json:"defaultBufferRatio"`

	// 采集配置
	DefaultMetricsDays    int `json:"defaultMetricsDays"`
	CollectionConcurrency int `json:"collectionConcurrency"`

	// 报告配置
	DefaultReportFormat string `json:"defaultReportFormat"`
	ReportOutputDir     string `json:"reportOutputDir"`

	// 界面配置
	Theme               string `json:"theme"`
	Language            string `json:"language"`
	AutoRefreshInterval int    `json:"autoRefreshInterval"`
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
		"version":    version.Version,
		"go_version": stdruntime.Version(),
		"os":         runtime.Environment(a.ctx).Platform,
		"arch":       stdruntime.GOARCH,
		"timestamp":  time.Now().Format(time.RFC3339),
	}
	sysInfoData, _ := json.MarshalIndent(sysInfo, "", "  ")
	_ = os.WriteFile(filepath.Join(tmpDir, "system_info.json"), sysInfoData, 0644)

	// 2. 数据库信息（不包含敏感数据）
	// 使用 appdir 模块获取数据库路径
	dbPath := appdir.MustGetDBPath()
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
	TargetType     string  `json:"targetType"`
	TargetKey      string  `json:"targetKey"`
	TargetName     string  `json:"targetName"`
	AlertType      string  `json:"alertType"`
	Severity       string  `json:"severity"`
	Title          string  `json:"title"`
	Message        string  `json:"message"`
	Acknowledged   bool    `json:"acknowledged"`
	AcknowledgedAt *string `json:"acknowledgedAt,omitempty"`
	CreatedAt      string  `json:"createdAt"`
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
	ID           uint `json:"id"`
	Acknowledged bool `json:"acknowledged"`
}

// MarkAlert 标记告警 (空操作，因为新设计中不再需要确认功能)
func (a *App) MarkAlert(req MarkAlertRequest) error {
	// 新设计中告警合并到 AnalysisFinding，不再需要确认功能
	return nil
}

// AlertStats 告警统计
type AlertStats struct {
	Total          int64            `json:"total"`
	Unacknowledged int64            `json:"unacknowledged"`
	BySeverity     map[string]int64 `json:"bySeverity"`
	ByType         map[string]int64 `json:"byType"`
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
