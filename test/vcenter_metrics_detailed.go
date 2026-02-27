// 详细测试 vCenter 指标采集情况
package main

import (
	"context"
	"fmt"
	"log"
	"net/url"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/find"
	"github.com/vmware/govmomi/performance"
	"github.com/vmware/govmomi/session"
	"github.com/vmware/govmomi/vim25/mo"
)

func main() {
	host := "10.103.116.116"
	port := 443
	username := "administrator@vsphere.local"
	password := "Admin@123."
	insecure := true

	ctx := context.Background()
	u, err := url.Parse(fmt.Sprintf("https://%s:%d/sdk", host, port))
	if err != nil {
		log.Fatal(err)
	}

	client, err := govmomi.NewClient(ctx, u, insecure)
	if err != nil {
		log.Fatal(err)
	}
	defer client.Logout(ctx)

	sm := session.NewManager(client.Client)
	userInfo := url.UserPassword(username, password)
	if err := sm.Login(ctx, userInfo); err != nil {
		log.Fatal(err)
	}

	finder := find.NewFinder(client.Client, true)

	datacenters, err := finder.DatacenterList(ctx, "*")
	if err != nil || len(datacenters) == 0 {
		log.Fatal(err)
	}
	finder.SetDatacenter(datacenters[0])

	vmList, err := finder.VirtualMachineList(ctx, "*")
	if err != nil || len(vmList) == 0 {
		log.Fatal(err)
	}

	perfManager := performance.NewManager(client.Client)

	// 获取所有计数器信息
	counters, err := perfManager.CounterInfoByName(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// 搜索所有磁盘和网络相关的计数器
	fmt.Println("=== 查找所有磁盘和网络相关计数器 ===")

	diskCounters := []string{}
	netCounters := []string{}

	for name := range counters {
		if name == "" {
			continue
		}
		if contains(name, "disk") {
			diskCounters = append(diskCounters, name)
		}
		if contains(name, "net") {
			netCounters = append(netCounters, name)
		}
	}

	fmt.Printf("\n磁盘计数器 (%d 个):\n", len(diskCounters))
	for _, name := range diskCounters {
		fmt.Printf("  - %s\n", name)
	}

	fmt.Printf("\n网络计数器 (%d 个):\n", len(netCounters))
	for _, name := range netCounters {
		fmt.Printf("  - %s\n", name)
	}

	// 测试前 10 台开机状态的非 vCLS VM
	fmt.Println("\n=== 检查各虚拟机的可用指标 ===")
	vmCount := 0
	for _, vm := range vmList {
		if vmCount >= 10 {
			break
		}

		var vmMo mo.VirtualMachine
		if err := vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo); err != nil {
			continue
		}
		if vmMo.Summary.Runtime.PowerState != "poweredOn" {
			continue
		}

		// 跳过 vCLS 虚拟机
		if len(vmMo.Name) > 4 && vmMo.Name[:4] == "vCLS" {
			continue
		}

		vmCount++
		fmt.Printf("\n虚拟机 #%d: %s\n", vmCount, vmMo.Name)

		// 检查可用指标
		availMetrics, err := perfManager.AvailableMetric(ctx, vm.Reference(), 300)
		if err != nil {
			fmt.Printf("  获取可用指标失败: %v\n", err)
			continue
		}

		validMetricIds := make(map[int32]bool)
		for _, m := range availMetrics {
			validMetricIds[m.CounterId] = true
		}

		// 检查常见的磁盘和网络指标
		testMetrics := []string{
			"disk.read.average",
			"disk.write.average",
			"disk.usage.average",
			"net.bytesRx.average",
			"net.bytesTx.average",
			"net.usage.average",
			"virtualDisk.read.average",
			"virtualDisk.write.average",
		}

		for _, metricName := range testMetrics {
			if counterInfo, ok := counters[metricName]; ok && counterInfo != nil {
				isAvailable := validMetricIds[counterInfo.Key]
				status := "❌"
				if isAvailable {
					status = "✅"
				}
				fmt.Printf("  %s %s\n", status, metricName)
			}
		}
	}

	fmt.Println("\n=== 测试完成 ===")
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr ||
		len(s) > len(substr) && (s[:len(substr)] == substr ||
			s[len(s)-len(substr):] == substr ||
			containsMiddle(s, substr)))
}

func containsMiddle(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
