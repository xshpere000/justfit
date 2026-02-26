// Package storage 提供数据存储层
package storage

import (
	"time"

	"gorm.io/gorm"
)

// ==============================================================================
// 基础资源层 - 采集的数据
// ==============================================================================

// Connection 连接配置
type Connection struct {
	gorm.Model
	Name     string     `gorm:"size:100;not null" json:"name"`
	Platform string     `gorm:"size:20;not null" json:"platform"`
	Host     string     `gorm:"size:255;not null" json:"host"`
	Port     int        `gorm:"not null" json:"port"`
	Username string     `gorm:"size:100;not null" json:"username"`
	Password string     `gorm:"size:500;not null" json:"-"` // 加密存储，不导出 JSON
	Insecure bool       `gorm:"default:true" json:"insecure"`
	Status   string     `gorm:"size:20;default:disconnected" json:"status"`
	LastSync *time.Time `json:"lastSync"`
}

// Cluster 集群信息
type Cluster struct {
	gorm.Model
	ConnectionID uint        `gorm:"index:idx_cluster_connection" json:"connectionId"`
	Connection   *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	ClusterKey   string      `gorm:"size:100;index" json:"clusterKey"`
	Name         string      `gorm:"size:200;not null" json:"name"`
	Datacenter   string      `gorm:"size:100" json:"datacenter"`
	TotalCpu     int64       `json:"totalCpu"`    // MHz
	TotalMemory  int64       `json:"totalMemory"` // Bytes
	NumHosts     int32       `json:"numHosts"`
	NumVMs       int         `json:"numVMs"`
	Status       string      `gorm:"size:50" json:"status"`
	CollectedAt  time.Time   `json:"collectedAt"`
}

// Host 主机信息
type Host struct {
	gorm.Model
	ConnectionID    uint        `gorm:"index:idx_host_connection" json:"connectionId"`
	Connection      *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	HostKey         string      `gorm:"size:100;index" json:"hostKey"`
	Name            string      `gorm:"size:200;not null" json:"name"`
	Datacenter      string      `gorm:"size:100" json:"datacenter"`
	IPAddress       string      `gorm:"size:50" json:"ipAddress"`
	CpuCores        int32       `json:"cpuCores"`
	CpuMhz          int32       `json:"cpuMhz"`
	Memory          int64       `json:"memory"` // Bytes
	NumVMs          int         `json:"numVMs"`
	ConnectionState string      `gorm:"size:50" json:"connectionState"`
	PowerState      string      `gorm:"size:50" json:"powerState"`
	OverallStatus   string      `gorm:"size:50" json:"overallStatus"`
	CollectedAt     time.Time   `json:"collectedAt"`
}

// VM 虚拟机信息
type VM struct {
	gorm.Model
	ConnectionID    uint        `gorm:"index:idx_vm_connection" json:"connectionId"`
	Connection      *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	VMKey           string      `gorm:"size:100;index" json:"vmKey"`
	UUID            string      `gorm:"size:100;index" json:"uuid"`
	Name            string      `gorm:"size:200;not null;index" json:"name"`
	Datacenter      string      `gorm:"size:100" json:"datacenter"`
	CpuCount        int32       `json:"cpuCount"`
	MemoryMB        int32       `json:"memoryMb"`
	PowerState      string      `gorm:"size:50;index" json:"powerState"`
	ConnectionState string      `gorm:"size:50" json:"connectionState"`
	IPAddress       string      `gorm:"size:50" json:"ipAddress"`
	GuestOS         string      `gorm:"size:100" json:"guestOs"`
	HostName        string      `gorm:"size:200" json:"hostName"`
	OverallStatus   string      `gorm:"size:50" json:"overallStatus"`
	CollectedAt     time.Time   `json:"collectedAt"`
}

// VMMetric 性能指标
type VMMetric struct {
	gorm.Model
	VMID       uint      `gorm:"index:idx_vm_metric_vm" json:"vmId"`
	VM         *VM       `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	MetricType string    `gorm:"size:50;index:idx_vm_metric_type" json:"metricType"`
	Timestamp  time.Time `gorm:"index:idx_vm_metric_timestamp" json:"timestamp"`
	Value      float64   `json:"value"`
}

// Metric 旧的性能指标表名，保持向后兼容
// Deprecated: 使用 VMMetric 代替
type Metric = VMMetric

// ==============================================================================
// 任务层 - 用户操作
// ==============================================================================

// AssessmentTask 评估任务
type AssessmentTask struct {
	gorm.Model
	Name           string     `gorm:"size:200;not null" json:"name"`
	ConnectionID   uint       `gorm:"index" json:"connectionId"`
	ConnectionName string     `gorm:"size:200" json:"connectionName"`
	Platform       string     `gorm:"size:20" json:"platform"`

	// 采集配置
	SelectedVMs string     `gorm:"type:text" json:"selectedVMs"`
	MetricsDays int        `gorm:"default:30" json:"metricsDays"`

	// 任务状态: pending | collecting | analyzing | completed | failed | cancelled
	Status     string     `gorm:"size:20;not null;index" json:"status"`
	Progress   int        `gorm:"default:0" json:"progress"`
	CurrentStep string    `gorm:"size:100" json:"currentStep"`
	Error      string     `gorm:"type:text" json:"error"`

	// 时间
	StartedAt   *time.Time `json:"startedAt"`
	CompletedAt *time.Time `json:"completedAt"`
}

// TableName 指定表名
func (AssessmentTask) TableName() string {
	return "tasks"
}

// Task 旧的任务表名，保持向后兼容
// Deprecated: 使用 AssessmentTask 代替
type Task = AssessmentTask

// TaskVMSnapshot 任务虚拟机快照
type TaskVMSnapshot struct {
	gorm.Model
	TaskID       uint      `gorm:"index:idx_task_vm_snapshot_task" json:"taskId"`
	Task         *AssessmentTask `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	ConnectionID uint      `gorm:"index:idx_task_vm_snapshot_conn" json:"connectionId"`
	Connection   *Connection `gorm:"constraint:OnDelete:CASCADE" json:"-"`

	// VM标识
	VMKey       string    `gorm:"size:120;index:idx_task_vm_snapshot_vmkey" json:"vmKey"`
	UUID        string    `gorm:"size:100;index" json:"uuid"`
	Name        string    `gorm:"size:200;index" json:"name"`
	Datacenter  string    `gorm:"size:100" json:"datacenter"`

	// 配置快照
	CpuCount        int32  `json:"cpuCount"`
	MemoryMB        int32  `json:"memoryMb"`
	PowerState      string `json:"powerState"`
	ConnectionState string `gorm:"size:50" json:"connectionState"`
	GuestOS         string `json:"guestOs"`

	// 状态快照
	IPAddress     string `gorm:"size:50" json:"ipAddress"`
	HostName      string `gorm:"size:200" json:"hostName"`
	OverallStatus string `gorm:"size:50" json:"overallStatus"`

	CollectedAt   time.Time `json:"collectedAt"`
}

// TaskAnalysisJob 任务分析子任务
type TaskAnalysisJob struct {
	gorm.Model
	TaskID       uint            `gorm:"index:idx_task_analysis_job_task" json:"taskId"`
	Task         *AssessmentTask `gorm:"constraint:OnDelete:CASCADE" json:"-"`

	// 分析类型: zombie | rightsize | tidal | health
	JobType      string `gorm:"size:50;not null;index:idx_task_analysis_job_type" json:"jobType"`

	// 执行状态: pending | running | completed | failed
	Status       string     `gorm:"size:20;not null" json:"status"`
	Progress     int        `gorm:"default:0" json:"progress"`
	StartedAt    *time.Time `json:"startedAt"`
	CompletedAt  *time.Time `json:"completedAt"`
	Error        string     `gorm:"type:text" json:"error"`

	// 分析结果 (JSON存储)
	Result       string `gorm:"type:text" json:"result"`
	ResultCount  int    `gorm:"default:0" json:"resultCount"`
}

// TaskAnalysisResult 旧的分析结果表名，保持向后兼容
// Deprecated: 使用 TaskAnalysisJob 代替
type TaskAnalysisResult = TaskAnalysisJob

// ==============================================================================
// 输出层 - 分析结果和报告
// ==============================================================================

// AnalysisFinding 分析发现
type AnalysisFinding struct {
	gorm.Model
	TaskID      uint            `gorm:"index:idx_analysis_finding_task" json:"taskId"`
	Task        *AssessmentTask `gorm:"constraint:OnDelete:CASCADE" json:"-"`

	// 分析类型
	JobType     string `gorm:"size:50;not null;index:idx_analysis_finding_job_type" json:"jobType"`

	// 目标对象
	TargetType  string `gorm:"size:50;not null;index:idx_analysis_finding_target" json:"targetType"`
	TargetKey   string `gorm:"size:100;not null;index" json:"targetKey"`
	TargetName  string `gorm:"size:200;not null" json:"targetName"`

	// 发现的问题
	Severity    string `gorm:"size:20;not null;index" json:"severity"` // critical | warning | info
	Category    string `gorm:"size:50;not null;index" json:"category"`
	Title       string `gorm:"size:200;not null" json:"title"`
	Description string `gorm:"type:text" json:"description"`

	// 建议
	Action      string `gorm:"type:text" json:"action"`
	Reason      string `gorm:"type:text" json:"reason"`

	// 估算收益
	SavingCPU   int32  `gorm:"default:0" json:"savingCpu"`
	SavingMemory int32 `gorm:"default:0" json:"savingMemory"`
	SavingCost  string `gorm:"size:100" json:"savingCost"`

	// 详细数据
	Details     string `gorm:"type:text" json:"details"`

	CreatedAt   time.Time `json:"createdAt"`
}

// TaskReport 任务报告
type TaskReport struct {
	gorm.Model
	TaskID       uint            `gorm:"index:idx_task_report_task" json:"taskId"`
	Task         *AssessmentTask `gorm:"constraint:OnDelete:CASCADE" json:"-"`

	// 报告类型: comprehensive | zombie | rightsize | tidal | health
	ReportType   string `gorm:"size:50;not null;index" json:"reportType"`
	Format       string `gorm:"size:20;not null" json:"format"`

	// 报告内容
	Title        string `gorm:"size:200;not null" json:"title"`
	FilePath     string `gorm:"size:500" json:"filePath"`
	FileSize     int64  `json:"fileSize"`

	// 生成信息
	Status       string `gorm:"size:20;default:pending" json:"status"`
	GeneratedAt  *time.Time `json:"generatedAt"`
}

// Report 旧的报告表名，保持向后兼容
// Deprecated: 使用 TaskReport 代替
type Report = TaskReport

// ==============================================================================
// 系统配置层
// ==============================================================================

// Settings 系统配置
type Settings struct {
	gorm.Model
	Key   string `gorm:"size:100;uniqueIndex;not null" json:"key"`
	Value string `gorm:"type:text" json:"value"`
	Type  string `gorm:"size:20;default:string" json:"type"`
}

// TaskLog 任务操作日志
type TaskLog struct {
	gorm.Model
	TaskID       uint       `gorm:"index:idx_task_log_task;not null" json:"taskId"`
	Task         *AssessmentTask `gorm:"constraint:OnDelete:CASCADE" json:"-"`
	JobID        *uint      `gorm:"index:idx_task_log_job" json:"jobId"`
	Job          *TaskAnalysisJob `gorm:"constraint:OnDelete:CASCADE" json:"-"`

	// 操作信息
	Operation    string     `gorm:"size:50;not null;index" json:"operation"`
	Category     string     `gorm:"size:50;index" json:"category"`

	// 详细内容
	Title        string     `gorm:"size:200" json:"title"`
	Message      string     `gorm:"type:text" json:"message"`
	Config       string     `gorm:"type:text" json:"config"`
	Result       string     `gorm:"type:text" json:"result"`

	// 元数据
	Duration     int64      `gorm:"default:0" json:"duration"`
	UserID       string     `gorm:"size:100" json:"userId"`
	IPAddress    string     `gorm:"size:50" json:"ipAddress"`

	CreatedAt    time.Time  `json:"createdAt"`
}

// ==============================================================================
// 向后兼容的类型别名
// ==============================================================================

// V2 类型别名 (向后兼容)
type VMMetrics = VMMetric

// TaskVMSnapshots 任务快照复数别名
type TaskVMSnapshots = TaskVMSnapshot

// AnalysisFindings 分析发现复数别名
type AnalysisFindings = AnalysisFinding

// TaskReports 任务报告复数别名
type TaskReports = TaskReport

// TaskLogs 任务日志复数别名
type TaskLogs = TaskLog

// ==============================================================================
// 告警相关（保留用于兼容）
// ==============================================================================

// AnalysisResult 旧的分析结果类型
// Deprecated: 使用 AnalysisFinding 代替
type AnalysisResult struct {
	gorm.Model
	ReportID       uint   `gorm:"index:idx_analysis_report" json:"reportId"`
	AnalysisType   string `gorm:"size:50;index" json:"analysisType"`
	TargetType     string `gorm:"size:50" json:"targetType"`
	TargetKey      string `gorm:"size:100;index" json:"targetKey"`
	TargetName     string `gorm:"size:200" json:"targetName"`
	Data           string `gorm:"type:text" json:"data"`
	Recommendation string `gorm:"type:text" json:"recommendation"`
	SavedAmount    string `gorm:"size:100" json:"savedAmount"`
}

// Alert 旧的告警类型
// Deprecated: 告警功能已合并到 AnalysisFinding 中
type Alert struct {
	gorm.Model
	TargetType     string     `gorm:"size:50;index" json:"targetType"`
	TargetKey      string     `gorm:"size:100;index" json:"targetKey"`
	TargetName     string     `gorm:"size:200" json:"targetName"`
	AlertType      string     `gorm:"size:50;index" json:"alertType"`
	Severity       string     `gorm:"size:20" json:"severity"`
	Title          string     `gorm:"size:200" json:"title"`
	Message        string     `gorm:"type:text" json:"message"`
	Data           string     `gorm:"type:text" json:"data"`
	Acknowledged   bool       `gorm:"default:false" json:"acknowledged"`
	AcknowledgedAt *time.Time `json:"acknowledgedAt"`
	CreatedAt      time.Time  `json:"createdAt"`
}
