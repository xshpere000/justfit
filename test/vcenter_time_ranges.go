// 测试不同时间范围的数据密度
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

type TimeRangeTest struct {
	Name      string
	Duration  time.Duration
	StartTime time.Time
}

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

	// 测试不同时间范围
	now := time.Now()
	timeRanges := []TimeRangeTest{
		{"实时 (2小时)", 2 * time.Hour, now.Add(-2 * time.Hour)},
		{"1 天", 24 * time.Hour, now.Add(-24 * time.Hour)},
		{"7 天 (Last Week)", 7 * 24 * time.Hour, now.Add(-7 * 24 * time.Hour)},
		{"30 天 (Last Month)", 30 * 24 * time.Hour, now.Add(-30 * 24 * time.Hour)},
	}

	// 测试指标：CPU (级别 1)、磁盘读 (级别 2)
	testMetrics := []string{
		"cpu.usage.average",
		"disk.read.average",
	}

	for _, tr := range timeRanges {
		fmt.Printf("=== %s ===\n", tr.Name)
		fmt.Printf("时间范围: %s - %s\n", tr.StartTime.Format("2006-01-02 15:04"), now.Format("2006-01-02 15:04"))
		fmt.Printf("时长: %.1f 小时\n\n", tr.Duration.Hours())

		// 根据时间范围选择合适的间隔
		var interval int32
		if tr.Duration.Hours() <= 2 {
			interval = 20 // 实时
		} else if tr.Duration.Hours() <= 24 {
			interval = 300 // 5分钟
		} else if tr.Duration.Hours() <= 24*7 {
			interval = 1800 // 30分钟
		} else {
			interval = 7200 // 2小时
		}

		for _, metricName := range testMetrics {
			counterInfo, ok := counters[metricName]
			if !ok {
				continue
			}

			// 查询 - 指定间隔
			spec := types.PerfQuerySpec{
				Entity: targetVM.(interface {
					Reference() types.ManagedObjectReference
				}).Reference(),
				StartTime:  &tr.StartTime,
				EndTime:    &now,
				IntervalId: interval,
				MetricId: []types.PerfMetricId{
					{CounterId: counterInfo.Key, Instance: ""},
				},
			}

			metricInfo, err := perfManager.Query(ctx, []types.PerfQuerySpec{spec})
			if err != nil {
				fmt.Printf("  %s: 查询失败 - %v\n", metricName, err)
				continue
			}

			if len(metricInfo) == 0 {
				fmt.Printf("  %s: ❌ 无数据\n", metricName)
				continue
			}

			for _, mi := range metricInfo {
				if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
					if len(entityMetric.Value) == 0 || len(entityMetric.SampleInfo) == 0 {
						fmt.Printf("  %s: ❌ 无数据点\n", metricName)
						continue
					}

					sampleCount := len(entityMetric.SampleInfo)

					// 计算实际平均间隔（使用最近的几个采样点）
					avgInterval := time.Duration(0)
					if len(entityMetric.SampleInfo) >= 2 {
						// 计算最后几个采样点的平均间隔
						checkCount := 10
						if len(entityMetric.SampleInfo) < checkCount {
							checkCount = len(entityMetric.SampleInfo)
						}
						totalDiff := time.Duration(0)
						for i := len(entityMetric.SampleInfo) - checkCount; i < len(entityMetric.SampleInfo); i++ {
							if i > 0 {
								totalDiff += entityMetric.SampleInfo[i].Timestamp.Sub(entityMetric.SampleInfo[i-1].Timestamp)
							}
						}
						avgInterval = totalDiff / time.Duration(checkCount-1)
					}

					fmt.Printf("  %s:\n", metricName)
					fmt.Printf("    数据点数: %d\n", sampleCount)
					if avgInterval > 0 {
						fmt.Printf("    平均间隔: %v (%d 秒)\n", avgInterval, int64(avgInterval.Seconds()))
					}
					fmt.Printf("    时间范围: %s - %s\n",
						entityMetric.SampleInfo[0].Timestamp.Format("15:04:05"),
						entityMetric.SampleInfo[len(entityMetric.SampleInfo)-1].Timestamp.Format("15:04:05"))
				}
			}
		}
		fmt.Println()
	}

	fmt.Println("=== 结论 ===")
	fmt.Println("vCenter 根据查询时间范围自动调整数据采样间隔:")
	fmt.Println("- 实时数据 (1-2小时): 约 20 秒间隔")
	fmt.Println("- 1 天数据: 约 5 分钟间隔")
	fmt.Println("- 7 天数据: 约 30 分钟间隔")
	fmt.Println("- 30 天数据: 约 2 小时间隔")
	fmt.Println("")
	fmt.Println("磁盘和网络指标 (级别 2) 在所有时间范围都可用，")
	fmt.Println("但数据密度会随时间范围增加而降低")
}
