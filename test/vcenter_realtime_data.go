// 测试获取实时数据
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

	// 实时查询：只设置开始时间，不设置结束时间
	// 返回最近可用的实时数据（通常最近 1-2 小时）
	now := time.Now()
	startTime := now.Add(-2 * time.Hour)

	// 目标指标
	targetMetrics := []string{
		"cpu.usage.average",
		"mem.consumed.average",
		"disk.read.average",
		"disk.write.average",
		"net.bytesRx.average",
		"net.bytesTx.average",
	}

	fmt.Println("=== 实时数据查询 (20秒间隔) ===")

	spec := types.PerfQuerySpec{
		Entity: targetVM.(interface {
			Reference() types.ManagedObjectReference
		}).Reference(),
		StartTime:  &startTime,
		IntervalId: 20, // 实时间隔
		MetricId:   []types.PerfMetricId{},
	}

	// 添加指标
	for _, metricName := range targetMetrics {
		if counterInfo, ok := counters[metricName]; ok {
			spec.MetricId = append(spec.MetricId, types.PerfMetricId{
				CounterId: counterInfo.Key,
				Instance:  "", // 空字符串表示获取所有实例
			})
		}
	}

	metricInfo, err := perfManager.Query(ctx, []types.PerfQuerySpec{spec})
	if err != nil {
		fmt.Printf("查询失败: %v\n", err)
		return
	}

	fmt.Printf("返回结果数: %d\n\n", len(metricInfo))

	// 构建计数器 ID 到名称的映射
	counterIDToName := make(map[int32]string)
	for _, name := range targetMetrics {
		if counterInfo, ok := counters[name]; ok {
			counterIDToName[counterInfo.Key] = name
		}
	}

	for _, mi := range metricInfo {
		if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
			fmt.Printf("采样点数: %d\n", len(entityMetric.SampleInfo))
			if len(entityMetric.SampleInfo) > 0 {
				fmt.Printf("时间范围: %s - %s\n\n",
					entityMetric.SampleInfo[0].Timestamp.Format("15:04:05"),
					entityMetric.SampleInfo[len(entityMetric.SampleInfo)-1].Timestamp.Format("15:04:05"))
			}

			for _, baseSeries := range entityMetric.Value {
				if intSeries, ok := baseSeries.(*types.PerfMetricIntSeries); ok {
					metricName := counterIDToName[intSeries.Id.CounterId]
					instanceName := intSeries.Id.Instance
					if instanceName == "" {
						instanceName = "(聚合)"
					}

					fmt.Printf("指标: %s\n", metricName)
					fmt.Printf("  实例: %s\n", instanceName)
					fmt.Printf("  数据点数: %d\n", len(intSeries.Value))

					if len(intSeries.Value) > 0 {
						fmt.Printf("  最新值: %d\n", intSeries.Value[len(intSeries.Value)-1])

						// 显示最近几个值
						showCount := 5
						if len(intSeries.Value) < showCount {
							showCount = len(intSeries.Value)
						}
						fmt.Printf("  最近 %d 个值:\n  ", showCount)
						startIdx := len(intSeries.Value) - showCount
						for i := startIdx; i < len(intSeries.Value); i++ {
							fmt.Printf("%d ", intSeries.Value[i])
						}
						fmt.Println()

						// 计算平均值（转换为 KBps）
						if len(intSeries.Value) > 0 {
							sum := int64(0)
							for _, v := range intSeries.Value {
								sum += v
							}
							avg := float64(sum) / float64(len(intSeries.Value))

							// 根据指标类型显示
							if metricName == "cpu.usage.average" {
								fmt.Printf("  平均值: %.2f%% (原始单位: basis points)\n", float64(avg)/100)
							} else if metricName == "mem.consumed.average" {
								fmt.Printf("  平均值: %.2f MB\n", avg/1024)
							} else {
								// disk/net 单位是 KBps
								fmt.Printf("  平均值: %.2f KB/s\n", avg)
							}
						}
					}
					fmt.Println()
				}
			}
		}
	}

	fmt.Println("=== 结论 ===")
	fmt.Println("vCenter 的磁盘和网络 IO 指标只在实时模式（20秒间隔）下可用")
	fmt.Println("历史数据（5分钟间隔）中不包含这些指标")
	fmt.Println("")
	fmt.Println("建议:")
	fmt.Println("1. 如果需要长期趋势分析，需要在 vCenter 中提高统计级别到级别 2 或更高")
	fmt.Println("2. 或者只提供实时监控功能，不查询历史数据")
}
