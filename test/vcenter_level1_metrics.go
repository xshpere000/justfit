// 查找级别 1 的磁盘和网络指标
package main

import (
	"context"
	"fmt"
	"net/url"
	"sort"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/find"
	"github.com/vmware/govmomi/performance"
	"github.com/vmware/govmomi/session"
	"github.com/vmware/govmomi/vim25/mo"
	"github.com/vmware/govmomi/vim25/types"
)

func main() {
	host := "10.103.116.116"
	username := "administrator@vsphere.local"
	password := "Admin@123."
	insecure := true

	ctx := context.Background()
	u, _ := url.Parse(fmt.Sprintf("https://%s:%d/sdk", host, 443))
	client, _ := govmomi.NewClient(ctx, u, insecure)
	defer client.Logout(ctx)

	sm := session.NewManager(client.Client)
	userInfo := url.UserPassword(username, password)
	sm.Login(ctx, userInfo)

	perfManager := performance.NewManager(client.Client)
	counters, _ := perfManager.CounterInfoByName(ctx)

	// 获取一台开机虚拟机来测试可用性
	finder := find.NewFinder(client.Client, false)
	datacenters, _ := finder.DatacenterList(ctx, "*")
	finder.SetDatacenter(datacenters[len(datacenters)-1]) // 使用最后一个数据中心

	vmList, _ := finder.VirtualMachineList(ctx, "*")
	var testVM interface{}
	for _, vm := range vmList {
		var vmMo mo.VirtualMachine
		vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo)
		if vmMo.Summary.Runtime.PowerState == "poweredOn" && (len(vmMo.Name) <= 4 || vmMo.Name[:4] != "vCLS") {
			testVM = vm
			fmt.Printf("测试虚拟机: %s\n\n", vmMo.Name)
			break
		}
	}

	if testVM == nil {
		fmt.Println("没有找到合适的测试虚拟机")
		return
	}

	// 检查可用指标
	availMetrics, _ := perfManager.AvailableMetric(ctx, testVM.(interface {
		Reference() types.ManagedObjectReference
	}).Reference(), 300)
	validMetricIds := make(map[int32]bool)
	for _, m := range availMetrics {
		validMetricIds[m.CounterId] = true
	}

	// 查找所有级别 1 的磁盘和网络指标
	fmt.Println("=== 级别 1 的磁盘相关计数器 ===")
	diskCounters := []string{}
	for name, counterInfo := range counters {
		if counterInfo.Level == 1 && contains(name, "disk") {
			isAvailable := validMetricIds[counterInfo.Key]
			status := "❌"
			if isAvailable {
				status = "✅"
			}
			diskCounters = append(diskCounters, fmt.Sprintf("%s %s", status, name))
		}
	}
	sort.Strings(diskCounters)
	for _, s := range diskCounters {
		fmt.Println(" ", s)
	}

	fmt.Println("\n=== 级别 1 的网络相关计数器 ===")
	netCounters := []string{}
	for name, counterInfo := range counters {
		if counterInfo.Level == 1 && contains(name, "net") {
			isAvailable := validMetricIds[counterInfo.Key]
			status := "❌"
			if isAvailable {
				status = "✅"
			}
			netCounters = append(netCounters, fmt.Sprintf("%s %s", status, name))
		}
	}
	sort.Strings(netCounters)
	for _, s := range netCounters {
		fmt.Println(" ", s)
	}

	// 查找可用的替代指标
	fmt.Println("\n=== 可用的磁盘/网络替代指标 ===")
	alternatives := []string{
		"disk.usage.average",
		"disk.numberReadAveraged.average",
		"disk.numberWriteAveraged.average",
		"net.usage.average",
		"net.throughput.usage.average",
	}

	for _, name := range alternatives {
		if counterInfo, ok := counters[name]; ok {
			isAvailable := validMetricIds[counterInfo.Key]
			status := "❌"
			if isAvailable {
				status = "✅"
			}
			fmt.Printf("  %s %s (级别 %d)\n", status, name, counterInfo.Level)
		} else {
			fmt.Printf("  ❌ %s (不存在)\n", name)
		}
	}

	fmt.Println("\n=== 建议 ===")
	fmt.Println("vCenter 统计级别当前设置为级别 1，磁盘和网络指标不可用")
	fmt.Println("")
	fmt.Println("解决方案:")
	fmt.Println("1. 在 vCenter 中提高统计级别到级别 2 或更高:")
	fmt.Println("   - 导航到 vCenter Server > 管理 > 统计")
	fmt.Println("   - 将统计级别从 '级别 1' 改为 '级别 2' 或 '级别 3'")
	fmt.Println("   - 点击 '确定' 保存设置")
	fmt.Println("")
	fmt.Println("2. 或者使用可用的替代指标（如果有）")
	fmt.Println("")
	fmt.Println("注意: 更改统计级别后，可能需要等待一段时间才能收集到新的指标数据")
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr ||
		(len(s) > len(substr) && (s[:len(substr)] == substr ||
			s[len(s)-len(substr):] == substr ||
			containsMiddle(s, substr))))
}

func containsMiddle(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
