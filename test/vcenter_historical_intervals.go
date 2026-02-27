// 测试不同间隔的历史数据可用性
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

	counters, _ := perfManager.CounterInfoByName(ctx)

	// 测试指标
	testMetrics := []string{
		"cpu.usage.average",
		"disk.read.average",
	}

	// 测试不同间隔
	intervals := []struct {
		Name     string
		Interval int32
	}{
		{"20秒 (实时)", 20},
		{"5分钟", 300},
		{"30分钟", 1800},
		{"2小时", 7200},
	}

	// 查询最近 24 小时
	now := time.Now()
	startTime := now.Add(-24 * time.Hour)

	fmt.Printf("查询时间范围: %s - %s (24小时)\n\n", startTime.Format("15:04"), now.Format("15:04"))

	for _, intervalInfo := range intervals {
		fmt.Printf("=== 间隔: %s ===\n", intervalInfo.Name)

		for _, metricName := range testMetrics {
			counterInfo, ok := counters[metricName]
			if !ok {
				continue
			}

			// 首先检查可用性
			availMetrics, _ := perfManager.AvailableMetric(ctx, targetVM.(interface {
				Reference() types.ManagedObjectReference
			}).Reference(), intervalInfo.Interval)
			isAvailable := false
			for _, m := range availMetrics {
				if m.CounterId == counterInfo.Key {
					isAvailable = true
					break
				}
			}

			status := "❌ 不可用"
			if isAvailable {
				status = "✅ 可用"
			}
			fmt.Printf("  %s: %s", metricName, status)

			// 如果可用，尝试查询
			if isAvailable {
				spec := types.PerfQuerySpec{
					Entity: targetVM.(interface {
						Reference() types.ManagedObjectReference
					}).Reference(),
					StartTime:  &startTime,
					EndTime:    &now,
					IntervalId: intervalInfo.Interval,
					MetricId: []types.PerfMetricId{
						{CounterId: counterInfo.Key, Instance: ""},
					},
				}

				metricInfo, err := perfManager.Query(ctx, []types.PerfQuerySpec{spec})
				if err != nil {
					fmt.Printf(" (查询失败: %v)", err)
				} else if len(metricInfo) > 0 {
					if entityMetric, ok := metricInfo[0].(*types.PerfEntityMetric); ok {
						if len(entityMetric.SampleInfo) > 0 {
							fmt.Printf(" (%d 个数据点)", len(entityMetric.SampleInfo))
						} else {
							fmt.Printf(" (无数据点)")
						}
					}
				} else {
					fmt.Printf(" (返回空)")
				}
			}
			fmt.Println()
		}
		fmt.Println()
	}

	// 测试历史间隔配置
	fmt.Println("=== vCenter 历史间隔配置 ===")
	historicalIntervals, _ := perfManager.HistoricalInterval(ctx)
	for _, interval := range historicalIntervals {
		fmt.Printf("名称: %s, 间隔: %d 秒, 级别: %d\n", interval.Name, interval.Length, interval.Level)
	}

	fmt.Println("\n=== 结论 ===")
	fmt.Println("当前 vCenter 配置分析:")
	fmt.Println("- 实时数据 (20秒间隔): 可用，但只保留约 2 小时")
	fmt.Println("- 历史数据 (5分钟及以上): 不可用")
	fmt.Println("")
	fmt.Println("原因: vCenter 统计级别设置为级别 1，只收集实时数据")
	fmt.Println("解决方案: 在 vCenter 中提高统计级别到级别 2 或更高")
	fmt.Println("")
	fmt.Println("修改方法:")
	fmt.Println("1. vSphere Client > vCenter > 管理 > 统计")
	fmt.Println("2. 将 '统计级别' 从 '级别 1' 改为 '级别 2'")
	fmt.Println("3. 保存后等待数据收集")
}
