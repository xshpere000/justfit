// Package connector 提供云平台连接器实现
package connector

import (
	"context"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/find"
	"github.com/vmware/govmomi/object"
	"github.com/vmware/govmomi/performance"
	"github.com/vmware/govmomi/session"
	"github.com/vmware/govmomi/vim25/mo"
	"github.com/vmware/govmomi/vim25/types"
)

// PlatformType 平台类型
type PlatformType string

const (
	PlatformVCenter PlatformType = "vcenter"
	PlatformH3CUIS  PlatformType = "h3c-uis"
)

// ConnectionConfig 连接配置
type ConnectionConfig struct {
	ID       uint
	Name     string
	Platform PlatformType
	Host     string
	Port     int
	Username string
	Password string
	Insecure bool // 跳过 SSL 证书验证
}

// VCenterClient vCenter 客户端封装
type VCenterClient struct {
	config *ConnectionConfig
	client *govmomi.Client
	ctx    context.Context
}

// NewVCenterClient 创建 vCenter 客户端
func NewVCenterClient(config *ConnectionConfig) (*VCenterClient, error) {
	ctx := context.Background()

	// 构建 URL
	scheme := "https"
	if config.Insecure {
		scheme = "https"
	}

	u, err := url.Parse(fmt.Sprintf("%s://%s:%d/sdk", scheme, config.Host, config.Port))
	if err != nil {
		return nil, fmt.Errorf("解析 URL 失败: %w", err)
	}

	// 连接 vCenter
	client, err := govmomi.NewClient(ctx, u, config.Insecure)
	if err != nil {
		return nil, fmt.Errorf("连接 vCenter 失败: %w", err)
	}

	// 使用 session.Manager 登录
	sm := session.NewManager(client.Client)
	userInfo := url.UserPassword(config.Username, config.Password)
	err = sm.Login(ctx, userInfo)
	if err != nil {
		client.Logout(ctx)
		return nil, fmt.Errorf("登录失败: %w", err)
	}

	return &VCenterClient{
		config: config,
		client: client,
		ctx:    ctx,
	}, nil
}

// Close 关闭连接
func (vc *VCenterClient) Close() error {
	if vc.client != nil {
		return vc.client.Logout(vc.ctx)
	}
	return nil
}

// TestConnection 测试连接是否正常
func (vc *VCenterClient) TestConnection() error {
	// 尝试获取会话信息
	sm := session.NewManager(vc.client.Client)
	_, err := sm.UserSession(vc.ctx)
	return err
}

// ClusterInfo 集群信息
type ClusterInfo struct {
	Name        string
	Datacenter  string
	TotalCpu    int64 // MHz
	TotalMemory int64 // Bytes
	NumHosts    int32
	NumVMs      int
	Status      types.ManagedEntityStatus
}

// HostInfo 主机信息
type HostInfo struct {
	Name          string
	Datacenter    string
	IPAddress     string
	CpuCores      int32
	CpuMhz        int32
	Memory        int64 // Bytes
	NumVMs        int
	Connection    types.HostSystemConnectionState
	PowerState    types.HostSystemPowerState
	OverallStatus types.ManagedEntityStatus
}

// VMInfo 虚拟机信息
type VMInfo struct {
	Name          string
	Datacenter    string
	CpuCount      int32
	MemoryMB      int32
	PowerState    types.VirtualMachinePowerState
	IPAddress     string
	GuestOS       string
	HostName      string
	OverallStatus types.ManagedEntityStatus
	UUID          string
}

// GetClusters 获取所有集群信息
func (vc *VCenterClient) GetClusters() ([]ClusterInfo, error) {
	finder := find.NewFinder(vc.client.Client, true)

	// 获取数据中心
	datacenters, err := finder.DatacenterList(vc.ctx, "*")
	if err != nil {
		return nil, fmt.Errorf("获取数据中心列表失败: %w", err)
	}

	var clusters []ClusterInfo

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

			clusters = append(clusters, ClusterInfo{
				Name:        clusterMo.Name,
				Datacenter:  dc.Name(),
				TotalCpu:    int64(s.TotalCpu),
				TotalMemory: s.TotalMemory,
				NumHosts:    s.NumHosts,
				NumVMs:      numVMs,
				Status:      s.OverallStatus,
			})
		}
	}

	return clusters, nil
}

// GetHosts 获取所有主机信息
func (vc *VCenterClient) GetHosts() ([]HostInfo, error) {
	finder := find.NewFinder(vc.client.Client, true)

	datacenters, err := finder.DatacenterList(vc.ctx, "*")
	if err != nil {
		return nil, fmt.Errorf("获取数据中心列表失败: %w", err)
	}

	var hosts []HostInfo

	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		hostList, err := finder.HostSystemList(vc.ctx, "*")
		if err != nil {
			continue
		}

		for _, host := range hostList {
			var hostMo mo.HostSystem
			err = host.Properties(vc.ctx, host.Reference(), []string{"name", "summary", "vm"}, &hostMo)
			if err != nil {
				continue
			}

			hosts = append(hosts, HostInfo{
				Name:          hostMo.Name,
				Datacenter:    dc.Name(),
				IPAddress:     hostMo.Summary.ManagementServerIp,
				CpuCores:      int32(hostMo.Summary.Hardware.NumCpuCores),
				CpuMhz:        hostMo.Summary.Hardware.CpuMhz,
				Memory:        hostMo.Summary.Hardware.MemorySize,
				NumVMs:        len(hostMo.Vm),
				Connection:    hostMo.Summary.Runtime.ConnectionState,
				PowerState:    hostMo.Summary.Runtime.PowerState,
				OverallStatus: hostMo.Summary.OverallStatus,
			})
		}
	}

	return hosts, nil
}

// GetVMs 获取所有虚拟机信息
func (vc *VCenterClient) GetVMs() ([]VMInfo, error) {
	finder := find.NewFinder(vc.client.Client, true)

	datacenters, err := finder.DatacenterList(vc.ctx, "*")
	if err != nil {
		return nil, fmt.Errorf("获取数据中心列表失败: %w", err)
	}

	var vms []VMInfo

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

			vms = append(vms, VMInfo{
				Name:          vmMo.Name,
				Datacenter:    dc.Name(),
				CpuCount:      vmMo.Summary.Config.NumCpu,
				MemoryMB:      vmMo.Summary.Config.MemorySizeMB,
				PowerState:    vmMo.Summary.Runtime.PowerState,
				IPAddress:     vmMo.Summary.Guest.IpAddress,
				GuestOS:       vmMo.Summary.Guest.GuestFullName,
				HostName:      hostName,
				OverallStatus: vmMo.Summary.OverallStatus,
				UUID:          vmMo.Summary.Config.Uuid,
			})
		}
	}

	return vms, nil
}

// MetricSample 性能指标采样点
type MetricSample struct {
	Timestamp time.Time
	Value     float64
}

// VMMetrics 虚拟机性能指标
type VMMetrics struct {
	VMName    string
	CPU       []MetricSample
	Memory    []MetricSample
	DiskRead  []MetricSample
	DiskWrite []MetricSample
	NetRx     []MetricSample
	NetTx     []MetricSample
}

// GetVMMetrics 获取虚拟机性能指标
func (vc *VCenterClient) GetVMMetrics(datacenter, vmName, vmUUID string, startTime time.Time, endTime time.Time, cpuCount int32) (*VMMetrics, error) {
	finder := find.NewFinder(vc.client.Client, true)

	// 设置数据中心
	dc, err := finder.Datacenter(vc.ctx, datacenter)
	if err != nil {
		return nil, fmt.Errorf("查找数据中心失败: %w", err)
	}
	finder.SetDatacenter(dc)

	vm, resolvedVMName, err := vc.findVMByUUIDOrName(finder, vmName, vmUUID)
	if err != nil {
		return nil, err
	}

	perfManager := performance.NewManager(vc.client.Client)

	// 定义要采集的指标
	// cpu.usage.average (Basis Points 0.01%) -> Cores
	// mem.consumed.average (KB) -> MB
	// disk/net (KBps) -> KBps
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

	result := &VMMetrics{
		VMName: resolvedVMName,
	}

	// 解析查询结果
	for _, mi := range metricInfo {
		if entityMetric, ok := mi.(*types.PerfEntityMetric); ok {
			// 获取采样时间信息
			sampleTimes := make([]time.Time, len(entityMetric.SampleInfo))
			for i, si := range entityMetric.SampleInfo {
				sampleTimes[i] = si.Timestamp
			}

			for _, baseSeries := range entityMetric.Value {
				// 尝试转换为整数序列
				if intSeries, ok := baseSeries.(*types.PerfMetricIntSeries); ok {
					counterName := counterIDToName[intSeries.Id.CounterId]
					if counterName == "" {
						continue
					}

					// 构建采样点
					samples := make([]MetricSample, len(intSeries.Value))
					for i, v := range intSeries.Value {
						var val float64

						// 根据指标名称处理单位转换
						switch counterName {
						case "cpu.usage.average":
							// 原始单位：Basis Points (1/100 %)
							// 转换目标：Cores
							// 公式：(v / 10000) * cpuCount
							if cpuCount > 0 {
								val = (float64(v) / 10000.0) * float64(cpuCount)
							} else {
								// 如果没有 cpuCount，回退到百分比 / 100 (0-1) ? 或保持百分比 0-100 ?
								// 保持 0-100%
								val = float64(v) / 100.0
							}
						case "mem.consumed.average":
							// 原始单位：KB
							// 转换目标：MB
							val = float64(v) / 1024.0
						default:
							// disk/net 原始单位：KBps
							// 保持原样
							val = float64(v)
						}

						samples[i] = MetricSample{
							Timestamp: sampleTimes[i],
							Value:     val,
						}
					}

					// 根据指标名称归类
					switch counterName {
					case "cpu.usage.average":
						result.CPU = samples
					case "mem.consumed.average":
						result.Memory = samples
					case "disk.read.average":
						result.DiskRead = samples
					case "disk.write.average":
						result.DiskWrite = samples
					case "net.bytesRx.average":
						result.NetRx = samples
					case "net.bytesTx.average":
						result.NetTx = samples
					}
				}
			}
		}
	}

	return result, nil
}

func (vc *VCenterClient) findVMByUUIDOrName(finder *find.Finder, vmName, vmUUID string) (*object.VirtualMachine, string, error) {
	vms, err := finder.VirtualMachineList(vc.ctx, "*")
	if err != nil {
		return nil, "", fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	wantUUID := strings.ToLower(strings.TrimSpace(vmUUID))
	if wantUUID != "" {
		for _, vm := range vms {
			var vmMo mo.VirtualMachine
			if propErr := vm.Properties(vc.ctx, vm.Reference(), []string{"name", "summary.config.uuid"}, &vmMo); propErr != nil {
				continue
			}
			if strings.EqualFold(strings.TrimSpace(vmMo.Summary.Config.Uuid), wantUUID) {
				return vm, vmMo.Name, nil
			}
		}
	}

	wantName := strings.TrimSpace(vmName)
	for _, vm := range vms {
		var vmMo mo.VirtualMachine
		if propErr := vm.Properties(vc.ctx, vm.Reference(), []string{"name"}, &vmMo); propErr != nil {
			continue
		}
		if strings.TrimSpace(vmMo.Name) == wantName {
			return vm, vmMo.Name, nil
		}
	}

	if wantUUID != "" {
		return nil, "", fmt.Errorf("查找虚拟机失败: 未找到 uuid=%s 且名称=%s 的虚拟机", vmUUID, vmName)
	}

	return nil, "", fmt.Errorf("查找虚拟机失败: 未找到名称=%s 的虚拟机", vmName)
}
