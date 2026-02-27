// 检查所有数据中心的虚拟机指标
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

	perfManager := performance.NewManager(client.Client)
	finder := find.NewFinder(client.Client, false) // 不自动设置数据中心

	// 获取所有数据中心
	datacenters, err := finder.DatacenterList(ctx, "*")
	if err != nil {
		log.Fatalf("获取数据中心失败: %v", err)
	}

	fmt.Printf("=== 找到 %d 个数据中心 ===\n\n", len(datacenters))

	// 获取所有计数器信息
	counters, err := perfManager.CounterInfoByName(ctx)
	if err != nil {
		log.Fatal(err)
	}

	totalVMs := 0
	poweredOnVMs := 0
	testedVMs := 0
	maxTestVMs := 5 // 最多测试 5 台虚拟机

	// 遍历所有数据中心
	for _, dc := range datacenters {
		fmt.Printf("=== 数据中心: %s ===\n", dc.Name())
		finder.SetDatacenter(dc)

		vmList, err := finder.VirtualMachineList(ctx, "*")
		if err != nil {
			fmt.Printf("获取虚拟机列表失败: %v\n\n", err)
			continue
		}

		fmt.Printf("  虚拟机总数: %d\n", len(vmList))
		totalVMs += len(vmList)

		// 统计开机虚拟机
		dcPoweredOn := 0
		for _, vm := range vmList {
			var vmMo mo.VirtualMachine
			vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo)
			if vmMo.Summary.Runtime.PowerState == "poweredOn" {
				dcPoweredOn++
			}
		}
		fmt.Printf("  开机虚拟机: %d\n", dcPoweredOn)
		poweredOnVMs += dcPoweredOn

		// 测试开机虚拟机的指标
		if dcPoweredOn > 0 && testedVMs < maxTestVMs {
			fmt.Printf("\n  测试虚拟机指标可用性:\n")

			for _, vm := range vmList {
				if testedVMs >= maxTestVMs {
					break
				}

				var vmMo mo.VirtualMachine
				vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo)
				if vmMo.Summary.Runtime.PowerState != "poweredOn" {
					continue
				}

				// 跳过 vCLS
				if len(vmMo.Name) > 4 && vmMo.Name[:4] == "vCLS" {
					continue
				}

				testedVMs++
				vmName := vmMo.Name
				if len(vmName) > 30 {
					vmName = vmName[:30] + "..."
				}
				fmt.Printf("\n  [%d] %s\n", testedVMs, vmName)

				// 检查 5 分钟间隔的指标可用性
				availMetrics, err := perfManager.AvailableMetric(ctx, vm.Reference(), 300)
				if err != nil {
					fmt.Printf("      获取可用指标失败: %v\n", err)
					continue
				}

				// 构建可用指标 ID 集合
				validMetricIds := make(map[int32]bool)
				for _, m := range availMetrics {
					validMetricIds[m.CounterId] = true
				}

				// 检查目标指标
				targetMetrics := []string{
					"cpu.usage.average",
					"mem.consumed.average",
					"disk.read.average",
					"disk.write.average",
					"net.bytesRx.average",
					"net.bytesTx.average",
				}

				for _, metricName := range targetMetrics {
					if counterInfo, ok := counters[metricName]; ok && counterInfo != nil {
						isAvailable := validMetricIds[counterInfo.Key]
						if isAvailable {
							fmt.Printf("      ✅ %s (级别 %d)\n", metricName, counterInfo.Level)
						} else {
							fmt.Printf("      ❌ %s (级别 %d) - 不可用\n", metricName, counterInfo.Level)
						}
					}
				}
			}
		}

		fmt.Println()
	}

	fmt.Printf("=== 统计汇总 ===\n")
	fmt.Printf("总虚拟机数: %d\n", totalVMs)
	fmt.Printf("开机虚拟机: %d\n", poweredOnVMs)
	fmt.Printf("已测试虚拟机: %d\n", testedVMs)

	if poweredOnVMs == 0 {
		fmt.Println("\n⚠️  没有找到开机状态的虚拟机，无法验证指标采集功能")
		fmt.Println("   请确保至少有一台虚拟机处于开机状态")
	} else if testedVMs == 0 {
		fmt.Println("\n⚠️  所有开机虚拟机都是 vCLS（vCenter 内部服务虚拟机）")
		fmt.Println("   vCLS 虚拟机不产生实际的磁盘和网络指标")
	}
}
