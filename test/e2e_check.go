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

// E2E 测试：完整的数据采集和分析流程
func main() {
	fmt.Println("JustFit 端到端测试")
	fmt.Println("==================\n")

	// 初始化数据库
	fmt.Println("1. 初始化数据库...")
	if err := storage.Init(&storage.Config{}); err != nil {
		log.Fatalf("初始化数据库失败: %v", err)
	}
	defer storage.Close()
	repos := storage.NewRepositories()
	fmt.Println("   ✓ 数据库初始化成功\n")

	// 创建 H3C UIS 连接
	fmt.Println("2. 创建 H3C UIS 连接...")
	config := &connector.ConnectionConfig{
		Name:     "H3C UIS 测试环境",
		Platform: connector.PlatformH3CUIS,
		Host:     "10.103.125.116",
		Port:     443,
		Username: "admin",
		Password: "Admin@123.",
		Insecure: true,
	}

	client, err := connector.NewConnector(config)
	if err != nil {
		log.Fatalf("创建 UIS 连接器失败: %v", err)
	}
	defer client.Close()
	fmt.Println("   ✓ UIS 连接成功\n")

	// 数据采集
	fmt.Println("3. 开始数据采集...")
	collector := etl.NewCollector(nil, repos)

	// 使用明文密码进行采集（仅用于测试）
	password := "Admin@123."

	// 采集虚拟机数据
	fmt.Println("   3.1 采集虚拟机列表...")
	vmResult, err := collector.Collect(nil, &etl.CollectionConfig{
		ConnectionID: 0,
		DataTypes:    []string{"vms"},
		Concurrency:  3,
		Password:     password,
	})
	if err != nil {
		log.Printf("   ⚠ 采集虚拟机失败: %v", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 台虚拟机\n", vmResult.VMs)
	}

	// 采集主机数据
	fmt.Println("   3.2 采集主机列表...")
	hostResult, err := collector.Collect(nil, &etl.CollectionConfig{
		ConnectionID: 0,
		DataTypes:    []string{"hosts"},
		Concurrency:  3,
		Password:     password,
	})
	if err != nil {
		log.Printf("   ⚠ 采集主机失败: %v", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 台主机\n", hostResult.Hosts)
	}

	// 采集集群数据
	fmt.Println("   3.3 采集集群列表...")
	clusterResult, err := collector.Collect(nil, &etl.CollectionConfig{
		ConnectionID: 0,
		DataTypes:    []string{"clusters"},
		Concurrency:  3,
		Password:     password,
	})
	if err != nil {
		log.Printf("   ⚠ 采集集群失败: %v", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 个集群\n", clusterResult.Clusters)
	}

	// 采集性能指标
	fmt.Println("   3.4 采集性能指标...")
	// 创建临时任务用于关联指标数据
	tempTask := &storage.AssessmentTask{
		Name:         "E2E测试任务",
		ConnectionID: 0,
		Status:       "running",
	}
	repos.Task.Create(tempTask)
	defer repos.Task.Delete(tempTask.ID) // 测试结束后清理

	metricStats, err := collector.CollectMetrics(nil, tempTask.ID, 0, 7, password)
	if err != nil {
		log.Printf("   ⚠ 采集性能指标失败: %v", err)
	} else {
		fmt.Printf("   ✓ 采集到 %d 条性能指标\n", metricStats.CollectedMetricCount)
	}

	// 查询采集的虚拟机数量
	vms, _ := repos.VM.ListByConnectionID(0)
	fmt.Printf("   数据库中现有 %d 台虚拟机\n\n", len(vms))

	// 运行分析
	fmt.Println("4. 运行分析引擎...")
	analysisEngine := analyzer.NewEngine(repos)

	// 获取第一个连接的 ID（假设使用 connectionID = 1）
	connectionID := uint(1)

	// 4.1 僵尸 VM 检测
	fmt.Println("   4.1 僵尸 VM 检测...")
	zombieConfig := analyzer.DefaultZombieVMConfig()
	zombieResults, err := analysisEngine.DetectZombieVMs(connectionID, zombieConfig)
	if err != nil {
		log.Printf("   ⚠ 僵尸 VM 检测失败: %v", err)
	} else {
		fmt.Printf("   ✓ 检测到 %d 台僵尸 VM\n", len(zombieResults))
		for i, r := range zombieResults {
			if i < 3 {
				fmt.Printf("     - %s: CPU %.2f%%, 内存 %.2f%%, 置信度 %.0f%%\n",
					r.VMName, r.CPUUsage, r.MemoryUsage, r.Confidence)
			}
		}
	}

	// 4.2 Right Size 分析
	fmt.Println("\n   4.2 Right Size 分析...")
	rightSizeConfig := analyzer.DefaultRightSizeConfig()
	rightSizeResults, err := analysisEngine.AnalyzeRightSize(connectionID, rightSizeConfig)
	if err != nil {
		log.Printf("   ⚠ Right Size 分析失败: %v", err)
	} else {
		fmt.Printf("   ✓ 分析出 %d 台需要调整规格的 VM\n", len(rightSizeResults))
		for i, r := range rightSizeResults {
			if i < 3 {
				fmt.Printf("     - %s: %d→%d vCPU, %d→%d MB, 风险: %s\n",
					r.VMName, r.CurrentCPU, r.RecommendedCPU,
					r.CurrentMemoryMB, r.RecommendedMemoryMB, r.RiskLevel)
			}
		}
	}

	// 4.3 潮汐模式检测
	fmt.Println("\n   4.3 潮汐模式检测...")
	tidalConfig := analyzer.DefaultTidalConfig()
	tidalResults, err := analysisEngine.DetectTidalPattern(connectionID, tidalConfig)
	if err != nil {
		log.Printf("   ⚠ 潮汐模式检测失败: %v", err)
	} else {
		fmt.Printf("   ✓ 检测到 %d 台有潮汐规律的 VM\n", len(tidalResults))
		for i, r := range tidalResults {
			if i < 3 {
				fmt.Printf("     - %s: 模式 %s, 稳定性 %.0f%%\n",
					r.VMName, r.Pattern, r.StabilityScore)
			}
		}
	}

	// 4.4 健康评分
	fmt.Println("\n   4.4 健康评分...")
	healthResult, err := analysisEngine.AnalyzeHealthScore(connectionID, nil)
	if err != nil {
		log.Printf("   ⚠ 健康评分失败: %v", err)
	} else {
		fmt.Printf("   ✓ 健康评分: %.0f/100 (%s)\n",
			healthResult.OverallScore, healthResult.HealthLevel)
		fmt.Printf("     - 资源均衡: %.0f/100\n", healthResult.ResourceBalance)
		fmt.Printf("     - 超配风险: %.0f/100\n", healthResult.OvercommitRisk)
		fmt.Printf("     - 热点集中: %.0f/100\n", healthResult.HotspotConcentration)
	}

	// 生成测试报告
	fmt.Println("\n5. 生成测试报告...")
	report := map[string]interface{}{
		"timestamp":    time.Now().Format(time.RFC3339),
		"connection":   "H3C UIS 测试环境",
		"vmCount":      len(vms),
		"zombieVMs":    len(zombieResults),
		"rightSizeVMs": len(rightSizeResults),
		"tidalVMs":     len(tidalResults),
		"healthScore":  healthResult.OverallScore,
	}

	reportData, _ := json.MarshalIndent(report, "", "  ")
	fmt.Println(string(reportData))

	// 保存报告到文件
	reportFile := "/tmp/justfit_e2e_report.json"
	os.WriteFile(reportFile, reportData, 0644)
	fmt.Printf("\n   ✓ 报告已保存到: %s\n", reportFile)

	fmt.Println("\n==================")
	fmt.Println("端到端测试完成!")
}
