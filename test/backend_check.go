package main

import (
	"fmt"
	"log"
	"time"

	"justfit/internal/connector"
	"justfit/internal/storage"
)

// 测试 H3C UIS 连接和数据采集
func testH3CUISConnection() error {
	fmt.Println("=== 测试 H3C UIS 连接 ===")

	config := &connector.ConnectionConfig{
		Name:     "测试 H3C UIS",
		Platform: connector.PlatformH3CUIS,
		Host:     "10.103.125.116",
		Port:     443,
		Username: "admin",
		Password: "Admin@123.",
		Insecure: true,
	}

	// 测试连接
	client, err := connector.NewConnector(config)
	if err != nil {
		return fmt.Errorf("创建 UIS 连接器失败: %w", err)
	}
	defer client.Close()

	// 测试连接是否正常
	if err := client.TestConnection(); err != nil {
		return fmt.Errorf("测试 UIS 连接失败: %w", err)
	}
	fmt.Println("✓ UIS 连接成功")

	// 获取虚拟机列表
	vms, err := client.GetVMs()
	if err != nil {
		return fmt.Errorf("获取虚拟机列表失败: %w", err)
	}
	fmt.Printf("✓ 获取到 %d 台虚拟机\n", len(vms))
	for i, vm := range vms {
		if i < 5 { // 只显示前5个
			fmt.Printf("  - %s: %d vCPU, %d MB 内存, 状态: %s\n",
				vm.Name, vm.CpuCount, vm.MemoryMB, vm.PowerState)
		}
	}

	// 获取集群列表
	clusters, err := client.GetClusters()
	if err != nil {
		return fmt.Errorf("获取集群列表失败: %w", err)
	}
	fmt.Printf("✓ 获取到 %d 个集群\n", len(clusters))

	// 获取主机列表
	hosts, err := client.GetHosts()
	if err != nil {
		return fmt.Errorf("获取主机列表失败: %w", err)
	}
	fmt.Printf("✓ 获取到 %d 台主机\n", len(hosts))

	// 测试性能指标获取
	if len(vms) > 0 {
		vm := vms[0]
		fmt.Printf("\n=== 测试获取虚拟机性能指标: %s ===\n", vm.Name)

		startTime := time.Now().AddDate(0, 0, -7)
		endTime := time.Now()

		metrics, err := client.GetVMMetrics(
			vm.Datacenter,
			vm.Name,
			vm.UUID,
			startTime,
			endTime,
			vm.CpuCount,
		)
		if err != nil {
			fmt.Printf("⚠ 获取性能指标失败: %v\n", err)
			fmt.Println("  (这可能是由于测试环境没有历史数据)")
		} else {
			fmt.Printf("✓ 获取到性能指标:\n")
			fmt.Printf("  - CPU 样本数: %d\n", len(metrics.CPU))
			fmt.Printf("  - 内存样本数: %d\n", len(metrics.Memory))
			fmt.Printf("  - 磁盘读样本数: %d\n", len(metrics.DiskRead))
			fmt.Printf("  - 磁盘写样本数: %d\n", len(metrics.DiskWrite))
			fmt.Printf("  - 网络接收样本数: %d\n", len(metrics.NetRx))
			fmt.Printf("  - 网络发送样本数: %d\n", len(metrics.NetTx))
		}
	}

	return nil
}

// 测试数据库功能
func testDatabase() error {
	fmt.Println("\n=== 测试数据库功能 ===")

	// 初始化数据库
	if err := storage.Init(&storage.Config{}); err != nil {
		return fmt.Errorf("初始化数据库失败: %w", err)
	}
	defer storage.Close()

	// 创建仓储
	repos := storage.NewRepositories()

	// 测试连接创建
	conn := &storage.Connection{
		Name:     "测试连接",
		Platform: "h3c-uis",
		Host:     "10.103.125.116",
		Port:     443,
		Username: "admin",
		Status:   "connected",
	}

	if err := repos.Connection.Create(conn); err != nil {
		return fmt.Errorf("创建连接记录失败: %w", err)
	}
	fmt.Printf("✓ 创建连接记录 (ID: %d)\n", conn.ID)

	// 查询连接
	connections, err := repos.Connection.List()
	if err != nil {
		return fmt.Errorf("查询连接列表失败: %w", err)
	}
	fmt.Printf("✓ 查询到 %d 条连接记录\n", len(connections))

	// 清理测试数据
	if err := repos.Connection.Delete(conn.ID); err != nil {
		fmt.Printf("⚠ 清理测试数据失败: %v\n", err)
	}

	return nil
}

func main() {
	fmt.Println("JustFit 后端功能测试")
	fmt.Println("====================\n")

	// 测试 H3C UIS 连接
	if err := testH3CUISConnection(); err != nil {
		log.Fatalf("H3C UIS 测试失败: %v", err)
	}

	// 测试数据库
	if err := testDatabase(); err != nil {
		log.Fatalf("数据库测试失败: %v", err)
	}

	fmt.Println("\n====================")
	fmt.Println("所有测试通过!")
}
