// 测试修改后的 vCenter connector
package main

import (
	"fmt"
	"time"

	"justfit/internal/connector"
)

func main() {
	config := &connector.ConnectionConfig{
		ID:       1,
		Name:     "测试连接",
		Platform: connector.PlatformVCenter,
		Host:     "10.103.116.116",
		Port:     443,
		Username: "administrator@vsphere.local",
		Password: "Admin@123.",
		Insecure: true,
	}

	client, err := connector.NewVCenterClient(config)
	if err != nil {
		fmt.Printf("连接失败: %v\n", err)
		return
	}
	defer client.Close()

	// 测试获取指标
	endTime := time.Now()
	startTime := endTime.Add(-2 * time.Hour)

	metrics, err := client.GetVMMetrics("Datacenter", "FIO001_test", "", startTime, endTime, 4)
	if err != nil {
		fmt.Printf("获取指标失败: %v\n", err)
		return
	}

	fmt.Printf("虚拟机: %s\n\n", metrics.VMName)
	fmt.Printf("CPU 数据点: %d\n", len(metrics.CPU))
	fmt.Printf("内存 数据点: %d\n", len(metrics.Memory))
	fmt.Printf("磁盘读 数据点: %d\n", len(metrics.DiskRead))
	fmt.Printf("磁盘写 数据点: %d\n", len(metrics.DiskWrite))
	fmt.Printf("网络接收 数据点: %d\n", len(metrics.NetRx))
	fmt.Printf("网络发送 数据点: %d\n", len(metrics.NetTx))

	totalDataPoints := len(metrics.CPU) + len(metrics.Memory) + len(metrics.DiskRead) + len(metrics.DiskWrite) + len(metrics.NetRx) + len(metrics.NetTx)
	fmt.Printf("\n总数据点数: %d\n", totalDataPoints)

	if totalDataPoints == 0 {
		fmt.Println("\n❌ 没有获取到任何数据")
		return
	}

	// 显示最新值
	fmt.Println("\n=== 最新值 ===")
	if len(metrics.CPU) > 0 {
		latest := metrics.CPU[len(metrics.CPU)-1]
		fmt.Printf("CPU: %.2f (时间: %s)\n", latest.Value, latest.Timestamp.Format("15:04:05"))
	}
	if len(metrics.Memory) > 0 {
		latest := metrics.Memory[len(metrics.Memory)-1]
		fmt.Printf("内存: %.2f MB (时间: %s)\n", latest.Value, latest.Timestamp.Format("15:04:05"))
	}
	if len(metrics.DiskRead) > 0 {
		latest := metrics.DiskRead[len(metrics.DiskRead)-1]
		fmt.Printf("磁盘读: %.2f KB/s (时间: %s)\n", latest.Value, latest.Timestamp.Format("15:04:05"))
	}
	if len(metrics.DiskWrite) > 0 {
		latest := metrics.DiskWrite[len(metrics.DiskWrite)-1]
		fmt.Printf("磁盘写: %.2f KB/s (时间: %s)\n", latest.Value, latest.Timestamp.Format("15:04:05"))
	}
	if len(metrics.NetRx) > 0 {
		latest := metrics.NetRx[len(metrics.NetRx)-1]
		fmt.Printf("网络接收: %.2f KB/s (时间: %s)\n", latest.Value, latest.Timestamp.Format("15:04:05"))
	}
	if len(metrics.NetTx) > 0 {
		latest := metrics.NetTx[len(metrics.NetTx)-1]
		fmt.Printf("网络发送: %.2f KB/s (时间: %s)\n", latest.Value, latest.Timestamp.Format("15:04:05"))
	}

	// 验证所有指标都有数据
	fmt.Println("\n=== 验证结果 ===")
	allMetricsAvailable := len(metrics.CPU) > 0 && len(metrics.Memory) > 0 &&
		len(metrics.DiskRead) > 0 && len(metrics.DiskWrite) > 0 &&
		len(metrics.NetRx) > 0 && len(metrics.NetTx) > 0

	if allMetricsAvailable {
		fmt.Println("✅ 所有 6 种指标都已成功获取！")
	} else {
		fmt.Println("❌ 部分指标缺失")
	}
}
