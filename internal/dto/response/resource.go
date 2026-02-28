// Package response 定义资源相关响应 DTO
package response

import "time"

// VMResponse 虚拟机响应
type VMResponse struct {
	ID            uint      `json:"id"`
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	UUID          string    `json:"uuid"`
	CPUCount      int32     `json:"cpuCount"`
	MemoryMB      int32     `json:"memoryMb"`
	MemoryGB      float64   `json:"memoryGb"`
	PowerState    string    `json:"powerState"`
	IPAddress     string    `json:"ipAddress,omitempty"`
	GuestOS       string    `json:"guestOs,omitempty"`
	HostName      string    `json:"hostName,omitempty"`
	HostIP        string    `json:"hostIp,omitempty"`
	OverallStatus string    `json:"overallStatus,omitempty"`
	CollectedAt   time.Time `json:"collectedAt"`
}

// HostResponse 主机响应
type HostResponse struct {
	ID            uint      `json:"id"`
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	IPAddress     string    `json:"ipAddress"`
	CPUCores      int32     `json:"cpuCores"`
	CPUMHz        int32     `json:"cpuMhz"`
	MemoryMB      int64     `json:"memoryMb"`
	MemoryGB      float64   `json:"memoryGb"`
	NumVMs        int       `json:"numVMs"`
	PowerState    string    `json:"powerState"`
	OverallStatus string    `json:"overallStatus"`
	CollectedAt   time.Time `json:"collectedAt"`
}

// ClusterResponse 集群响应
type ClusterResponse struct {
	ID            uint      `json:"id"`
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	TotalCPU      int64     `json:"totalCpu"`
	TotalMemory   int64     `json:"totalMemory"`
	TotalMemoryGB float64   `json:"totalMemoryGb"`
	NumHosts      int32     `json:"numHosts"`
	NumVMs        int       `json:"numVMs"`
	Status        string    `json:"status"`
	CollectedAt   time.Time `json:"collectedAt"`
}

// MetricPoint 指标数据点
type MetricPoint struct {
	Timestamp int64   `json:"timestamp"`
	Value     float64 `json:"value"`
}

// MetricsResponse 指标响应
type MetricsResponse struct {
	VMID       uint          `json:"vmId"`
	VMName     string        `json:"vmName"`
	MetricType string        `json:"metricType"` // cpu, memory, disk_read, disk_write, net_rx, net_tx
	StartTime  string        `json:"startTime"`
	EndTime    string        `json:"endTime"`
	DataPoints []MetricPoint `json:"dataPoints"`
}
