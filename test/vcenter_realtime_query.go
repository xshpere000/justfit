// 测试不同的查询方式
package main

import (
	"context"
	"fmt"
	"net/url"
	"time"

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
	finder := find.NewFinder(client.Client, false)

	datacenters, _ := finder.DatacenterList(ctx, "*")
	finder.SetDatacenter(datacenters[len(datacenters)-1])

	vmList, _ := finder.VirtualMachineList(ctx, "*")

	// 找一台非 vCLS 的开机虚拟机
	var targetVM interface{}
	var vmName string
	for _, vm := range vmList {
		var vmMo mo.VirtualMachine
		vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo)
		if vmMo.Summary.Runtime.PowerState == "poweredOn" && (len(vmMo.Name) <= 4 || vmMo.Name[:4] != "vCLS") {
			targetVM = vm
			vmName = vmMo.Name
			break
		}
	}

	if targetVM == nil {
		fmt.Println("没有找到合适的测试虚拟机")
		return
	}

	fmt.Printf("测试虚拟机: %s\n\n", vmName)

	// 获取计数器信息
	counters, _ := perfManager.CounterInfoByName(ctx)

	endTime := time.Now()
	startTime := endTime.Add(-24 * time.Hour)

	// 测试目标指标
	targetMetrics := []string{
		"disk.read.average",
		"disk.write.average",
		"net.bytesRx.average",
		"net.bytesTx.average",
	}

	for _, metricName := range targetMetrics {
		counterInfo, ok := counters[metricName]
		if !ok {
			fmt.Printf("❌ %s - 计数器不存在\n\n", metricName)
			continue
		}

		fmt.Printf("=== 测试指标: %s (级别 %d) ===\n", metricName, counterInfo.Level)

		// 1. 检查可用性
		availMetrics, _ := perfManager.AvailableMetric(ctx, targetVM.(interface {
			Reference() types.ManagedObjectReference
		}).Reference(), 300)
		counterID := counterInfo.Key
		isAvailable := false
		for _, m := range availMetrics {
			if m.CounterId == counterID {
				isAvailable = true
				fmt.Printf("  可用性: ✅ 可用\n")
				fmt.Printf("  实例: %s\n", m.Instance)
				break
			}
		}
		if !isAvailable {
			fmt.Printf("  可用性: ❌ 不可用 (5分钟间隔)\n")

			// 尝试其他间隔
			for _, interval := range []int32{20, 60, 300, 600} {
				availMetrics, _ := perfManager.AvailableMetric(ctx, targetVM.(interface {
					Reference() types.ManagedObjectReference
				}).Reference(), interval)
				for _, m := range availMetrics {
					if m.CounterId == counterID {
						fmt.Printf("  可用性: ✅ 可用 (%d秒间隔)\n", interval)
						fmt.Printf("  实例: %s\n", m.Instance)
						break
					}
				}
			}
		}

		// 2. 尝试查询（使用空实例，让 vCenter 返回所有实例）
		spec := types.PerfQuerySpec{
			Entity: targetVM.(interface {
				Reference() types.ManagedObjectReference
			}).Reference(),
			StartTime:  &startTime,
			EndTime:    &endTime,
			IntervalId: 300,
			MetricId: []types.PerfMetricId{
				{CounterId: counterID, Instance: ""},
			},
		}

		metricInfo, err := perfManager.Query(ctx, []types.PerfQuerySpec{spec})
		if err != nil {
			fmt.Printf("  查询结果: ❌ 查询失败 - %v\n\n", err)
			continue
		}

		if len(metricInfo) == 0 {
			fmt.Printf("  查询结果: ❌ 无数据返回\n\n")
			continue
		}

		// 分析结果
		dataFound := false
		for _, mi := range metricInfo {
			if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
				for _, baseSeries := range entityMetric.Value {
					if intSeries, ok := baseSeries.(*types.PerfMetricIntSeries); ok {
						dataFound = true
						instanceName := intSeries.Id.Instance
						if instanceName == "" {
							instanceName = "(聚合)"
						}
						fmt.Printf("  查询结果: ✅ 找到数据\n")
						fmt.Printf("  实例: %s\n", instanceName)
						fmt.Printf("  数据点数: %d\n", len(intSeries.Value))

						if len(intSeries.Value) > 0 {
							fmt.Printf("  最新值: %d\n", intSeries.Value[len(intSeries.Value)-1])
							if len(intSeries.Value) > 1 {
								fmt.Printf("  时间范围: %s - %s\n",
									entityMetric.SampleInfo[0].Timestamp.Format("15:04:05"),
									entityMetric.SampleInfo[len(entityMetric.SampleInfo)-1].Timestamp.Format("15:04:05"))
							}
						}
					}
				}
			}
		}

		if !dataFound {
			fmt.Printf("  查询结果: ❌ 查询成功但无数据\n")
		}
		fmt.Println()
	}

	// 3. 测试实时查询
	fmt.Println("=== 测试实时查询 (Real-time) ===")
	realtimeSpec := types.PerfQuerySpec{
		Entity: targetVM.(interface {
			Reference() types.ManagedObjectReference
		}).Reference(),
		IntervalId: 20, // 实时查询使用 20 秒间隔
		MetricId:   []types.PerfMetricId{},
		StartTime:  &startTime,
		EndTime:    &endTime,
	}

	// 添加所有目标指标
	for _, metricName := range targetMetrics {
		if counterInfo, ok := counters[metricName]; ok {
			realtimeSpec.MetricId = append(realtimeSpec.MetricId, types.PerfMetricId{
				CounterId: counterInfo.Key,
				Instance:  "",
			})
		}
	}

	realtimeInfo, err := perfManager.Query(ctx, []types.PerfQuerySpec{realtimeSpec})
	if err != nil {
		fmt.Printf("实时查询失败: %v\n", err)
	} else {
		fmt.Printf("实时查询返回 %d 条结果\n", len(realtimeInfo))
		for _, mi := range realtimeInfo {
			if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
				fmt.Printf("  包含 %d 个指标序列\n", len(entityMetric.Value))
			}
		}
	}
}
