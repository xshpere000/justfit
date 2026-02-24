package main

import (
	"context"
	"fmt"
	"net/url"
	"os"
	"time"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/find"
	"github.com/vmware/govmomi/object"
	"github.com/vmware/govmomi/performance"
	"github.com/vmware/govmomi/session"
	"github.com/vmware/govmomi/vim25/mo"
	"github.com/vmware/govmomi/vim25/types"
)

// VCenterClient vCenter 客户端封装
type VCenterClient struct {
	client   *govmomi.Client
	ctx      context.Context
	username string
	password string
}

// NewVCenterClient 创建 vCenter 客户端
func NewVCenterClient(server, username, password string) (*VCenterClient, error) {
	ctx := context.Background()

	// 构建 URL
	u, err := url.Parse("https://" + server + "/sdk")
	if err != nil {
		return nil, fmt.Errorf("解析 URL 失败: %w", err)
	}

	// 连接 vCenter
	client, err := govmomi.NewClient(ctx, u, true)
	if err != nil {
		return nil, fmt.Errorf("连接 vCenter 失败: %w", err)
	}

	// 使用 session.Manager 登录
	sm := session.NewManager(client.Client)
	userInfo := url.UserPassword(username, password)
	err = sm.Login(ctx, userInfo)
	if err != nil {
		client.Logout(ctx)
		return nil, fmt.Errorf("登录失败: %w", err)
	}

	return &VCenterClient{
		client:   client,
		ctx:      ctx,
		username: username,
		password: password,
	}, nil
}

// Close 关闭连接
func (vc *VCenterClient) Close() error {
	if vc.client != nil {
		vc.client.Logout(vc.ctx)
	}
	return nil
}

// GetVMs 获取所有虚拟机信息
func (vc *VCenterClient) GetVMs() ([]map[string]interface{}, error) {
	finder := find.NewFinder(vc.client.Client, true)

	datacenters, err := finder.DatacenterList(vc.ctx, "*")
	if err != nil {
		return nil, fmt.Errorf("获取数据中心列表失败: %w", err)
	}

	var vms []map[string]interface{}

	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		vmList, err := finder.VirtualMachineList(vc.ctx, "*")
		if err != nil {
			continue
		}

		for _, vm := range vmList {
			var vmMo mo.VirtualMachine
			err = vm.Properties(vc.ctx, vm.Reference(), []string{"name", "summary"}, &vmMo)
			if err != nil {
				continue
			}

			hostName := ""
			if vmMo.Summary.Runtime.Host != nil {
				hostObj := object.NewHostSystem(vc.client.Client, *vmMo.Summary.Runtime.Host)
				hostName = hostObj.Name()
			}

			connectionState := string(vmMo.Summary.Runtime.ConnectionState)

			vms = append(vms, map[string]interface{}{
				"name":            vmMo.Name,
				"datacenter":      dc.Name(),
				"cpuCount":        vmMo.Summary.Config.NumCpu,
				"memoryMB":        vmMo.Summary.Config.MemorySizeMB,
				"powerState":      vmMo.Summary.Runtime.PowerState,
				"connectionState": connectionState,
				"ipAddress":       vmMo.Summary.Guest.IpAddress,
				"guestOS":         vmMo.Summary.Guest.GuestFullName,
				"hostName":        hostName,
				"overallStatus":   vmMo.Summary.OverallStatus,
				"uuid":            vmMo.Summary.Config.Uuid,
			})
		}
	}

	return vms, nil
}

// GetVMMetrics 获取虚拟机性能指标
func (vc *VCenterClient) GetVMMetrics(datacenter, vmName, vmUUID string, startTime, endTime time.Time, cpuCount int32) (map[string]int, error) {
	finder := find.NewFinder(vc.client.Client, true)

	// 设置数据中心
	dc, err := finder.Datacenter(vc.ctx, datacenter)
	if err != nil {
		return nil, fmt.Errorf("查找数据中心失败: %w", err)
	}
	finder.SetDatacenter(dc)

	// 查找虚拟机
	var vm *object.VirtualMachine
	if vmUUID != "" {
		// 通过 UUID 查找
		vm, err = finder.VirtualMachine(vc.ctx, vmName)
	} else {
		vm, err = finder.VirtualMachine(vc.ctx, vmName)
	}

	if err != nil {
		return nil, fmt.Errorf("查找虚拟机失败: %w", err)
	}

	perfManager := performance.NewManager(vc.client.Client)

	// 定义要采集的指标
	counterNames := []string{
		"cpu.usage.average",
		"mem.consumed.average",
		"disk.read.average",
		"disk.write.average",
		"net.bytesRx.average",
		"net.bytesTx.average",
	}

	// 获取可用的性能计数器
	availMetrics, err := perfManager.AvailableMetric(vc.ctx, vm.Reference(), 300)
	if err != nil {
		return nil, fmt.Errorf("获取可用指标失败: %w", err)
	}

	fmt.Printf("    可用指标数量: %d\n", len(availMetrics))

	// 获取所有计数器信息
	counters, err := perfManager.CounterInfoByName(vc.ctx)
	if err != nil {
		return nil, fmt.Errorf("获取计数器信息失败: %w", err)
	}

	// 构建查询规格
	spec := types.PerfQuerySpec{
		Entity:     vm.Reference(),
		StartTime:  &startTime,
		EndTime:    &endTime,
		IntervalId: 300, // 5分钟间隔
		MetricId:   make([]types.PerfMetricId, 0),
	}

	// 构建可用指标 ID 集合
	validMetricIds := make(map[int32]bool)
	for _, m := range availMetrics {
		validMetricIds[m.CounterId] = true
	}

	// 查找计数器 ID
	for _, counterName := range counterNames {
		if counterInfo, ok := counters[counterName]; ok && counterInfo != nil {
			counterID := counterInfo.Key
			// 只添加实际可用的指标
			if validMetricIds[counterID] {
				spec.MetricId = append(spec.MetricId, types.PerfMetricId{
					CounterId: counterID,
					Instance:  "*",
				})
				fmt.Printf("    添加指标: %s (ID: %d)\n", counterName, counterID)
			} else {
				fmt.Printf("    指标不可用: %s (ID: %d)\n", counterName, counterID)
			}
		} else {
			fmt.Printf("    找不到指标: %s\n", counterName)
		}
	}

	if len(spec.MetricId) == 0 {
		return nil, fmt.Errorf("没有可用的性能指标")
	}

	fmt.Printf("    查询 %d 个指标...\n", len(spec.MetricId))

	// 使用 Query 查询指标
	metricInfo, err := perfManager.Query(vc.ctx, []types.PerfQuerySpec{spec})
	if err != nil {
		return nil, fmt.Errorf("查询性能指标失败: %w", err)
	}

	// 构建计数器 ID 到名称的反向映射
	counterIDToName := make(map[int32]string)
	for _, counterName := range counterNames {
		if counterInfo, ok := counters[counterName]; ok && counterInfo != nil {
			counterIDToName[counterInfo.Key] = counterName
		}
	}

	// 解析查询结果，统计每个指标的数据点数量
	result := make(map[string]int)
	for _, mi := range metricInfo {
		if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
			for _, baseSeries := range entityMetric.Value {
				if intSeries, ok := baseSeries.(*types.PerfMetricIntSeries); ok {
					if counterName, ok := counterIDToName[intSeries.Id.CounterId]; ok {
						result[counterName] = len(intSeries.Value)
					}
				}
			}
		}
	}

	return result, nil
}

func main() {
	// 测试连接参数（从 .env 获取）
	server := "10.103.116.116"
	username := "administrator@vsphere.local"
	password := "Admin@123."

	fmt.Println("=== vCenter 性能指标采集测试 ===")

	// 创建客户端
	client, err := NewVCenterClient(server, username, password)
	if err != nil {
		fmt.Printf("连接失败: %v\n", err)
		os.Exit(1)
	}
	defer client.Close()

	fmt.Println("✓ 连接成功!")

	// 获取虚拟机列表
	fmt.Println("\n=== 获取虚拟机列表 ===")
	vms, err := client.GetVMs()
	if err != nil {
		fmt.Printf("获取虚拟机失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("找到 %d 台虚拟机\n", len(vms))

	// 筛选开机且连接正常的虚拟机
	var poweredOnVMs []map[string]interface{}
	for _, vm := range vms {
		powerState := fmt.Sprintf("%s", vm["powerState"])
		connectionState := fmt.Sprintf("%s", vm["connectionState"])

		// 跳过连接状态异常的虚拟机
		if connectionState != "" && connectionState != "connected" {
			fmt.Printf("  跳过 %s: 连接状态异常 (%s)\n", vm["name"], connectionState)
			continue
		}

		// 只采集开机状态的虚拟机
		if powerState != "poweredOn" {
			continue
		}

		poweredOnVMs = append(poweredOnVMs, vm)
	}

	fmt.Printf("\n筛选出 %d 台开机且连接正常的虚拟机\n", len(poweredOnVMs))

	if len(poweredOnVMs) == 0 {
		fmt.Println("没有符合条件的虚拟机，测试结束")
		return
	}

	// 测试获取性能指标（只测试前 3 台）
	fmt.Println("\n=== 测试性能指标采集 ===")
	endTime := time.Now()
	startTime := endTime.Add(-1 * time.Hour)

	testCount := 3
	if len(poweredOnVMs) < testCount {
		testCount = len(poweredOnVMs)
	}

	successCount := 0
	failCount := 0

	for i, vm := range poweredOnVMs[:testCount] {
		vmName := vm["name"].(string)
		datacenter := vm["datacenter"].(string)
		vmUUID := vm["uuid"].(string)
		cpuCount := vm["cpuCount"].(int32)

		fmt.Printf("\n[%d/%d] 测试虚拟机: %s\n", i+1, testCount, vmName)
		fmt.Printf("  数据中心: %s\n", datacenter)
		fmt.Printf("  UUID: %s\n", vmUUID)
		fmt.Printf("  CPU: %d vCPU\n", cpuCount)

		metrics, err := client.GetVMMetrics(datacenter, vmName, vmUUID, startTime, endTime, cpuCount)
		if err != nil {
			fmt.Printf("  ❌ 采集失败: %v\n", err)
			failCount++
			continue
		}

		fmt.Printf("  ✓ 采集成功:\n")
		for counterName, count := range metrics {
			fmt.Printf("    - %s: %d 个数据点\n", counterName, count)
		}
		successCount++
	}

	// 输出总结
	fmt.Println("\n=== 测试总结 ===")
	fmt.Printf("测试总数: %d\n", testCount)
	fmt.Printf("成功: %d\n", successCount)
	fmt.Printf("失败: %d\n", failCount)

	if failCount > 0 {
		fmt.Printf("\n注意: 有 %d 台虚拟机采集失败，可能的原因:\n", failCount)
		fmt.Println("  1. 虚拟机刚开机，还没有足够的历史数据")
		fmt.Println("  2. vCenter 性能数据库中没有该虚拟机的记录")
		fmt.Println("  3. 虚拟机所在的宿主机不可访问")
	}

	fmt.Println("\n=== 测试完成 ===")
}
