package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"justfit/internal/analyzer"
	"justfit/internal/connector"
	"justfit/internal/etl"
	"justfit/internal/report"
	"justfit/internal/security"
	"justfit/internal/service"
	"justfit/internal/storage"
	"justfit/internal/task"
)

// TestApp 测试应用结构
type TestApp struct {
	connMgr       *connector.ConnectorManager
	repos         *storage.Repositories
	collector     *etl.Collector
	analyzer      *analyzer.Engine
	credentialMgr *security.CredentialManager
	taskScheduler *task.Scheduler
}

// NewTestApp 创建测试应用
func NewTestApp() *TestApp {
	return &TestApp{}
}

// Setup 初始化测试环境
func (a *TestApp) Setup() error {
	// 初始化数据库
	tmpDir := os.TempDir()
	cfg := &storage.Config{DataDir: tmpDir}
	if err := storage.Init(cfg); err != nil {
		return fmt.Errorf("初始化数据库失败: %w", err)
	}

	// 创建连接器管理器
	a.connMgr = connector.NewConnectorManager()

	// 创建数据仓储
	a.repos = storage.NewRepositories()

	// 创建采集器
	a.collector = etl.NewCollector(a.connMgr, a.repos)

	// 创建分析引擎
	a.analyzer = analyzer.NewEngine(a.repos)

	// 创建凭据管理器
	credMgr, err := security.NewCredentialManager(tmpDir)
	if err != nil {
		return fmt.Errorf("创建凭据管理器失败: %w", err)
	}
	a.credentialMgr = credMgr

	// 创建任务调度器
	a.taskScheduler = task.NewScheduler(3)

	// 注册任务执行器
	collectionExecutor := service.NewCollectionExecutor(a.collector, a.repos)
	analysisExecutor := service.NewAnalysisExecutor(a.analyzer, a.repos)

	a.taskScheduler.RegisterExecutor(task.TypeCollection, collectionExecutor)
	a.taskScheduler.RegisterExecutor(task.TypeAnalysis, analysisExecutor)

	return nil
}

// Teardown 清理测试环境
func (a *TestApp) Teardown() {
	if a.taskScheduler != nil {
		_ = a.taskScheduler.Shutdown(5 * time.Second)
	}
	if a.connMgr != nil {
		a.connMgr.CloseAll()
	}
	storage.Close()
}

// TestConnectionManagement 测试连接管理
func (a *TestApp) TestConnectionManagement() error {
	fmt.Println("\n=== 测试连接管理 ===")

	// 创建测试连接
	conn := &storage.Connection{
		Name:     "测试连接",
		Platform: "vcenter",
		Host:     "192.168.1.100",
		Port:     443,
		Username: "administrator@vsphere.local",
		Password: "password123",
		Insecure: true,
		Status:   "disconnected",
	}

	err := a.repos.Connection.Create(conn)
	if err != nil {
		return fmt.Errorf("创建连接失败: %w", err)
	}
	fmt.Printf("✓ 创建连接成功, ID: %d\n", conn.ID)

	// 列出连接
	conns, err := a.repos.Connection.List()
	if err != nil {
		return fmt.Errorf("列出连接失败: %w", err)
	}
	fmt.Printf("✓ 列出连接成功, 数量: %d\n", len(conns))

	// 获取连接详情
	retrievedConn, err := a.repos.Connection.GetByID(conn.ID)
	if err != nil {
		return fmt.Errorf("获取连接详情失败: %w", err)
	}
	fmt.Printf("✓ 获取连接详情成功, 名称: %s\n", retrievedConn.Name)

	// 更新连接
	conn.Name = "测试连接（已更新）"
	err = a.repos.Connection.Update(conn)
	if err != nil {
		return fmt.Errorf("更新连接失败: %w", err)
	}
	fmt.Printf("✓ 更新连接成功\n")

	// 删除连接
	err = a.repos.Connection.Delete(conn.ID)
	if err != nil {
		return fmt.Errorf("删除连接失败: %w", err)
	}
	fmt.Printf("✓ 删除连接成功\n")

	return nil
}

// TestTaskManagement 测试任务管理
func (a *TestApp) TestTaskManagement() error {
	fmt.Println("\n=== 测试任务管理 ===")

	ctx := context.Background()

	// 创建采集任务
	taskConfig := map[string]interface{}{
		"connection_id": float64(1),
		"data_types":    []string{"clusters", "hosts"},
		"metrics_days":  float64(7),
	}

	t, err := a.taskScheduler.Create(task.TypeCollection, "测试采集任务", taskConfig)
	if err != nil {
		return fmt.Errorf("创建任务失败: %w", err)
	}
	fmt.Printf("✓ 创建任务成功, ID: %d\n", t.ID)

	// 列出任务
	tasks, err := a.taskScheduler.List(task.StatusPending, 10, 0)
	if err != nil {
		return fmt.Errorf("列出任务失败: %w", err)
	}
	fmt.Printf("✓ 列出任务成功, 数量: %d\n", len(tasks))

	// 获取任务详情
	retrievedTask, err := a.taskScheduler.Get(t.ID)
	if err != nil {
		return fmt.Errorf("获取任务详情失败: %w", err)
	}
	fmt.Printf("✓ 获取任务详情成功, 名称: %s\n", retrievedTask.Name)

	// 提交任务
	go func() {
		_ = a.taskScheduler.Submit(ctx, t.ID)
	}()

	// 等待一小段时间让任务开始执行
	time.Sleep(100 * time.Millisecond)

	// 停止服务
	err = a.taskScheduler.Cancel(t.ID)
	if err != nil {
		// 任务可能已完成或失败，这是预期的
		fmt.Printf("✓ 停止任务: %v\n", err)
	} else {
		fmt.Printf("✓ 停止任务成功\n")
	}

	return nil
}

// TestSettingsManagement 测试系统配置
func (a *TestApp) TestSettingsManagement() error {
	fmt.Println("\n=== 测试系统配置 ===")

	// 使用时间戳创建唯一的键
	testKey := fmt.Sprintf("test_key_%d", time.Now().UnixNano())

	// 设置配置
	err := a.repos.Settings.Set(testKey, "test_value", "string")
	if err != nil {
		return fmt.Errorf("设置配置失败: %w", err)
	}
	fmt.Printf("✓ 设置配置成功\n")

	// 获取配置
	setting, err := a.repos.Settings.Get(testKey)
	if err != nil {
		return fmt.Errorf("获取配置失败: %w", err)
	}
	fmt.Printf("✓ 获取配置成功, 值: %s\n", setting.Value)

	// 获取所有配置
	settings, err := a.repos.Settings.GetAll()
	if err != nil {
		return fmt.Errorf("获取所有配置失败: %w", err)
	}
	fmt.Printf("✓ 获取所有配置成功, 数量: %d\n", len(settings))

	// 删除配置
	err = a.repos.Settings.Delete(testKey)
	if err != nil {
		return fmt.Errorf("删除配置失败: %w", err)
	}
	fmt.Printf("✓ 删除配置成功\n")

	return nil
}

// TestReportGeneration 测试报告生成
func (a *TestApp) TestReportGeneration() error {
	fmt.Println("\n=== 测试报告生成 ===")

	// 创建报告生成器
	generator := report.NewGenerator(&report.ReportConfig{
		Type:      report.ReportTypeJSON,
		OutputDir: os.TempDir(),
	})

	// 准备报告数据
	reportData := &report.ReportData{
		Title:        "测试报告",
		ConnectionID: 1,
		Sections: []report.ReportSection{
			{
				Title:   "概述",
				Content: "这是一个测试报告",
				Type:    "text",
			},
			{
				Title: "数据汇总",
				Type:  "summary",
				Data: map[string]interface{}{
					"vmCount":   100,
					"hostCount": 10,
				},
			},
		},
	}

	// 生成报告
	filepath, err := generator.Generate(reportData)
	if err != nil {
		return fmt.Errorf("生成报告失败: %w", err)
	}
	fmt.Printf("✓ 生成报告成功, 路径: %s\n", filepath)

	// 验证文件存在
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		return fmt.Errorf("报告文件不存在: %s", filepath)
	}
	fmt.Printf("✓ 报告文件存在验证成功\n")

	// 清理测试文件
	_ = os.Remove(filepath)

	return nil
}

// TestAnalysisFindingManagement 测试分析发现管理
func (a *TestApp) TestAnalysisFindingManagement() error {
	fmt.Println("\n=== 测试分析发现管理 ===")

	// 创建测试任务以获取 TaskID
	task := &storage.AssessmentTask{
		Name:         "测试任务",
		ConnectionID: 1,
		Status:       "pending",
	}
	err := a.repos.AssessmentTask.Create(task)
	if err != nil {
		return fmt.Errorf("创建测试任务失败: %w", err)
	}
	defer func() {
		_ = a.repos.AssessmentTask.Delete(task.ID)
	}()

	// 创建分析发现
	finding := &storage.AnalysisFinding{
		TaskID:      task.ID,
		JobType:     "zombie",
		TargetType:  "vm",
		TargetKey:   "vm-123",
		TargetName:  "test-vm",
		Severity:    "warning",
		Category:    "resource_waste",
		Title:       "测试告警",
		Description: "这是一个测试告警",
	}

	err = a.repos.AnalysisFinding.Create(finding)
	if err != nil {
		return fmt.Errorf("创建分析发现失败: %w", err)
	}
	fmt.Printf("✓ 创建分析发现成功, ID: %d\n", finding.ID)

	// 列出分析发现
	findings, err := a.repos.AnalysisFinding.ListByTaskID(task.ID)
	if err != nil {
		return fmt.Errorf("列出分析发现失败: %w", err)
	}
	fmt.Printf("✓ 列出分析发现成功, 数量: %d\n", len(findings))

	return nil
}

// TestCredentialManagement 测试凭据管理
func (a *TestApp) TestCredentialManagement() error {
	fmt.Println("\n=== 测试凭据管理 ===")

	// 创建测试连接 - 先保存到数据库获取 ID
	conn := &storage.Connection{
		Name:     "加密测试",
		Platform: "vcenter",
		Host:     "192.168.1.100",
		Port:     443,
		Username: "admin",
		Password: "secret_password_123",
		Insecure: true,
	}

	// 先保存到数据库
	err := a.repos.Connection.Create(conn)
	if err != nil {
		return fmt.Errorf("保存连接到数据库失败: %w", err)
	}

	// 保存凭据（密码将被加密）
	err = a.credentialMgr.SaveConnection(conn)
	if err != nil {
		return fmt.Errorf("保存凭据失败: %w", err)
	}
	fmt.Printf("✓ 保存凭据（密码加密）成功\n")

	// 重新从存储获取连接
	retrievedConn, err := a.repos.Connection.GetByID(conn.ID)
	if err != nil {
		return fmt.Errorf("获取连接失败: %w", err)
	}

	// 加载密码（解密）
	err = a.credentialMgr.LoadConnection(retrievedConn)
	if err != nil {
		return fmt.Errorf("加载密码失败: %w", err)
	}

	if retrievedConn.Password != "secret_password_123" {
		return fmt.Errorf("密码解密不匹配: 期望 secret_password_123, 实际 %s", retrievedConn.Password)
	}
	fmt.Printf("✓ 密码加密/解密验证成功\n")

	// 清理
	_ = a.repos.Connection.Delete(conn.ID)

	return nil
}

// TestDatabaseOperations 测试数据库操作
func (a *TestApp) TestDatabaseOperations() error {
	fmt.Println("\n=== 测试数据库操作 ===")

	// 创建测试连接
	conn := &storage.Connection{
		Name:     "DB测试",
		Platform: "vcenter",
		Host:     "192.168.1.200",
		Port:     443,
		Username: "admin",
		Password: "password",
		Insecure: true,
	}
	err := a.repos.Connection.Create(conn)
	if err != nil {
		return fmt.Errorf("创建连接失败: %w", err)
	}

	// 创建测试集群
	cluster := &storage.Cluster{
		ConnectionID: conn.ID,
		ClusterKey:   "cluster-1",
		Name:         "测试集群",
		Datacenter:   "DC1",
		TotalCpu:     100000,
		TotalMemory:  1024 * 1024 * 1024 * 100,
		NumHosts:     5,
		NumVMs:       50,
		Status:       "green",
		CollectedAt:  time.Now(),
	}
	err = a.repos.Cluster.Create(cluster)
	if err != nil {
		return fmt.Errorf("创建集群失败: %w", err)
	}
	fmt.Printf("✓ 创建集群成功\n")

	// 查询集群
	clusters, err := a.repos.Cluster.ListByConnectionID(conn.ID)
	if err != nil {
		return fmt.Errorf("查询集群失败: %w", err)
	}
	if len(clusters) != 1 {
		return fmt.Errorf("集群数量不匹配: 期望 1, 实际 %d", len(clusters))
	}
	fmt.Printf("✓ 查询集群成功\n")

	// 创建测试虚拟机
	vm := &storage.VM{
		ConnectionID: conn.ID,
		VMKey:        "vm-1",
		UUID:         "uuid-12345",
		Name:         "测试虚拟机",
		Datacenter:   "DC1",
		CpuCount:     2,
		MemoryMB:     4096,
		PowerState:   "poweredOn",
		GuestOS:      "ubuntu64Guest",
		HostName:     "esxi-1",
		CollectedAt:  time.Now(),
	}
	err = a.repos.VM.Create(vm)
	if err != nil {
		return fmt.Errorf("创建虚拟机失败: %w", err)
	}
	fmt.Printf("✓ 创建虚拟机成功\n")

	// 查询虚拟机
	vms, err := a.repos.VM.ListByConnectionID(conn.ID)
	if err != nil {
		return fmt.Errorf("查询虚拟机失败: %w", err)
	}
	if len(vms) != 1 {
		return fmt.Errorf("虚拟机数量不匹配: 期望 1, 实际 %d", len(vms))
	}
	fmt.Printf("✓ 查询虚拟机成功\n")

	// 测试 GetByID
	retrievedVM, err := a.repos.VM.GetByID(vm.ID)
	if err != nil {
		return fmt.Errorf("通过ID获取虚拟机失败: %w", err)
	}
	if retrievedVM.Name != "测试虚拟机" {
		return fmt.Errorf("虚拟机名称不匹配")
	}
	fmt.Printf("✓ 通过ID获取虚拟机成功\n")

	// 创建测试任务以获取 TaskID
	task := &storage.AssessmentTask{
		Name:         "指标测试任务",
		ConnectionID: conn.ID,
		Status:       "pending",
	}
	err = a.repos.AssessmentTask.Create(task)
	if err != nil {
		return fmt.Errorf("创建测试任务失败: %w", err)
	}
	defer func() {
		_ = a.repos.AssessmentTask.Delete(task.ID)
	}()

	// 创建指标
	metric := &storage.VMMetric{
		TaskID:     task.ID,
		VMID:       vm.ID,
		MetricType: "cpu",
		Timestamp:  time.Now(),
		Value:      50.5,
	}
	err = a.repos.VMMetric.Create(metric)
	if err != nil {
		return fmt.Errorf("创建指标失败: %w", err)
	}
	fmt.Printf("✓ 创建指标成功\n")

	// 查询指标（taskID=0 表示查询所有任务）
	metrics, err := a.repos.VMMetric.ListByTaskAndVMAndType(0, vm.ID, "cpu", time.Now().Add(-1*time.Hour), time.Now())
	if err != nil {
		return fmt.Errorf("查询指标失败: %w", err)
	}
	if len(metrics) != 1 {
		return fmt.Errorf("指标数量不匹配: 期望 1, 实际 %d", len(metrics))
	}
	fmt.Printf("✓ 查询指标成功\n")

	// 创建分析发现
	finding := &storage.AnalysisFinding{
		TaskID:      task.ID,
		JobType:     "zombie",
		TargetType:  "vm",
		TargetKey:   vm.VMKey,
		TargetName:  vm.Name,
		Severity:    "warning",
		Category:    "zombie_vm",
		Title:       "僵尸虚拟机",
		Description: `{"cpu_usage": 5.0, "confidence": 0.9}`,
		Action:      "建议删除",
		Reason:      "长期低使用率",
		Details:     `{"cpu_usage": 5.0, "confidence": 0.9}`,
	}
	err = a.repos.AnalysisFinding.Create(finding)
	if err != nil {
		return fmt.Errorf("创建分析发现失败: %w", err)
	}
	fmt.Printf("✓ 创建分析发现成功\n")

	return nil
}

// main 主函数
func main() {
	app := NewTestApp()

	fmt.Println("========================================")
	fmt.Println("JustFit 后端 API 集成测试")
	fmt.Println("========================================")

	// 初始化
	err := app.Setup()
	if err != nil {
		fmt.Printf("❌ 初始化失败: %v\n", err)
		os.Exit(1)
	}
	defer app.Teardown()
	fmt.Println("✓ 初始化成功")

	// 运行测试
	tests := []struct {
		name string
		fn   func() error
	}{
		{"连接管理", app.TestConnectionManagement},
		{"任务管理", app.TestTaskManagement},
		{"系统配置", app.TestSettingsManagement},
		{"报告生成", app.TestReportGeneration},
		{"分析发现管理", app.TestAnalysisFindingManagement},
		{"凭据管理", app.TestCredentialManagement},
		{"数据库操作", app.TestDatabaseOperations},
	}

	passed := 0
	failed := 0

	for _, tt := range tests {
		if err := tt.fn(); err != nil {
			fmt.Printf("❌ %s测试失败: %v\n", tt.name, err)
			failed++
		} else {
			passed++
		}
	}

	// 输出测试结果
	fmt.Println("\n========================================")
	fmt.Printf("测试结果: %d 通过, %d 失败\n", passed, failed)
	fmt.Println("========================================")

	if failed > 0 {
		os.Exit(1)
	}
}
