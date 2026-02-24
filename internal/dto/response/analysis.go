// Package response 定义分析相关响应 DTO
package response

// ZombieVMResult 僵尸 VM 分析结果
type ZombieVMResult struct {
	VMName        string   `json:"vm_name"`
	Datacenter    string   `json:"datacenter"`
	Host          string   `json:"host"`
	CPUCount      int32    `json:"cpu_count"`
	MemoryMB      int32    `json:"memory_mb"`
	CPUUsage      float64  `json:"cpu_usage"`      // 平均 CPU 使用率 (%)
	MemoryUsage   float64  `json:"memory_usage"`   // 平均内存使用率 (%)
	DiskIORate    float64  `json:"disk_io_rate"`   // 平均磁盘 I/O
	NetworkRate   float64  `json:"network_rate"`   // 平均网络速率
	Confidence    float64  `json:"confidence"`     // 置信度 (0-100)
	DaysLowUsage  int      `json:"days_low_usage"` // 低负载天数
	Evidence      []string `json:"evidence"`       // 证据列表
	Recommendation string  `json:"recommendation"` // 建议操作
}

// RightSizeResult Right Size 分析结果
type RightSizeResult struct {
	VMName               string  `json:"vm_name"`
	Datacenter           string  `json:"datacenter"`
	CurrentCPU           int32   `json:"current_cpu"`
	CurrentMemoryMB      int32   `json:"current_memory_mb"`
	CurrentMemoryGB      float64 `json:"current_memory_gb"`
	RecommendedCPU       int32   `json:"recommended_cpu"`
	RecommendedMemoryMB  int32   `json:"recommended_memory_mb"`
	RecommendedMemoryGB  float64 `json:"recommended_memory_gb"`
	AdjustmentType       string  `json:"adjustment_type"` // none, up, down
	RiskLevel            string  `json:"risk_level"`      // low, medium, high
	EstimatedSaving      string  `json:"estimated_saving"` // 节省估算
	Confidence           float64 `json:"confidence"`       // 置信度
}

// TidalResult 潮汐分析结果
type TidalResult struct {
	VMName         string   `json:"vm_name"`
	Datacenter     string   `json:"datacenter"`
	Pattern        string   `json:"pattern"`         // daily, weekly, none
	StabilityScore float64  `json:"stability_score"`  // 稳定性评分
	PeakHours      []int    `json:"peak_hours"`      // 峰值小时 (0-23)
	PeakDays       []int    `json:"peak_days"`       // 峰值星期 (0-6)
	Recommendation string   `json:"recommendation"`  // 建议操作
	EstimatedSaving string  `json:"estimated_saving"` // 节省估算
}

// HealthScoreResult 健康评分结果
type HealthScoreResult struct {
	ConnectionID         uint     `json:"connection_id"`
	ConnectionName       string   `json:"connection_name"`
	OverallScore         float64  `json:"overall_score"`          // 总分 (0-100)
	HealthLevel          string   `json:"health_level"`           // excellent, good, fair, poor
	ResourceBalance      float64  `json:"resource_balance"`       // 资源均衡度
	OvercommitRisk       float64  `json:"overcommit_risk"`        // 超配风险
	HotspotConcentration float64  `json:"hotspot_concentration"` // 热点集中度
	TotalClusters        int      `json:"total_clusters"`
	TotalHosts           int      `json:"total_hosts"`
	TotalVMs             int      `json:"total_vms"`
	RiskItems            []string `json:"risk_items"`
	Recommendations      []string `json:"recommendations"`
}

// AnalysisSummary 分析汇总
type AnalysisSummary struct {
	ConnectionID     uint            `json:"connection_id"`
	TotalVMs         int64           `json:"total_vms"`
	ZombieVMs        int             `json:"zombie_vms"`
	RightSizeVMs     int             `json:"right_size_vms"`
	TidalVMs         int             `json:"tidal_vms"`
	HealthScore      float64         `json:"health_score"`
	TotalSavings     string          `json:"total_savings"`
	LastAnalyzed     string          `json:"last_analyzed"`
	RiskDistribution map[string]int `json:"risk_distribution"`
}
