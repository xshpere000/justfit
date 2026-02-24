// Package response 定义资源相关响应 DTO
package response

import "time"

// VMResponse 虚拟机响应
type VMResponse struct {
	ID            uint      `json:"id"`
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	UUID          string    `json:"uuid"`
	CPUCount      int32     `json:"cpu_count"`
	MemoryMB      int32     `json:"memory_mb"`
	MemoryGB      float64   `json:"memory_gb"`
	PowerState    string    `json:"power_state"`
	IPAddress     string    `json:"ip_address,omitempty"`
	GuestOS       string    `json:"guest_os,omitempty"`
	HostName      string    `json:"host_name,omitempty"`
	OverallStatus string    `json:"overall_status,omitempty"`
	CollectedAt   time.Time `json:"collected_at"`
}

// HostResponse 主机响应
type HostResponse struct {
	ID            uint      `json:"id"`
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	IPAddress     string    `json:"ip_address"`
	CPUCores      int32     `json:"cpu_cores"`
	CPUMHz        int32     `json:"cpu_mhz"`
	MemoryMB      int64     `json:"memory_mb"`
	MemoryGB      float64   `json:"memory_gb"`
	NumVMs        int       `json:"num_vms"`
	PowerState    string    `json:"power_state"`
	OverallStatus string    `json:"overall_status"`
	CollectedAt   time.Time `json:"collected_at"`
}

// ClusterResponse 集群响应
type ClusterResponse struct {
	ID            uint      `json:"id"`
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	TotalCPU      int64     `json:"total_cpu"`
	TotalMemory   int64     `json:"total_memory"`
	TotalMemoryGB float64   `json:"total_memory_gb"`
	NumHosts      int32     `json:"num_hosts"`
	NumVMs        int       `json:"num_vms"`
	Status        string    `json:"status"`
	CollectedAt   time.Time `json:"collected_at"`
}

// MetricPoint 指标数据点
type MetricPoint struct {
	Timestamp int64   `json:"timestamp"`
	Value     float64 `json:"value"`
}

// MetricsResponse 指标响应
type MetricsResponse struct {
	VMID       uint          `json:"vm_id"`
	VMName     string        `json:"vm_name"`
	MetricType string        `json:"metric_type"` // cpu, memory, disk_read, disk_write, net_rx, net_tx
	StartTime  string        `json:"start_time"`
	EndTime    string        `json:"end_time"`
	DataPoints []MetricPoint `json:"data_points"`
}
