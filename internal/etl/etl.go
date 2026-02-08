// Package etl 提供数据抽取、转换、加载功能
package etl

import (
	"fmt"
	"strings"
	"time"

	"justfit/internal/connector"
	"justfit/internal/storage"
)

// Processor ETL 处理器
type Processor struct {
	repos *storage.Repositories
}

// NewProcessor 创建 ETL 处理器
func NewProcessor(repos *storage.Repositories) *Processor {
	return &Processor{repos: repos}
}

// ProcessCluster 处理集群数据
func (p *Processor) ProcessCluster(connectionID uint, cluster connector.ClusterInfo) error {
	now := time.Now()

	dbCluster := &storage.Cluster{
		ConnectionID:  connectionID,
		ClusterKey:    fmt.Sprintf("%s:%s", cluster.Datacenter, cluster.Name),
		Name:          cluster.Name,
		Datacenter:    cluster.Datacenter,
		TotalCpu:      cluster.TotalCpu,
		TotalMemory:   cluster.TotalMemory,
		NumHosts:      cluster.NumHosts,
		NumVMs:        cluster.NumVMs,
		Status:        string(cluster.Status),
		CollectedAt:   now,
	}

	return p.repos.Cluster.UpdateOrCreate(dbCluster)
}

// ProcessHost 处理主机数据
func (p *Processor) ProcessHost(connectionID uint, host connector.HostInfo) error {
	now := time.Now()

	dbHost := &storage.Host{
		ConnectionID:   connectionID,
		HostKey:        fmt.Sprintf("%s:%s", host.Datacenter, host.Name),
		Name:           host.Name,
		Datacenter:     host.Datacenter,
		IPAddress:      host.IPAddress,
		CpuCores:       host.CpuCores,
		CpuMhz:         host.CpuMhz,
		Memory:         host.Memory,
		NumVMs:         host.NumVMs,
		ConnectionState: string(host.Connection),
		PowerState:     string(host.PowerState),
		OverallStatus:  string(host.OverallStatus),
		CollectedAt:    now,
	}

	return p.repos.Host.UpdateOrCreate(dbHost)
}

// ProcessVM 处理虚拟机数据
func (p *Processor) ProcessVM(connectionID uint, vm connector.VMInfo) error {
	now := time.Now()

	dbVM := &storage.VM{
		ConnectionID:   connectionID,
		VMKey:          fmt.Sprintf("%s:%s", vm.Datacenter, vm.Name),
		UUID:           vm.UUID,
		Name:           vm.Name,
		Datacenter:     vm.Datacenter,
		CpuCount:       vm.CpuCount,
		MemoryMB:       vm.MemoryMB,
		PowerState:     string(vm.PowerState),
		IPAddress:      vm.IPAddress,
		GuestOS:        vm.GuestOS,
		HostName:       vm.HostName,
		OverallStatus:  string(vm.OverallStatus),
		CollectedAt:    now,
	}

	return p.repos.VM.UpdateOrCreate(dbVM)
}

// ProcessVMMetrics 处理虚拟机性能指标
func (p *Processor) ProcessVMMetrics(vmKey string, metrics *connector.VMMetrics) error {
	// 查找虚拟机
	vm, err := p.repos.VM.GetByKey(vmKey)
	if err != nil {
		return fmt.Errorf("查找虚拟机失败: %w", err)
	}

	var allMetrics []storage.Metric

	// 转换 CPU 指标
	for _, sample := range metrics.CPU {
		allMetrics = append(allMetrics, storage.Metric{
			VMID:       vm.ID,
			MetricType: "cpu",
			Timestamp:  sample.Timestamp,
			Value:      sample.Value,
		})
	}

	// 转换内存指标
	for _, sample := range metrics.Memory {
		allMetrics = append(allMetrics, storage.Metric{
			VMID:       vm.ID,
			MetricType: "memory",
			Timestamp:  sample.Timestamp,
			Value:      sample.Value,
		})
	}

	// 转换磁盘读指标
	for _, sample := range metrics.DiskRead {
		allMetrics = append(allMetrics, storage.Metric{
			VMID:       vm.ID,
			MetricType: "disk_read",
			Timestamp:  sample.Timestamp,
			Value:      sample.Value,
		})
	}

	// 转换磁盘写指标
	for _, sample := range metrics.DiskWrite {
		allMetrics = append(allMetrics, storage.Metric{
			VMID:       vm.ID,
			MetricType: "disk_write",
			Timestamp:  sample.Timestamp,
			Value:      sample.Value,
		})
	}

	// 转换网络接收指标
	for _, sample := range metrics.NetRx {
		allMetrics = append(allMetrics, storage.Metric{
			VMID:       vm.ID,
			MetricType: "net_rx",
			Timestamp:  sample.Timestamp,
			Value:      sample.Value,
		})
	}

	// 转换网络发送指标
	for _, sample := range metrics.NetTx {
		allMetrics = append(allMetrics, storage.Metric{
			VMID:       vm.ID,
			MetricType: "net_tx",
			Timestamp:  sample.Timestamp,
			Value:      sample.Value,
		})
	}

	return p.repos.Metric.BatchCreate(allMetrics)
}

// CleanupOldData 清理旧数据
func (p *Processor) CleanupOldData(retentionDays int) error {
	cutoffDate := time.Now().AddDate(0, 0, -retentionDays)
	return p.repos.Metric.DeleteByTimeRange(cutoffDate)
}

// CleanConnectionData 清理指定连接的所有数据
func (p *Processor) CleanConnectionData(connectionID uint) error {
	// 删除需要按顺序进行，考虑外键约束
	if err := p.repos.Metric.DeleteByVMID(0); err != nil {
		// 这里需要先获取所有 VM ID
	}

	if err := p.repos.VM.DeleteByConnectionID(connectionID); err != nil {
		return fmt.Errorf("删除虚拟机数据失败: %w", err)
	}

	if err := p.repos.Host.DeleteByConnectionID(connectionID); err != nil {
		return fmt.Errorf("删除主机数据失败: %w", err)
	}

	if err := p.repos.Cluster.DeleteByConnectionID(connectionID); err != nil {
		return fmt.Errorf("删除集群数据失败: %w", err)
	}

	return nil
}

// TransformUnit 单位转换工具
type TransformUnit struct{}

// MHzToGHz MHz 转 GHz
func (t *TransformUnit) MHzToGHz(mhz int64) float64 {
	return float64(mhz) / 1000
}

// BytesToGB Bytes 转 GB
func (t *TransformUnit) BytesToGB(bytes int64) float64 {
	return float64(bytes) / (1024 * 1024 * 1024)
}

// MBToGB MB 转 GB
func (t *TransformUnit) MBToGB(mb int32) float64 {
	return float64(mb) / 1024
}

// NormalizePath 规范化路径
func (t *TransformUnit) NormalizePath(path string) string {
	return strings.TrimPrefix(strings.TrimSpace(path), "/")
}

// NormalizeName 规范化名称
func (t *TransformUnit) NormalizeName(name string) string {
	return strings.TrimSpace(name)
}

// DataValidator 数据验证器
type DataValidator struct{}

// ValidateHostIP 验证主机 IP
func (v *DataValidator) ValidateHostIP(ip string) bool {
	if ip == "" || ip == "0.0.0.0" {
		return false
	}
	// 简单验证，实际可以使用更复杂的 IP 验证
	parts := strings.Split(ip, ".")
	return len(parts) == 4
}

// ValidateVMName 验证虚拟机名称
func (v *DataValidator) ValidateVMName(name string) bool {
	return strings.TrimSpace(name) != ""
}

// ValidateMetricValue 验证指标值
func (v *DataValidator) ValidateMetricValue(value float64) bool {
	return value >= 0
}

// SanitizeString 清理字符串
func (v *DataValidator) SanitizeString(s string) string {
	// 移除控制字符
	result := strings.Map(func(r rune) rune {
		if r < 32 && r != '\n' && r != '\r' && r != '\t' {
			return -1
		}
		return r
	}, s)
	return strings.TrimSpace(result)
}
