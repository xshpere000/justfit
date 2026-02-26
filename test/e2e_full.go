package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"justfit/internal/analyzer"
	"justfit/internal/connector"
	"justfit/internal/etl"
	"justfit/internal/storage"
)

// 完整端到端测试
func main() {
	fmt.Println("JustFit 完整端到端测试")
	fmt.Println("=====================\n")

	// 1. 初始化数据库
	fmt.Println("1. 初始化数据库...")
	if err := storage.Init(&storage.Config{}); err != nil {
		log.Fatalf("初始化数据库失败: %v", err)
	}
	defer storage.Close()
	repos := storage.NewRepositories()
	fmt.Println("   ✓ 数据库初始化成功\n")

	// 2. 创建连接记录
	fmt.Println("2. 创建连接记录...")
	conn := &storage.Connection{
		Name:     "H3C UIS 测试环境",
		Platform: "h3c-uis",
		Host:     "200.201.38.95",
		Port:     443,
		Username: "admin",
		Insecure: true,
		Status:   "disconnected",
	}
	if err := repos.Connection.Create(conn); err != nil {
		log.Printf("   ⚠ 创建连接记录失败: %v", err)
		// 尝试使用现有连接
		connections, _ := repos.Connection.List()
		if len(connections) > 0 {
			conn = &connections[0]
			fmt.Printf("   使用现有连接: %s (ID: %d)\n", conn.Name, conn.ID)
		} else {
			log.Fatal("   ✗ 没有可用的连接")
		}
	} else {
		fmt.Printf("   ✓ 创建连接记录 (ID: %d)\n\n", conn.ID)
	}
	connectionID := conn.ID

	// 3. 测试连接
	fmt.Println("3. 测试连接...")
	config := &connector.ConnectionConfig{
		ID:       conn.ID,
		Name:     conn.Name,
		Platform: connector.PlatformType(conn.Platform),
		Host:     conn.Host,
		Port:     conn.Port,
		Username: conn.Username,
		Password: "Admin@123.",
		Insecure: conn.Insecure,
	}

	client, err := connector.NewConnector(config)
	if err != nil {
		log.Fatalf("创建连接器失败: %v", err)
	}
	defer client.Close()

	if err := client.TestConnection(); err != nil {
		log.Printf("   ⚠ 连接测试失败: %v\n", err)
	} else {
		repos.Connection.UpdateStatus(connectionID, "connected")
		fmt.Println("   ✓ 连接测试成功\n")
	}

	// 4. 数据采集
	fmt.Println("4. 开始数据采集...")
	connMgr := connector.NewConnectorManager()
	collector := etl.NewCollector(connMgr, repos)
	password := "Admin@123."

	// 4.1 采集虚拟机
	fmt.Println("   4.1 采集虚拟机...")
	vmResult, err := collector.Collect(nil, &etl.CollectionConfig{
		ConnectionID: connectionID,
		DataTypes:    []string{"vms"},
		Concurrency:  3,
		Password:     password,
	})
	if err != nil {
		log.Printf("   ⚠ 采集虚拟机失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 台虚拟机\n", vmResult.VMs)
	}

	// 4.2 采集主机
	fmt.Println("   4.2 采集主机...")
	hostResult, err := collector.Collect(nil, &etl.CollectionConfig{
		ConnectionID: connectionID,
		DataTypes:    []string{"hosts"},
		Concurrency:  3,
		Password:     password,
	})
	if err != nil {
		log.Printf("   ⚠ 采集主机失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 台主机\n", hostResult.Hosts)
	}

	// 4.3 采集集群
	fmt.Println("   4.3 采集集群...")
	clusterResult, err := collector.Collect(nil, &etl.CollectionConfig{
		ConnectionID: connectionID,
		DataTypes:    []string{"clusters"},
		Concurrency:  3,
		Password:     password,
	})
	if err != nil {
		log.Printf("   ⚠ 采集集群失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 个集群\n", clusterResult.Clusters)
	}

	// 4.4 采集性能指标
	fmt.Println("   4.4 采集性能指标...")
	metricStats, err := collector.CollectMetrics(nil, connectionID, 7, password)
	if err != nil {
		log.Printf("   ⚠ 采集性能指标失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 条性能指标\n", metricStats.CollectedMetricCount)
	}

	// 更新连接最后同步时间
	now := time.Now()
	repos.Connection.UpdateLastSync(connectionID, now)

	// 查询采集结果
	vms, _ := repos.VM.ListByConnectionID(connectionID)
	fmt.Printf("\n   数据库中现有 %d 台虚拟机\n", len(vms))

	// 显示虚拟机列表
	if len(vms) > 0 {
		fmt.Println("\n   虚拟机列表:")
		for i, vm := range vms {
			if i < 5 {
				fmt.Printf("     - %s: %d vCPU, %d MB 内存, 状态: %s\n",
					vm.Name, vm.CpuCount, vm.MemoryMB, vm.PowerState)
			}
		}
		if len(vms) > 5 {
			fmt.Printf("     ... 还有 %d 台\n", len(vms)-5)
		}
	}

	// 5. 运行分析
	fmt.Println("\n5. 运行分析引擎...")
	analysisEngine := analyzer.NewEngine(repos)

	// 5.1 僵尸 VM 检测
	fmt.Println("   5.1 僵尸 VM 检测...")
	zombieConfig := &analyzer.ZombieVMConfig{
		AnalysisDays:     7,
		CPUThreshold:     5.0,
		MemoryThreshold:  10.0,
		MinConfidence:    60.0,
	}
	zombieResults, err := analysisEngine.DetectZombieVMs(connectionID, zombieConfig)
	if err != nil {
		log.Printf("   ⚠ 僵尸 VM 检测失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 检测到 %d 台僵尸 VM\n", len(zombieResults))
		for i, r := range zombieResults {
			if i < 3 {
				fmt.Printf("     - %s: CPU %.2f%%, 内存 %.2f%%, 置信度 %.0f%%\n",
					r.VMName, r.CPUUsage, r.MemoryUsage, r.Confidence)
			}
		}
	}

	// 5.2 Right Size 分析
	fmt.Println("\n   5.2 Right Size 分析...")
	rightSizeConfig := &analyzer.RightSizeConfig{
		AnalysisDays: 7,
		BufferRatio:  0.2,
	}
	rightSizeResults, err := analysisEngine.AnalyzeRightSize(connectionID, rightSizeConfig)
	if err != nil {
		log.Printf("   ⚠ Right Size 分析失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 分析出 %d 台需要调整规格的 VM\n", len(rightSizeResults))
		for i, r := range rightSizeResults {
			if i < 3 {
				fmt.Printf("     - %s: %d→%d vCPU, %d→%d MB, %s\n",
					r.VMName, r.CurrentCPU, r.RecommendedCPU,
					r.CurrentMemoryMB, r.RecommendedMemoryMB, r.AdjustmentType)
			}
		}
	}

	// 5.3 潮汐模式检测
	fmt.Println("\n   5.3 潮汐模式检测...")
	tidalConfig := &analyzer.TidalConfig{
		AnalysisDays: 7,
		MinStability: 0.6,
	}
	tidalResults, err := analysisEngine.DetectTidalPattern(connectionID, tidalConfig)
	if err != nil {
		log.Printf("   ⚠ 潮汐模式检测失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 检测到 %d 台有潮汐规律的 VM\n", len(tidalResults))
		for i, r := range tidalResults {
			if i < 3 {
				fmt.Printf("     - %s: 模式 %s, 稳定性 %.0f%%\n",
					r.VMName, r.Pattern, r.StabilityScore)
			}
		}
	}

	// 5.4 健康评分
	fmt.Println("\n   5.4 健康评分...")
	healthResult, err := analysisEngine.AnalyzeHealthScore(connectionID, nil)
	if err != nil {
		log.Printf("   ⚠ 健康评分失败: %v\n", err)
	} else {
		fmt.Printf("   ✓ 健康评分: %.0f/100 (%s)\n",
			healthResult.OverallScore, healthResult.HealthLevel)
		fmt.Printf("     - 资源均衡: %.0f/100\n", healthResult.ResourceBalance)
		fmt.Printf("     - 超配风险: %.0f/100\n", healthResult.OvercommitRisk)
		fmt.Printf("     - 热点集中: %.0f/100\n", healthResult.HotspotConcentration)
		fmt.Printf("     - 风险项: %v\n", healthResult.RiskItems)
	}

	// 6. 生成报告
	fmt.Println("\n6. 生成测试报告...")
	report := map[string]interface{}{
		"timestamp":       time.Now().Format(time.RFC3339),
		"connection_id":   connectionID,
		"connection_name": conn.Name,
		"vm_count":        len(vms),
		"zombieVMs":      len(zombieResults),
		"rightsize_vms":   len(rightSizeResults),
		"tidal_vms":       len(tidalResults),
		"healthScore":    healthResult.OverallScore,
		"health_level":    healthResult.HealthLevel,
		"resource_balance": healthResult.ResourceBalance,
		"overcommit_risk": healthResult.OvercommitRisk,
	}

	reportData, _ := json.MarshalIndent(report, "", "  ")
	fmt.Println(string(reportData))

	// 保存报告
	reportFile := "/tmp/justfit_e2e_report.json"
	os.WriteFile(reportFile, reportData, 0644)
	fmt.Printf("\n   ✓ 报告已保存到: %s\n", reportFile)

	fmt.Println("\n=====================")
	fmt.Println("端到端测试完成!")
	fmt.Println("\n总结:")
	fmt.Printf("- 采集虚拟机: %d 台\n", len(vms))
	fmt.Printf("- 僵尸 VM: %d 台\n", len(zombieResults))
	fmt.Printf("- 需要调整规格: %d 台\n", len(rightSizeResults))
	fmt.Printf("- 有潮汐规律: %d 台\n", len(tidalResults))
	fmt.Printf("- 健康评分: %.0f/100\n", healthResult.OverallScore)
}
