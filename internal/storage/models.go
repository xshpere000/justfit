// Package storage 提供数据存储层
package storage

import (
	"time"

	"gorm.io/gorm"
)

// Connection 连接配置
type Connection struct {
	gorm.Model
	Name     string     `gorm:"size:100;not null" json:"name"`
	Platform string     `gorm:"size:20;not null" json:"platform"` // vcenter, h3c-uis
	Host     string     `gorm:"size:255;not null" json:"host"`
	Port     int        `gorm:"not null" json:"port"`
	Username string     `gorm:"size:100;not null" json:"username"`
	Password string     `gorm:"size:500;not null" json:"-"` // 加密存储，不导出 JSON
	Insecure bool       `gorm:"default:true" json:"insecure"`
	Status   string     `gorm:"size:20;default:disconnected" json:"status"` // connected, disconnected, error
	LastSync *time.Time `json:"last_sync"`
}

// Cluster 集群信息
type Cluster struct {
	gorm.Model
	ConnectionID uint        `gorm:"index:idx_cluster_connection" json:"connection_id"`
	Connection   *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	ClusterKey   string      `gorm:"size:100;index" json:"cluster_key"` // 唯一标识
	Name         string      `gorm:"size:200;not null" json:"name"`
	Datacenter   string      `gorm:"size:100" json:"datacenter"`
	TotalCpu     int64       `json:"total_cpu"`    // MHz
	TotalMemory  int64       `json:"total_memory"` // Bytes
	NumHosts     int32       `json:"num_hosts"`
	NumVMs       int         `json:"num_vms"`
	Status       string      `gorm:"size:50" json:"status"`
	CollectedAt  time.Time   `json:"collected_at"`
}

// Host 主机信息
type Host struct {
	gorm.Model
	ConnectionID    uint        `gorm:"index:idx_host_connection" json:"connection_id"`
	Connection      *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	HostKey         string      `gorm:"size:100;index" json:"host_key"` // 唯一标识
	Name            string      `gorm:"size:200;not null" json:"name"`
	Datacenter      string      `gorm:"size:100" json:"datacenter"`
	IPAddress       string      `gorm:"size:50" json:"ip_address"`
	CpuCores        int32       `json:"cpu_cores"`
	CpuMhz          int32       `json:"cpu_mhz"`
	Memory          int64       `json:"memory"` // Bytes
	NumVMs          int         `json:"num_vms"`
	ConnectionState string      `gorm:"size:50" json:"connection_state"`
	PowerState      string      `gorm:"size:50" json:"power_state"`
	OverallStatus   string      `gorm:"size:50" json:"overall_status"`
	CollectedAt     time.Time   `json:"collected_at"`
}

// VM 虚拟机信息
type VM struct {
	gorm.Model
	ConnectionID    uint        `gorm:"index:idx_vm_connection" json:"connection_id"`
	Connection      *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	VMKey           string      `gorm:"size:100;index" json:"vm_key"` // 唯一标识
	UUID            string      `gorm:"size:100;index" json:"uuid"`
	Name            string      `gorm:"size:200;not null;index" json:"name"`
	Datacenter      string      `gorm:"size:100" json:"datacenter"`
	CpuCount        int32       `json:"cpu_count"`
	MemoryMB        int32       `json:"memory_mb"`
	PowerState      string      `gorm:"size:50;index" json:"power_state"`
	ConnectionState string      `gorm:"size:50" json:"connection_state"` // 连接状态: connected, disconnected, orphaned, notResponding
	IPAddress       string      `gorm:"size:50" json:"ip_address"`
	GuestOS         string      `gorm:"size:100" json:"guest_os"`
	HostName        string      `gorm:"size:200" json:"host_name"`
	OverallStatus   string      `gorm:"size:50" json:"overall_status"`
	CollectedAt     time.Time   `json:"collected_at"`
}

// Metric 性能指标
type Metric struct {
	gorm.Model
	VMID       uint      `gorm:"index:idx_metric_vm" json:"vm_id"`
	VM         *VM       `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	MetricType string    `gorm:"size:50;index:idx_metric_type" json:"metric_type"` // cpu, memory, disk_read, disk_write, net_rx, net_tx
	Timestamp  time.Time `gorm:"index:idx_metric_timestamp" json:"timestamp"`
	Value      float64   `json:"value"`
}

// Task 任务
type Task struct {
	gorm.Model
	Type        string     `gorm:"size:50;not null;index" json:"type"`   // collect, analyze, report
	Status      string     `gorm:"size:20;not null;index" json:"status"` // pending, running, completed, failed
	Progress    int        `gorm:"default:0" json:"progress"`
	Message     string     `gorm:"size:500" json:"message"`
	Result      string     `gorm:"type:text" json:"result"` // JSON 格式的结果
	StartedAt   *time.Time `json:"started_at"`
	CompletedAt *time.Time `json:"completed_at"`
	// 任务关联信息
	ConnectionID   uint   `gorm:"index" json:"connection_id"`      // 关联的连接ID
	ConnectionName string `gorm:"size:200" json:"connection_name"` // 连接名称
	Platform       string `gorm:"size:20" json:"platform"`         // 平台类型: vcenter, h3c-uis
	// VM选择信息
	TotalVMs    int32  `gorm:"default:0" json:"total_vms"`    // 虚拟机总数
	SelectedVMs string `gorm:"type:text" json:"selected_vms"` // 选中的VM列表(JSON数组)
}

// TaskLog 任务日志
type TaskLog struct {
	gorm.Model
	TaskID    uint      `gorm:"index:idx_task_log_task" json:"task_id"`
	Task      *Task     `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	Level     string    `gorm:"size:20" json:"level"` // info, warning, error
	Message   string    `gorm:"type:text" json:"message"`
	CreatedAt time.Time `json:"created_at"`
}

// TaskVMSnapshot 任务虚拟机快照
type TaskVMSnapshot struct {
	gorm.Model
	TaskID        uint      `gorm:"index:idx_task_vm_snapshot_task" json:"task_id"`
	ConnectionID  uint      `gorm:"index:idx_task_vm_snapshot_conn" json:"connection_id"`
	VMKey         string    `gorm:"size:120;index:idx_task_vm_snapshot_vmkey" json:"vm_key"`
	UUID          string    `gorm:"size:100;index" json:"uuid"`
	Name          string    `gorm:"size:200;index" json:"name"`
	Datacenter    string    `gorm:"size:100;index" json:"datacenter"`
	CpuCount      int32     `json:"cpu_count"`
	MemoryMB      int32     `json:"memory_mb"`
	PowerState    string    `gorm:"size:50" json:"power_state"`
	IPAddress     string    `gorm:"size:50" json:"ip_address"`
	GuestOS       string    `gorm:"size:100" json:"guest_os"`
	HostName      string    `gorm:"size:200" json:"host_name"`
	OverallStatus string    `gorm:"size:50" json:"overall_status"`
	CollectedAt   time.Time `json:"collected_at"`
}

// TaskAnalysisResult 任务分析结果
type TaskAnalysisResult struct {
	gorm.Model
	TaskID       uint   `gorm:"index:idx_task_analysis_result_task" json:"task_id"`
	AnalysisType string `gorm:"size:50;index:idx_task_analysis_result_type" json:"analysis_type"`
	Data         string `gorm:"type:text" json:"data"`
}

// Report 报告
type Report struct {
	gorm.Model
	Type         string    `gorm:"size:50;index" json:"type"` // comprehensive, zombie_vm, right_size, tidal, health
	Name         string    `gorm:"size:200;not null" json:"name"`
	ConnectionID uint      `gorm:"index" json:"connection_id"`
	Status       string    `gorm:"size:20;default:pending" json:"status"` // pending, generating, completed, failed
	Format       string    `gorm:"size:20" json:"format"`                 // json, html, pdf
	FilePath     string    `gorm:"size:500" json:"file_path"`
	FileSize     int64     `json:"file_size"`
	CreatedAt    time.Time `json:"created_at"`
}

// AnalysisResult 分析结果
type AnalysisResult struct {
	gorm.Model
	ReportID       uint    `gorm:"index:idx_analysis_report" json:"report_id"`
	Report         *Report `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	AnalysisType   string  `gorm:"size:50;index" json:"analysis_type"` // zombie_vm, right_size, tidal, health_score
	TargetType     string  `gorm:"size:50" json:"target_type"`         // cluster, host, vm
	TargetKey      string  `gorm:"size:100;index" json:"target_key"`
	TargetName     string  `gorm:"size:200" json:"target_name"`
	Data           string  `gorm:"type:text" json:"data"` // JSON 格式的详细数据
	Recommendation string  `gorm:"type:text" json:"recommendation"`
	SavedAmount    string  `gorm:"size:100" json:"saved_amount"` // 节省的资源估算
}

// Alert 告警
type Alert struct {
	gorm.Model
	TargetType     string     `gorm:"size:50;index" json:"target_type"` // cluster, host, vm
	TargetKey      string     `gorm:"size:100;index" json:"target_key"`
	TargetName     string     `gorm:"size:200" json:"target_name"`
	AlertType      string     `gorm:"size:50;index" json:"alert_type"` // zombie_vm, overprovisioned, underprovisioned, health_risk
	Severity       string     `gorm:"size:20" json:"severity"`         // info, warning, critical
	Title          string     `gorm:"size:200" json:"title"`
	Message        string     `gorm:"type:text" json:"message"`
	Data           string     `gorm:"type:text" json:"data"` // JSON 格式的详细数据
	Acknowledged   bool       `gorm:"default:false" json:"acknowledged"`
	AcknowledgedAt *time.Time `json:"acknowledged_at"`
	CreatedAt      time.Time  `json:"created_at"`
}

// Settings 系统配置
type Settings struct {
	gorm.Model
	Key   string `gorm:"size:100;uniqueIndex;not null" json:"key"`
	Value string `gorm:"type:text" json:"value"`
	Type  string `gorm:"size:20;default:string" json:"type"` // string, int, float, bool, json
}
