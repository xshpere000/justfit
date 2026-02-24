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

	// 跳过 SSL 证书验证（仅用于测试环境）
	u.Scheme = "https"

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

// GetClusters 获取所有集群信息
func (vc *VCenterClient) GetClusters() ([]map[string]interface{}, error) {
	finder := find.NewFinder(vc.client.Client, true)

	// 获取数据中心
	datacenters, err := finder.DatacenterList(vc.ctx, "*")
	if err != nil {
		return nil, fmt.Errorf("获取数据中心列表失败: %w", err)
	}

	var clusters []map[string]interface{}

	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		clusterList, err := finder.ClusterComputeResourceList(vc.ctx, "*")
		if err != nil {
			continue
		}

		for _, cluster := range clusterList {
			var clusterMo mo.ClusterComputeResource
			err = cluster.Properties(vc.ctx, cluster.Reference(), []string{"name", "summary"}, &clusterMo)
			if err != nil {
				continue
			}

			s := clusterMo.Summary.GetComputeResourceSummary()
			if s == nil {
				continue
			}

			// 获取 VM 数量
			numVMs := 0
			for _, hostRef := range clusterMo.Host {
				var hostMo mo.HostSystem
				_ = vc.client.RetrieveOne(vc.ctx, hostRef, []string{"vm"}, &hostMo)
				numVMs += len(hostMo.Vm)
			}

			clusterInfo := map[string]interface{}{
				"name":        clusterMo.Name,
				"datacenter":  dc.Name(),
				"totalCpu":    s.TotalCpu,
				"totalMemory": s.TotalMemory,
				"numHosts":    s.NumHosts,
				"numVMs":      numVMs,
				"status":      s.OverallStatus,
			}

			clusters = append(clusters, clusterInfo)
		}
	}

	return clusters, nil
}

// GetHosts 获取所有主机信息
func (vc *VCenterClient) GetHosts() ([]map[string]interface{}, error) {
	finder := find.NewFinder(vc.client.Client, true)

	datacenters, err := finder.DatacenterList(vc.ctx, "*")
	if err != nil {
		return nil, fmt.Errorf("获取数据中心列表失败: %w", err)
	}

	var hosts []map[string]interface{}

	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		hostList, err := finder.HostSystemList(vc.ctx, "*/*")
		if err != nil {
			continue
		}

		for _, host := range hostList {
			var hostMo mo.HostSystem
			err = host.Properties(vc.ctx, host.Reference(), []string{"name", "summary", "vm"}, &hostMo)
			if err != nil {
				continue
			}

			hostInfo := map[string]interface{}{
				"name":          hostMo.Name,
				"datacenter":    dc.Name(),
				"ipAddress":     hostMo.Summary.ManagementServerIp,
				"cpuCores":      hostMo.Summary.Hardware.NumCpuCores,
				"cpuMhz":        hostMo.Summary.Hardware.CpuMhz,
				"memory":        hostMo.Summary.Hardware.MemorySize,
				"numVMs":        len(hostMo.Vm),
				"connection":    hostMo.Summary.Runtime.ConnectionState,
				"powerState":    hostMo.Summary.Runtime.PowerState,
				"overallStatus": hostMo.Summary.OverallStatus,
			}

			hosts = append(hosts, hostInfo)
		}
	}

	return hosts, nil
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

			// 获取连接状态，用于显示异常状态
			connectionState := vmMo.Summary.Runtime.ConnectionState
			displayState := vmMo.Summary.Runtime.PowerState
			if connectionState != "" && connectionState != "connected" {
				displayState = types.VirtualMachinePowerState(connectionState)
			}

			vmInfo := map[string]interface{}{
				"name":            vmMo.Name,
				"datacenter":      dc.Name(),
				"cpuCount":        vmMo.Summary.Config.NumCpu,
				"memoryMB":        vmMo.Summary.Config.MemorySizeMB,
				"powerState":      vmMo.Summary.Runtime.PowerState,
				"connectionState": connectionState,
				"displayState":    displayState,
				"ipAddress":       vmMo.Summary.Guest.IpAddress,
				"guestOS":         vmMo.Summary.Guest.GuestFullName,
				"hostName":        hostName,
				"overallStatus":   vmMo.Summary.OverallStatus,
			}

			vms = append(vms, vmInfo)
		}
	}

	return vms, nil
}

// GetVMMetrics 获取虚拟机性能指标
func (vc *VCenterClient) GetVMMetrics(datacenter, vmName string, startTime time.Time, endTime time.Time) (map[string]int, error) {
	finder := find.NewFinder(vc.client.Client, true)

	// 设置数据中心
	dc, err := finder.Datacenter(vc.ctx, datacenter)
	if err != nil {
		return nil, fmt.Errorf("查找数据中心失败: %w", err)
	}
	finder.SetDatacenter(dc)

	vm, err := finder.VirtualMachine(vc.ctx, vmName)
	if err != nil {
		return nil, fmt.Errorf("查找虚拟机失败: %w", err)
	}

	perfManager := performance.NewManager(vc.client.Client)

	// 定义要采集的指标
	counterNames := []string{
		"cpu.usage.average",
		"mem.usage.average",
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
			}
		}
	}

	if len(spec.MetricId) == 0 {
		return nil, fmt.Errorf("没有可用的性能指标")
	}

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
		// BasePerfEntityMetricBase 需要通过类型断言获取具体实现
		if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
			for _, baseSeries := range entityMetric.Value {
				// 尝试转换为整数序列
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

	fmt.Println("=== vCenter 连接测试 ===")

	// 创建客户端
	client, err := NewVCenterClient(server, username, password)
	if err != nil {
		fmt.Printf("连接失败: %v\n", err)
		os.Exit(1)
	}
	defer client.Close()

	fmt.Println("✓ 连接成功!")

	// 测试获取集群
	fmt.Println("\n=== 集群信息 ===")
	clusters, err := client.GetClusters()
	if err != nil {
		fmt.Printf("获取集群失败: %v\n", err)
	} else {
		fmt.Printf("找到 %d 个集群:\n", len(clusters))
		for _, cluster := range clusters {
			totalCpu, _ := cluster["totalCpu"].(int64)
			totalMem, _ := cluster["totalMemory"].(int64)
			fmt.Printf("  - %s (CPU: %.2f GHz, 内存: %.2f GB, 主机: %d)\n",
				cluster["name"],
				float64(totalCpu)/1000,
				float64(totalMem)/(1024*1024*1024),
				cluster["numHosts"],
			)
		}
	}

	// 测试获取主机
	fmt.Println("\n=== 主机信息 ===")
	hosts, err := client.GetHosts()
	if err != nil {
		fmt.Printf("获取主机失败: %v\n", err)
	} else {
		fmt.Printf("找到 %d 台主机:\n", len(hosts))
		for i, host := range hosts {
			if i >= 5 {
				fmt.Printf("  ... 还有 %d 台主机\n", len(hosts)-5)
				break
			}
			memory, _ := host["memory"].(int64)
			fmt.Printf("  - %s (IP: %s, CPU核心: %d, 内存: %.2f GB, VM数量: %d)\n",
				host["name"],
				host["ipAddress"],
				host["cpuCores"],
				float64(memory)/(1024*1024*1024),
				host["numVMs"],
			)
		}
	}

	// 测试获取虚拟机
	fmt.Println("\n=== 虚拟机信息 ===")
	vms, err := client.GetVMs()
	if err != nil {
		fmt.Printf("获取虚拟机失败: %v\n", err)
	} else {
		fmt.Printf("找到 %d 台虚拟机:\n", len(vms))
		for i, vm := range vms {
			if i >= 50 {
				fmt.Printf("  ... 还有 %d 台虚拟机\n", len(vms)-50)
				break
			}
			powerState := vm["powerState"]
			connectionState := vm["connectionState"]
			displayState := vm["displayState"]

			// 显示状态，如果有异常连接状态则显示
			stateStr := fmt.Sprintf("%s", displayState)
			if connectionState != "" && connectionState != "connected" {
				stateStr = fmt.Sprintf("%s (连接: %s)", powerState, connectionState)
			}

			fmt.Printf("  - %-40s (CPU: %2d vCPU, 内存: %6d MB, 状态: %-15s, IP: %s)\n",
				vm["name"],
				vm["cpuCount"],
				vm["memoryMB"],
				stateStr,
				vm["ipAddress"],
			)
		}
	}

	// 测试获取性能指标
	if len(vms) > 0 {
		fmt.Println("\n=== 性能指标测试 ===")
		vmName := vms[0]["name"].(string)
		datacenter := vms[0]["datacenter"].(string)
		endTime := time.Now()
		startTime := endTime.Add(-1 * time.Hour)

		metrics, err := client.GetVMMetrics(datacenter, vmName, startTime, endTime)
		if err != nil {
			fmt.Printf("获取性能指标失败: %v\n", err)
		} else {
			fmt.Printf("虚拟机 %s 的性能指标:\n", vmName)
			for counterName, count := range metrics {
				fmt.Printf("  - %s: %d 个数据点\n", counterName, count)
			}
		}
	}

	fmt.Println("\n=== 测试完成 ===")
}
