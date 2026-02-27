package main

import (
	"context"
	"fmt"
	"net/url"
	"os"
	"time"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/vim25/soap"

	"justfit/internal/analyzer"
	"justfit/internal/connector"
	"justfit/internal/etl"
	"justfit/internal/storage"
)

// E2ETest 端到端测试结构
type E2ETest struct {
	ctx       context.Context
	repos     *storage.Repositories
	connMgr   *connector.ConnectorManager
	collector *etl.Collector
	analyzer  *analyzer.Engine
}

// NewE2ETest 创建端到端测试
func NewE2ETest() *E2ETest {
	return &E2ETest{}
}

// Setup 初始化测试环境
func (t *E2ETest) Setup() error {
	t.ctx = context.Background()

	// 初始化数据库
	homeDir, _ := os.UserHomeDir()
	cfg := &storage.Config{DataDir: homeDir + "/.justfit"}
	if err := storage.Init(cfg); err != nil {
		return fmt.Errorf("初始化数据库失败: %w", err)
	}

	// 创建连接器管理器
	t.connMgr = connector.NewConnectorManager()

	// 创建数据仓储
	t.repos = storage.NewRepositories()

	// 创建采集器
	t.collector = etl.NewCollector(t.connMgr, t.repos)

	// 创建分析引擎
	t.analyzer = analyzer.NewEngine(t.repos)

	return nil
}

// Teardown 清理测试环境
func (t *E2ETest) Teardown() {
	if t.connMgr != nil {
		t.connMgr.CloseAll()
	}
	storage.Close()
}

// TestVCenterConnection 测试 vCenter 连接
func (t *E2ETest) TestVCenterConnection(host, username, password string) error {
	fmt.Println("\n=== 测试 vCenter 连接 ===")

	// 创建 vCenter 客户端验证凭据
	soapURL, err := soap.ParseURL(fmt.Sprintf("https://%s/sdk", host))
	if err != nil {
		return fmt.Errorf("解析 URL 失败: %w", err)
	}

	soapURL.User = url.UserPassword(username, password)

	// 创建客户端，insecure=true 跳过 TLS 证书验证
	client, err := govmomi.NewClient(t.ctx, soapURL, true)
	if err != nil {
		return fmt.Errorf("连接 vCenter 失败: %w", err)
	}
	defer client.Logout(t.ctx)

	// 获取版本信息
	version := client.ServiceContent.About

	fmt.Printf("✓ 连接成功!\n")
	fmt.Printf("  服务器: %s\n", host)
	fmt.Printf("  产品: %s\n", version.Name)
	fmt.Printf("  版本: %s\n", version.Version)
	fmt.Printf("  全名: %s\n", version.FullName)

	return nil
}

// TestCreateConnection 测试创建连接
func (t *E2ETest) TestCreateConnection(host, username, password string) (uint, error) {
	fmt.Println("\n=== 测试创建连接 ===")

	conn := &storage.Connection{
		Name:     fmt.Sprintf("vCenter-%s", host),
		Platform: "vcenter",
		Host:     host,
		Port:     443,
		Username: username,
		Password: password,
		Insecure: true,
		Status:   "disconnected",
	}

	err := t.repos.Connection.Create(conn)
	if err != nil {
		return 0, fmt.Errorf("创建连接失败: %w", err)
	}

	fmt.Printf("✓ 连接创建成功, ID: %d\n", conn.ID)
	fmt.Printf("  名称: %s\n", conn.Name)
	fmt.Printf("  主机: %s\n", conn.Host)
	fmt.Printf("  用户: %s\n", conn.Username)

	return conn.ID, nil
}

// TestCollection 测试数据采集
func (t *E2ETest) TestCollection(connectionID uint, password string) error {
	fmt.Println("\n=== 测试数据采集 ===")

	config := &etl.CollectionConfig{
		ConnectionID: connectionID,
		DataTypes:    []string{"clusters", "hosts", "vms"},
		MetricsDays:  0, // 不采集性能指标，加快测试
		Concurrency:  3,
		Password:     password,
	}

	startTime := time.Now()
	result, err := t.collector.Collect(t.ctx, config)
	if err != nil {
		return fmt.Errorf("采集失败: %w", err)
	}

	duration := time.Since(startTime)

	fmt.Printf("✓ 采集成功!\n")
	fmt.Printf("  耗时: %v\n", duration)
	fmt.Printf("  集群数: %d\n", result.Clusters)
	fmt.Printf("  主机数: %d\n", result.Hosts)
	fmt.Printf("  虚拟机数: %d\n", result.VMs)

	// 更新连接的最后同步时间
	now := time.Now()
	_ = t.repos.Connection.UpdateLastSync(connectionID, now)
	_ = t.repos.Connection.UpdateStatus(connectionID, "connected")

	return nil
}

// TestListResources 测试列出资源
func (t *E2ETest) TestListResources(connectionID uint) error {
	fmt.Println("\n=== 测试列出资源 ===")

	// 列出集群
	clusters, err := t.repos.Cluster.ListByConnectionID(connectionID)
	if err != nil {
		return fmt.Errorf("列出集群失败: %w", err)
	}
	fmt.Printf("✓ 集群列表 (%d 个):\n", len(clusters))
	for i, c := range clusters {
		if i < 5 { // 只显示前 5 个
			fmt.Printf("  - %s (主机: %d, 虚拟机: %d)\n", c.Name, c.NumHosts, c.NumVMs)
		}
	}
	if len(clusters) > 5 {
		fmt.Printf("  ... 还有 %d 个集群\n", len(clusters)-5)
	}

	// 列出主机
	hosts, err := t.repos.Host.ListByConnectionID(connectionID)
	if err != nil {
		return fmt.Errorf("列出主机失败: %w", err)
	}
	fmt.Printf("✓ 主机列表 (%d 个):\n", len(hosts))
	for i, h := range hosts {
		if i < 5 {
			fmt.Printf("  - %s (IP: %s, CPU: %d核, 内存: %.1fGB)\n",
				h.Name, h.IPAddress, h.CpuCores, float64(h.Memory)/(1024*1024*1024))
		}
	}
	if len(hosts) > 5 {
		fmt.Printf("  ... 还有 %d 个主机\n", len(hosts)-5)
	}

	// 列出虚拟机
	vms, err := t.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return fmt.Errorf("列出虚拟机失败: %w", err)
	}
	fmt.Printf("✓ 虚拟机列表 (%d 个):\n", len(vms))
	for i, vm := range vms {
		if i < 5 {
			powerState := "关机"
			if vm.PowerState == "poweredOn" {
				powerState = "运行"
			}
			fmt.Printf("  - %s (状态: %s, CPU: %d核, 内存: %.1fGB)\n",
				vm.Name, powerState, vm.CpuCount, float64(vm.MemoryMB)/1024)
		}
	}
	if len(vms) > 5 {
		fmt.Printf("  ... 还有 %d 个虚拟机\n", len(vms)-5)
	}

	return nil
}

// TestZombieVMAnalysis 测试僵尸 VM 分析
func (t *E2ETest) TestZombieVMAnalysis(connectionID uint) error {
	fmt.Println("\n=== 测试僵尸 VM 分析 ===")

	config := analyzer.DefaultZombieVMConfig()
	// 降低阈值以便更容易检测到僵尸 VM
	config.CPUThreshold = 10.0
	config.MemoryThreshold = 20.0

	results, err := t.analyzer.DetectZombieVMs(connectionID, config)
	if err != nil {
		return fmt.Errorf("僵尸 VM 分析失败: %w", err)
	}

	fmt.Printf("✓ 分析完成，检测到 %d 个潜在僵尸 VM\n", len(results))
	if len(results) > 0 {
		for i, r := range results {
			if i < 5 {
				fmt.Printf("  %d. %s\n", i+1, r.VMName)
				fmt.Printf("     主机: %s\n", r.Host)
				fmt.Printf("     CPU 使用率: %.2f%%, 内存使用率: %.2f%%\n", r.CPUUsage, r.MemoryUsage)
				fmt.Printf("     置信度: %.2f%%, 建议: %s\n", r.Confidence*100, r.Recommendation)
			}
		}
		if len(results) > 5 {
			fmt.Printf("  ... 还有 %d 个\n", len(results)-5)
		}
	} else {
		fmt.Println("  未检测到僵尸 VM（资源使用率高于阈值）")
	}

	return nil
}

// TestRightSizeAnalysis 测试 Right Size 分析
func (t *E2ETest) TestRightSizeAnalysis(connectionID uint) error {
	fmt.Println("\n=== 测试 Right Size 分析 ===")

	config := analyzer.DefaultRightSizeConfig()
	config.BufferRatio = 1.2

	results, err := t.analyzer.AnalyzeRightSize(connectionID, config)
	if err != nil {
		return fmt.Errorf("Right Size 分析失败: %w", err)
	}

	fmt.Printf("✓ 分析完成，检测到 %d 个可优化的虚拟机\n", len(results))
	if len(results) > 0 {
		optimizableCount := 0
		for i, r := range results {
			if r.AdjustmentType != "none" {
				optimizableCount++
			}
			if i < 5 {
				fmt.Printf("  %d. %s\n", i+1, r.VMName)
				fmt.Printf("     当前配置: %d核, %.0fMB\n", r.CurrentCPU, r.CurrentMemoryMB)
				fmt.Printf("     推荐配置: %d核, %.0fMB\n", r.RecommendedCPU, r.RecommendedMemoryMB)
				fmt.Printf("     调整类型: %s, 风险: %s\n", r.AdjustmentType, r.RiskLevel)
			}
		}
		fmt.Printf("  其中 %d 个建议优化\n", optimizableCount)
		if len(results) > 5 {
			fmt.Printf("  ... 还有 %d 个\n", len(results)-5)
		}
	}

	return nil
}

// TestHealthScoreAnalysis 测试健康度分析
func (t *E2ETest) TestHealthScoreAnalysis(connectionID uint) error {
	fmt.Println("\n=== 测试健康度分析 ===")

	result, err := t.analyzer.AnalyzeHealthScore(connectionID, nil)
	if err != nil {
		return fmt.Errorf("健康度分析失败: %w", err)
	}

	fmt.Printf("✓ 分析完成\n")
	fmt.Printf("  连接名称: %s\n", result.ConnectionName)
	fmt.Printf("  总体评分: %.2f / 100\n", result.OverallScore)
	fmt.Printf("  健康等级: %s\n", result.HealthLevel)
	fmt.Printf("  资源均衡度: %.2f\n", result.ResourceBalance)
	fmt.Printf("  超配风险: %.2f\n", result.OvercommitRisk)
	fmt.Printf("  热点集中度: %.2f\n", result.HotspotConcentration)
	fmt.Printf("  集群数: %d, 主机数: %d, 虚拟机数: %d\n",
		result.ClusterCount, result.HostCount, result.VMCount)

	if len(result.RiskItems) > 0 {
		fmt.Printf("  风险项: %d 个\n", len(result.RiskItems))
		for i, risk := range result.RiskItems {
			if i < 3 {
				fmt.Printf("    - %s\n", risk)
			}
		}
	}

	return nil
}

// TestCleanup 测试清理
func (t *E2ETest) TestCleanup(connectionID uint) {
	fmt.Println("\n=== 清理测试数据 ===")
	_ = t.repos.Connection.Delete(connectionID)
	fmt.Printf("✓ 测试连接已删除\n")
}

// main 主函数
func main() {
	fmt.Println("========================================")
	fmt.Println("JustFit 后端 API 真实环境测试")
	fmt.Println("========================================")

	// 读取环境变量
	vCenterHost := "10.103.116.116"
	vCenterUser := "administrator@vsphere.local"
	vCenterPass := "Admin@123."

	// 创建测试实例
	test := NewE2ETest()

	// 初始化
	err := test.Setup()
	if err != nil {
		fmt.Printf("❌ 初始化失败: %v\n", err)
		os.Exit(1)
	}
	defer test.Teardown()
	fmt.Println("✓ 初始化成功")

	var connectionID uint

	// 1. 验证 vCenter 连接
	if err := test.TestVCenterConnection(vCenterHost, vCenterUser, vCenterPass); err != nil {
		fmt.Printf("❌ vCenter 连接测试失败: %v\n", err)
		fmt.Println("\n注意: 请确保网络连接正常，vCenter 服务可达")
		os.Exit(1)
	}

	// 2. 创建连接
	connectionID, err = test.TestCreateConnection(vCenterHost, vCenterUser, vCenterPass)
	if err != nil {
		fmt.Printf("❌ 创建连接失败: %v\n", err)
		os.Exit(1)
	}

	// 3. 数据采集
	if err := test.TestCollection(connectionID, vCenterPass); err != nil {
		fmt.Printf("❌ 数据采集失败: %v\n", err)
		// 继续执行其他测试
	}

	// 4. 列出资源
	if err := test.TestListResources(connectionID); err != nil {
		fmt.Printf("❌ 列出资源失败: %v\n", err)
	}

	// 5. 僵尸 VM 分析
	if err := test.TestZombieVMAnalysis(connectionID); err != nil {
		fmt.Printf("❌ 僵尸 VM 分析失败: %v\n", err)
	}

	// 6. Right Size 分析
	if err := test.TestRightSizeAnalysis(connectionID); err != nil {
		fmt.Printf("❌ Right Size 分析失败: %v\n", err)
	}

	// 7. 健康度分析
	if err := test.TestHealthScoreAnalysis(connectionID); err != nil {
		fmt.Printf("❌ 健康度分析失败: %v\n", err)
	}

	// 清理
	// test.TestCleanup(connectionID) // 保留数据供后续查看

	fmt.Println("\n========================================")
	fmt.Println("测试完成！数据已保存到 ~/.justfit/ 目录")
	fmt.Println("========================================")
}
