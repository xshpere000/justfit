// 测试 vCenter 指标采集情况
package main

import (
	"context"
	"fmt"
	"log"
	"net/url"
	"time"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/find"
	"github.com/vmware/govmomi/object"
	"github.com/vmware/govmomi/performance"
	"github.com/vmware/govmomi/session"
	"github.com/vmware/govmomi/vim25/mo"
	"github.com/vmware/govmomi/vim25/types"
)

func main() {
	// 连接配置
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
		log.Fatalf("连接 vCenter 失败: %v", err)
	}
	defer client.Logout(ctx)

	sm := session.NewManager(client.Client)
	userInfo := url.UserPassword(username, password)
	if err := sm.Login(ctx, userInfo); err != nil {
		log.Fatalf("登录失败: %v", err)
	}

	finder := find.NewFinder(client.Client, true)

	// 获取数据中心
	datacenters, err := finder.DatacenterList(ctx, "*")
	if err != nil || len(datacenters) == 0 {
		log.Fatalf("获取数据中心失败: %v", err)
	}
	finder.SetDatacenter(datacenters[0])

	// 获取第一台开机状态的 VM
	vmList, err := finder.VirtualMachineList(ctx, "*")
	if err != nil || len(vmList) == 0 {
		log.Fatalf("获取虚拟机列表失败: %v", err)
	}

	var targetVM *object.VirtualMachine
	for _, vm := range vmList {
		var vmMo mo.VirtualMachine
		if err := vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo); err != nil {
			continue
		}
		if vmMo.Summary.Runtime.PowerState == "poweredOn" {
			targetVM = vm
			fmt.Printf("选择测试虚拟机: %s\n", vmMo.Name)
			break
		}
	}

	if targetVM == nil {
		log.Fatal("没有找到开机状态的虚拟机")
	}

	perfManager := performance.NewManager(client.Client)

	// 所有要检查的指标
	counterNames := []string{
		"cpu.usage.average",
		"mem.consumed.average",
		"disk.read.average",
		"disk.write.average",
		"net.bytesRx.average",
		"net.bytesTx.average",
	}

	// 获取可用的性能计数器
	endTime := time.Now()
	startTime := endTime.Add(-24 * time.Hour)

	availMetrics, err := perfManager.AvailableMetric(ctx, targetVM.Reference(), 300)
	if err != nil {
		log.Fatalf("获取可用指标失败: %v", err)
	}

	// 构建可用指标 ID 集合
	validMetricIds := make(map[int32]bool)
	for _, m := range availMetrics {
		validMetricIds[m.CounterId] = true
	}

	// 获取所有计数器信息
	counters, err := perfManager.CounterInfoByName(ctx)
	if err != nil {
		log.Fatalf("获取计数器信息失败: %v", err)
	}

	fmt.Println("\n=== 指标可用性检查 ===")
	availableCounters := []types.PerfMetricId{}

	for _, counterName := range counterNames {
		if counterInfo, ok := counters[counterName]; ok && counterInfo != nil {
			counterID := counterInfo.Key
			isAvailable := validMetricIds[counterID]
			status := "❌ 不可用"
			if isAvailable {
				status = "✅ 可用"
				availableCounters = append(availableCounters, types.PerfMetricId{
					CounterId: counterID,
					Instance:  "*",
				})
			}
			fmt.Printf("%-25s : %s (CounterID: %d)\n", counterName, status, counterID)
		} else {
			fmt.Printf("%-25s : ❌ 计数器不存在\n", counterName)
		}
	}

	if len(availableCounters) == 0 {
		fmt.Println("\n❌ 没有可用的指标，无法进行查询测试")
		return
	}

	// 尝试查询指标
	fmt.Println("\n=== 执行指标查询 ===")
	spec := types.PerfQuerySpec{
		Entity:     targetVM.Reference(),
		StartTime:  &startTime,
		EndTime:    &endTime,
		IntervalId: 300,
		MetricId:   availableCounters,
	}

	metricInfo, err := perfManager.Query(ctx, []types.PerfQuerySpec{spec})
	if err != nil {
		log.Fatalf("查询性能指标失败: %v", err)
	}

	// 构建计数器 ID 到名称的反向映射
	counterIDToName := make(map[int32]string)
	for _, counterName := range counterNames {
		if counterInfo, ok := counters[counterName]; ok && counterInfo != nil {
			counterIDToName[counterInfo.Key] = counterName
		}
	}

	fmt.Println("\n=== 查询结果统计 ===")
	for _, mi := range metricInfo {
		if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
			for _, baseSeries := range entityMetric.Value {
				if intSeries, ok := baseSeries.(*types.PerfMetricIntSeries); ok {
					counterName := counterIDToName[intSeries.Id.CounterId]
					sampleCount := len(intSeries.Value)
					fmt.Printf("%-25s : %d 个数据点\n", counterName, sampleCount)
				}
			}
		}
	}

	fmt.Println("\n=== 测试完成 ===")
}
