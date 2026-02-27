// Package response 定义分析相关响应 DTO
package response

// ZombieVMResult 僵尸 VM 分析结果
type ZombieVMResult struct {
	VMName         string   `json:"vmName"`
	Datacenter     string   `json:"datacenter"`
	Host           string   `json:"host"`
	CPUCount       int32    `json:"cpuCount"`
	MemoryMB       int32    `json:"memoryMb"`
	CPUUsage       float64  `json:"cpuUsage"`       // 平均 CPU 使用率 (%)
	MemoryUsage    float64  `json:"memoryUsage"`    // 平均内存使用率 (%)
	DiskIORate     float64  `json:"diskIoRate"`     // 平均磁盘 I/O
	NetworkRate    float64  `json:"networkRate"`    // 平均网络速率
	Confidence     float64  `json:"confidence"`     // 置信度 (0-100)
	DaysLowUsage   int      `json:"daysLowUsage"`   // 低负载天数
	Evidence       []string `json:"evidence"`       // 证据列表
	Recommendation string   `json:"recommendation"` // 建议操作
}

// RightSizeResult Right Size 分析结果
type RightSizeResult struct {
	VMName              string  `json:"vmName"`
	Datacenter          string  `json:"datacenter"`
	CurrentCPU          int32   `json:"currentCpu"`
	CurrentMemoryMB     int32   `json:"currentMemoryMb"`
	CurrentMemoryGB     float64 `json:"currentMemoryGb"`
	RecommendedCPU      int32   `json:"recommendedCpu"`
	RecommendedMemoryMB int32   `json:"recommendedMemoryMb"`
	RecommendedMemoryGB float64 `json:"recommendedMemoryGb"`
	AdjustmentType      string  `json:"adjustmentType"`  // none, up, down
	RiskLevel           string  `json:"riskLevel"`       // low, medium, high
	EstimatedSaving     string  `json:"estimatedSaving"` // 节省估算
	Confidence          float64 `json:"confidence"`      // 置信度
}

// TidalResult 潮汐分析结果
type TidalResult struct {
	VMName          string  `json:"vmName"`
	Datacenter      string  `json:"datacenter"`
	Pattern         string  `json:"pattern"`         // daily, weekly, none
	StabilityScore  float64 `json:"stabilityScore"`  // 稳定性评分
	PeakHours       []int   `json:"peakHours"`       // 峰值小时 (0-23)
	PeakDays        []int   `json:"peakDays"`        // 峰值星期 (0-6)
	Recommendation  string  `json:"recommendation"`  // 建议操作
	EstimatedSaving string  `json:"estimatedSaving"` // 节省估算
}

// HealthScoreResult 健康评分结果
type HealthScoreResult struct {
	ConnectionID         uint     `json:"connectionId"`
	ConnectionName       string   `json:"connectionName"`
	OverallScore         float64  `json:"overallScore"`         // 总分 (0-100)
	HealthLevel          string   `json:"healthLevel"`          // excellent, good, fair, poor
	ResourceBalance      float64  `json:"resourceBalance"`      // 资源均衡度
	OvercommitRisk       float64  `json:"overcommitRisk"`       // 超配风险
	HotspotConcentration float64  `json:"hotspotConcentration"` // 热点集中度
	ClusterCount         int      `json:"clusterCount"`
	HostCount            int      `json:"hostCount"`
	VMCount              int      `json:"vmCount"`
	RiskItems            []string `json:"riskItems"`
	Recommendations      []string `json:"recommendations"`
}

// AnalysisSummary 分析汇总
type AnalysisSummary struct {
	ConnectionID     uint           `json:"connectionId"`
	VMCount          int64          `json:"vmCount"`
	ZombieVMs        int            `json:"zombieVMs"`
	RightSizeVMs     int            `json:"rightSizeVMs"`
	TidalVMs         int            `json:"tidalVMs"`
	HealthScore      float64        `json:"healthScore"`
	TotalSavings     string         `json:"totalSavings"`
	LastAnalyzed     string         `json:"lastAnalyzed"`
	RiskDistribution map[string]int `json:"riskDistribution"`
}
