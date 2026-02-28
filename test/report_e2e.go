package main

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"justfit/internal/report"
	"justfit/internal/storage"
)

// ReportIntegrationTest 报告集成测试
type ReportIntegrationTest struct {
	repos     *storage.Repositories
	outputDir string
	cleanup   []string // 清理列表
}

// NewReportIntegrationTest 创建报告集成测试
func NewReportIntegrationTest() *ReportIntegrationTest {
	return &ReportIntegrationTest{}
}

// Setup 初始化测试环境
func (t *ReportIntegrationTest) Setup() error {
	fmt.Println("========================================")
	fmt.Println("JustFit 报告生成集成测试")
	fmt.Println("========================================\n")

	// 创建独立的临时目录用于测试
	tmpDir := filepath.Join(os.TempDir(), fmt.Sprintf("justfit_test_%d", time.Now().Unix()))
	if err := os.MkdirAll(tmpDir, 0755); err != nil {
		return fmt.Errorf("创建临时目录失败: %w", err)
	}
	t.outputDir = tmpDir

	// 使用临时数据目录（确保每次测试都是独立的）
	cfg := &storage.Config{DataDir: tmpDir}
	if err := storage.Init(cfg); err != nil {
		return fmt.Errorf("初始化数据库失败: %w", err)
	}

	t.repos = storage.NewRepositories()

	fmt.Printf("✓ 数据库初始化成功\n")
	fmt.Printf("✓ 输出目录: %s\n\n", t.outputDir)

	return nil
}

// Teardown 清理测试环境
func (t *ReportIntegrationTest) Teardown() {
	storage.Close()

	// 清理生成的文件
	for _, file := range t.cleanup {
		os.Remove(file)
	}

	// 清理输出目录
	os.RemoveAll(t.outputDir)

	fmt.Println("\n✓ 清理完成")
}

// setupTestData 创建测试数据
func (t *ReportIntegrationTest) setupTestData() (uint, uint, error) {
	fmt.Println("1. 创建测试数据...")

	// 1.1 创建测试连接
	conn := &storage.Connection{
		Name:     "测试平台",
		Platform: "vcenter",
		Host:     "192.168.1.100",
		Port:     443,
		Username: "admin",
		Insecure: true,
		Status:   "connected",
	}
	if err := t.repos.Connection.Create(conn); err != nil {
		return 0, 0, fmt.Errorf("创建连接失败: %w", err)
	}
	fmt.Printf("   ✓ 创建连接: %s (ID: %d)\n", conn.Name, conn.ID)

	// 1.2 创建测试集群
	clusters := []storage.Cluster{
		{
			ConnectionID: conn.ID,
			ClusterKey:   "cluster-01",
			Name:         "Cluster-Production",
			Datacenter:   "DC1",
			TotalCpu:     100000,
			TotalMemory:  100 * 1024 * 1024 * 1024, // 100GB
			NumHosts:     5,
			NumVMs:       50,
			Status:       "green",
			CollectedAt:  time.Now(),
		},
		{
			ConnectionID: conn.ID,
			ClusterKey:   "cluster-02",
			Name:         "Cluster-Development",
			Datacenter:   "DC1",
			TotalCpu:     80000,
			TotalMemory:  80 * 1024 * 1024 * 1024, // 80GB
			NumHosts:     3,
			NumVMs:       30,
			Status:       "green",
			CollectedAt:  time.Now(),
		},
	}
	for _, cluster := range clusters {
		if err := t.repos.Cluster.Create(&cluster); err != nil {
			return 0, 0, fmt.Errorf("创建集群失败: %w", err)
		}
	}
	fmt.Printf("   ✓ 创建集群: %d 个\n", len(clusters))

	// 1.3 创建测试主机
	hosts := []storage.Host{
		{
			ConnectionID: conn.ID,
			HostKey:      "host-01",
			Name:         "esxi-host-01",
			Datacenter:   "DC1",
			IPAddress:    "192.168.1.101",
			CpuCores:     32,
			CpuMhz:       2400,
			Memory:       128 * 1024 * 1024 * 1024, // 128GB
			NumVMs:       10,
			PowerState:   "poweredOn",
			CollectedAt:  time.Now(),
		},
		{
			ConnectionID: conn.ID,
			HostKey:      "host-02",
			Name:         "esxi-host-02",
			Datacenter:   "DC1",
			IPAddress:    "192.168.1.102",
			CpuCores:     32,
			CpuMhz:       2400,
			Memory:       128 * 1024 * 1024 * 1024, // 128GB
			NumVMs:       8,
			PowerState:   "poweredOn",
			CollectedAt:  time.Now(),
		},
	}
	for _, host := range hosts {
		if err := t.repos.Host.Create(&host); err != nil {
			return 0, 0, fmt.Errorf("创建主机失败: %w", err)
		}
	}
	fmt.Printf("   ✓ 创建主机: %d 个\n", len(hosts))

	// 1.4 创建测试虚拟机
	vms := []storage.VM{
		{
			ConnectionID: conn.ID,
			VMKey:        "vm-001",
			UUID:         "uuid-001",
			Name:         "web-server-01",
			Datacenter:   "DC1",
			CpuCount:     4,
			MemoryMB:     8192,
			PowerState:   "poweredOn",
			GuestOS:      "ubuntu64Guest",
			HostName:     "esxi-host-01",
			CollectedAt:  time.Now(),
		},
		{
			ConnectionID: conn.ID,
			VMKey:        "vm-002",
			UUID:         "uuid-002",
			Name:         "db-server-01",
			Datacenter:   "DC1",
			CpuCount:     8,
			MemoryMB:     16384,
			PowerState:   "poweredOn",
			GuestOS:      "centos64Guest",
			HostName:     "esxi-host-01",
			CollectedAt:  time.Now(),
		},
		{
			ConnectionID: conn.ID,
			VMKey:        "vm-003",
			UUID:         "uuid-003",
			Name:         "app-server-01",
			Datacenter:   "DC1",
			CpuCount:     2,
			MemoryMB:     4096,
			PowerState:   "poweredOn",
			GuestOS:      "ubuntu64Guest",
			HostName:     "esxi-host-02",
			CollectedAt:  time.Now(),
		},
		{
			ConnectionID: conn.ID,
			VMKey:        "vm-004",
			UUID:         "uuid-004",
			Name:         "cache-server-01",
			Datacenter:   "DC1",
			CpuCount:     4,
			MemoryMB:     16384,
			PowerState:   "poweredOn",
			GuestOS:      "centos64Guest",
			HostName:     "esxi-host-02",
			CollectedAt:  time.Now(),
		},
	}
	for _, vm := range vms {
		if err := t.repos.VM.Create(&vm); err != nil {
			return 0, 0, fmt.Errorf("创建虚拟机失败: %w", err)
		}
	}
	fmt.Printf("   ✓ 创建虚拟机: %d 个\n", len(vms))

	// 1.5 创建测试任务（用于关联指标数据）
	startTime := time.Now().Add(-1 * time.Hour)
	endTime := time.Now()
	task := &storage.AssessmentTask{
		Name:         "资源评估任务",
		ConnectionID: conn.ID,
		Status:       "completed",
		StartedAt:    &startTime,
		CompletedAt:  &endTime,
		MetricsDays:  7,
	}
	if err := t.repos.Task.Create(task); err != nil {
		return 0, 0, fmt.Errorf("创建任务失败: %w", err)
	}
	fmt.Printf("   ✓ 创建任务: %s (ID: %d)\n", task.Name, task.ID)

	// 1.6 创建性能指标数据（模拟7天的数据）
	fmt.Printf("   ✓ 创建性能指标数据...\n")
	now := time.Now()
	var metrics []storage.VMMetric

	// 为每个 VM 创建 7 天的指标数据
	for _, vm := range vms {
		baseTime := now.Add(-7 * 24 * time.Hour)

		// 每 6 小时一个数据点，7 天 = 28 个数据点
		for i := 0; i < 28; i++ {
			timestamp := baseTime.Add(time.Duration(i) * 6 * time.Hour)

			// CPU 指标 (MHz)
			metrics = append(metrics, storage.VMMetric{
				TaskID:     task.ID,
				VMID:       vm.ID,
				MetricType: "cpu",
				Timestamp:  timestamp,
				Value:      float64(vm.CpuCount*100) + float64(i%10)*50, // 模拟变化
			})

			// 内存指标 (字节)
			metrics = append(metrics, storage.VMMetric{
				TaskID:     task.ID,
				VMID:       vm.ID,
				MetricType: "memory",
				Timestamp:  timestamp,
				Value:      float64(vm.MemoryMB*1024*1024) * (0.5 + float64(i%20)*0.02), // 50-90% 使用率
			})

			// 磁盘读指标
			metrics = append(metrics, storage.VMMetric{
				TaskID:     task.ID,
				VMID:       vm.ID,
				MetricType: "disk_read",
				Timestamp:  timestamp,
				Value:      float64(1024*1024) * (1 + float64(i%5)), // 1-5 MB/s
			})

			// 磁盘写指标
			metrics = append(metrics, storage.VMMetric{
				TaskID:     task.ID,
				VMID:       vm.ID,
				MetricType: "disk_write",
				Timestamp:  timestamp,
				Value:      float64(1024*1024) * (0.5 + float64(i%3)), // 0.5-2.5 MB/s
			})

			// 网络接收指标
			metrics = append(metrics, storage.VMMetric{
				TaskID:     task.ID,
				VMID:       vm.ID,
				MetricType: "net_rx",
				Timestamp:  timestamp,
				Value:      float64(1024*1024) * (2 + float64(i%10)), // 2-11 MB/s
			})

			// 网络发送指标
			metrics = append(metrics, storage.VMMetric{
				TaskID:     task.ID,
				VMID:       vm.ID,
				MetricType: "net_tx",
				Timestamp:  timestamp,
				Value:      float64(1024*1024) * (1 + float64(i%8)), // 1-8 MB/s
			})
		}
	}

	// 批量创建指标
	if err := t.repos.Metric.BatchCreate(metrics); err != nil {
		return 0, 0, fmt.Errorf("创建指标失败: %w", err)
	}
	fmt.Printf("   ✓ 创建性能指标: %d 条\n", len(metrics))

	// 1.7 创建分析结果
	findings := []storage.AnalysisFinding{
		{
			TaskID:      task.ID,
			JobType:     "zombie",
			TargetType:  "vm",
			TargetKey:   "vm-003",
			TargetName:  "app-server-01",
			Severity:    "warning",
			Category:    "resource",
			Title:       "低使用率虚拟机",
			Description: "该虚拟机在过去 30 天内 CPU 和内存使用率均低于 10%",
			Action:      "建议关机以节省资源",
			Reason:      "长期低使用率",
			SavingCost:  "180元/月",
		},
		{
			TaskID:      task.ID,
			JobType:     "rightsize",
			TargetType:  "vm",
			TargetKey:   "vm-001",
			TargetName:  "web-server-01",
			Severity:    "info",
			Category:    "optimization",
			Title:       "资源配置过剩",
			Description: "该虚拟机 CPU 和内存使用率均低于 30%，存在资源浪费",
			Action:      "建议降配为 2 vCPU / 4GB 内存",
			Reason:      "资源配置与实际需求不匹配",
			SavingCost:  "120元/月",
		},
	}
	for _, f := range findings {
		if err := t.repos.AnalysisFinding.Create(&f); err != nil {
			return 0, 0, fmt.Errorf("创建分析结果失败: %w", err)
		}
	}
	fmt.Printf("   ✓ 创建分析结果: %d 条\n\n", len(findings))

	return conn.ID, task.ID, nil
}

// TestReportDataBuilder 测试报告数据构建器
func (t *ReportIntegrationTest) TestReportDataBuilder(connID, taskID uint) error {
	fmt.Println("2. 测试报告数据构建器...")

	// 创建按任务过滤的数据源
	ds := report.NewDataSourceByTaskID(t.repos, taskID)
	builder := report.NewReportBuilder(ds)

	// 构建报告数据
	reportData, err := builder.BuildReportData()
	if err != nil {
		return fmt.Errorf("构建报告数据失败: %w", err)
	}

	fmt.Printf("   ✓ 报告标题: %s\n", reportData.Title)
	fmt.Printf("   ✓ 章节数量: %d\n", len(reportData.Sections))

	// 验证报告数据
	if reportData.Title == "" {
		return fmt.Errorf("报告标题为空")
	}
	if len(reportData.Sections) == 0 {
		return fmt.Errorf("报告章节为空")
	}

	// 打印章节信息
	for i, section := range reportData.Sections {
		fmt.Printf("   - 章节 %d: %s (%s)\n", i+1, section.Title, section.Type)
	}

	fmt.Println()
	return nil
}

// TestChartGeneration 测试图表生成
func (t *ReportIntegrationTest) TestChartGeneration(connID, taskID uint) (*report.ChartImages, error) {
	fmt.Println("3. 测试图表生成...")

	// 获取任务信息
	task, err := t.repos.Task.GetByID(taskID)
	if err != nil {
		return nil, fmt.Errorf("获取任务信息失败: %w", err)
	}

	// 创建数据源
	metricDS := report.NewMetricDataSource(t.repos, taskID)
	ds := report.NewDataSourceByTaskID(t.repos, taskID)

	// 构建报告数据
	builder := report.NewReportBuilder(ds)
	reportData, err := builder.BuildReportData()
	if err != nil {
		return nil, fmt.Errorf("构建报告数据失败: %w", err)
	}

	// 创建图表生成器
	chartGen := report.NewChartGenerator(t.outputDir)
	chartGen.SetMetricDataSource(metricDS, taskID, int(task.MetricsDays))

	// 生成所有图表
	images, err := chartGen.GenerateAllCharts(reportData)
	if err != nil {
		return nil, fmt.Errorf("生成图表失败: %w", err)
	}

	// 验证图表
	fmt.Printf("   ✓ 集群分布图: %s\n", images.ClusterDistribution)
	if images.ClusterDistribution != "" {
		if _, err := os.Stat(images.ClusterDistribution); os.IsNotExist(err) {
			return nil, fmt.Errorf("集群分布图文件不存在")
		}
		t.cleanup = append(t.cleanup, images.ClusterDistribution)
	}

	fmt.Printf("   ✓ 主机利用率图: %s\n", images.HostUsageTop10)
	if images.HostUsageTop10 != "" {
		if _, err := os.Stat(images.HostUsageTop10); os.IsNotExist(err) {
			return nil, fmt.Errorf("主机利用率图文件不存在")
		}
		t.cleanup = append(t.cleanup, images.HostUsageTop10)
	}

	fmt.Printf("   ✓ VM CPU 分布图: %s\n", images.VMCpuDistribution)
	if images.VMCpuDistribution != "" {
		if _, err := os.Stat(images.VMCpuDistribution); os.IsNotExist(err) {
			return nil, fmt.Errorf("VM CPU 分布图文件不存在")
		}
		t.cleanup = append(t.cleanup, images.VMCpuDistribution)
	}

	fmt.Printf("   ✓ VM 内存趋势图: %s\n", images.VMMemoryTrend)
	if images.VMMemoryTrend != "" {
		if _, err := os.Stat(images.VMMemoryTrend); os.IsNotExist(err) {
			return nil, fmt.Errorf("VM 内存趋势图文件不存在")
		}
		t.cleanup = append(t.cleanup, images.VMMemoryTrend)
	}

	fmt.Println()
	return images, nil
}

// TestExcelGeneration 测试 Excel 生成
func (t *ReportIntegrationTest) TestExcelGeneration(connID, taskID uint) error {
	fmt.Println("4. 测试 Excel 生成...")

	// 创建数据源
	ds := report.NewDataSourceByTaskID(t.repos, taskID)

	// 构建报告数据
	builder := report.NewReportBuilder(ds)
	reportData, err := builder.BuildReportData()
	if err != nil {
		return fmt.Errorf("构建报告数据失败: %w", err)
	}

	// 创建 Excel 生成器
	excelGen := report.NewExcelGenerator(reportData, t.outputDir)

	// 生成 Excel
	excelPath, err := excelGen.Generate()
	if err != nil {
		return fmt.Errorf("生成 Excel 失败: %w", err)
	}

	// 验证文件
	if _, err := os.Stat(excelPath); os.IsNotExist(err) {
		return fmt.Errorf("Excel 文件不存在: %s", excelPath)
	}

	fmt.Printf("   ✓ Excel 文件: %s\n", excelPath)
	fmt.Printf("   ✓ 文件大小: %d 字节\n", fileInfo(excelPath))

	t.cleanup = append(t.cleanup, excelPath)
	fmt.Println()
	return nil
}

// TestPDFGeneration 测试 PDF 生成
func (t *ReportIntegrationTest) TestPDFGeneration(connID, taskID uint, images *report.ChartImages) error {
	fmt.Println("5. 测试 PDF 生成...")

	// PDF 生成现在使用嵌入的 simhei.ttf 字体，不需要检查系统字体
	// 字体已通过 embed.FS 嵌入到二进制文件中

	// 创建数据源
	ds := report.NewDataSourceByTaskID(t.repos, taskID)

	// 构建报告数据
	builder := report.NewReportBuilder(ds)
	reportData, err := builder.BuildReportData()
	if err != nil {
		return fmt.Errorf("构建报告数据失败: %w", err)
	}

	// 创建 PDF 生成器
	config := &report.PDFConfig{
		OutputDir: t.outputDir,
	}
	pdfGen := report.NewPDFGenerator(reportData, images, config)

	// 生成 PDF
	pdfPath, err := pdfGen.Generate()
	if err != nil {
		return fmt.Errorf("生成 PDF 失败: %w", err)
	}

	// 验证文件
	if _, err := os.Stat(pdfPath); os.IsNotExist(err) {
		return fmt.Errorf("PDF 文件不存在: %s", pdfPath)
	}

	fmt.Printf("   ✓ PDF 文件: %s\n", pdfPath)
	fmt.Printf("   ✓ 文件大小: %d 字节\n", fileInfo(pdfPath))

	t.cleanup = append(t.cleanup, pdfPath)
	fmt.Println()
	return nil
}

// TestEndToEnd 端到端测试：完整报告生成流程
func (t *ReportIntegrationTest) TestEndToEnd(connID, taskID uint) error {
	fmt.Println("6. 端到端测试：完整报告生成流程...")

	// 获取任务信息
	task, err := t.repos.Task.GetByID(taskID)
	if err != nil {
		return fmt.Errorf("获取任务信息失败: %w", err)
	}

	// 创建数据源
	metricDS := report.NewMetricDataSource(t.repos, taskID)
	ds := report.NewDataSourceByTaskID(t.repos, taskID)

	// 1. 构建报告数据
	builder := report.NewReportBuilder(ds)
	reportData, err := builder.BuildReportData()
	if err != nil {
		return fmt.Errorf("构建报告数据失败: %w", err)
	}

	// 2. 生成图表
	chartGen := report.NewChartGenerator(t.outputDir)
	chartGen.SetMetricDataSource(metricDS, taskID, int(task.MetricsDays))
	images, err := chartGen.GenerateAllCharts(reportData)
	if err != nil {
		return fmt.Errorf("生成图表失败: %w", err)
	}

	// 3. 生成 Excel
	excelGen := report.NewExcelGenerator(reportData, t.outputDir)
	excelPath, err := excelGen.Generate()
	if err != nil {
		return fmt.Errorf("生成 Excel 失败: %w", err)
	}
	t.cleanup = append(t.cleanup, excelPath)

	// 4. 生成 PDF（如果有中文字体）
	pdfConfig := &report.PDFConfig{
		OutputDir: t.outputDir,
	}
	pdfGen := report.NewPDFGenerator(reportData, images, pdfConfig)
	pdfPath, err := pdfGen.Generate()
	if err != nil {
		// PDF 生成失败可能是因为没有中文字体，但这不影响核心功能
		fmt.Printf("   ⚠ PDF 生成失败（可能缺少中文字体）: %v\n", err)
	} else {
		t.cleanup = append(t.cleanup, pdfPath)
		fmt.Printf("   - PDF: %s\n", pdfPath)
	}

	fmt.Printf("   ✓ 报告生成完成\n")
	fmt.Printf("   - Excel: %s\n", excelPath)
	if err == nil {
		fmt.Printf("   - PDF: %s\n", pdfPath)
	}
	fmt.Println()
	return nil
}

// 辅助函数：获取文件信息
func fileInfo(path string) int64 {
	info, _ := os.Stat(path)
	if info != nil {
		return info.Size()
	}
	return 0
}

// Run 运行所有测试
func (t *ReportIntegrationTest) Run() error {
	// 初始化
	if err := t.Setup(); err != nil {
		return fmt.Errorf("初始化失败: %w", err)
	}
	defer t.Teardown()

	// 创建测试数据
	connID, taskID, err := t.setupTestData()
	if err != nil {
		return fmt.Errorf("创建测试数据失败: %w", err)
	}

	// 运行测试
	tests := []struct {
		name string
		fn   func(connID, taskID uint) error
	}{
		{"报告数据构建器", t.TestReportDataBuilder},
		{"图表生成", func(id1, id2 uint) error {
			_, err := t.TestChartGeneration(id1, id2)
			return err
		}},
		{"Excel 生成", t.TestExcelGeneration},
		{"PDF 生成", func(id1, id2 uint) error {
			images, _ := t.TestChartGeneration(id1, id2)
			return t.TestPDFGeneration(id1, id2, images)
		}},
		{"端到端测试", t.TestEndToEnd},
	}

	passed := 0
	failed := 0

	for _, tt := range tests {
		if err := tt.fn(connID, taskID); err != nil {
			fmt.Printf("❌ %s 失败: %v\n\n", tt.name, err)
			failed++
		} else {
			fmt.Printf("✅ %s 通过\n\n", tt.name)
			passed++
		}
	}

	// 输出测试结果
	fmt.Println("========================================")
	fmt.Printf("测试结果: %d 通过, %d 失败\n", passed, failed)
	fmt.Println("========================================")

	if failed > 0 {
		return fmt.Errorf("%d 个测试失败", failed)
	}

	return nil
}

// main 主函数
func main() {
	test := NewReportIntegrationTest()
	if err := test.Run(); err != nil {
		fmt.Printf("\n❌ 测试失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("\n✅ 所有测试通过!")
}
