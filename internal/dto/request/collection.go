// Package request 定义 API 请求 DTO
package request

// CreateCollectionRequest 创建采集任务请求
type CreateCollectionRequest struct {
	ConnectionID   uint     `json:"connection_id" validate:"required"`
	ConnectionName string   `json:"connection_name"`
	Platform       string   `json:"platform"`
	DataTypes      []string `json:"data_types"`      // clusters, hosts, vms, metrics
	MetricsDays    int      `json:"metrics_days"`
	TotalVMs       int      `json:"total_vms"`       // 虚拟机总数
	SelectedVMs    []string `json:"selected_vms"`    // 用户选择的虚拟机列表（vmKey 格式）
}

// CreateAnalysisRequest 创建分析任务请求
type CreateAnalysisRequest struct {
	ConnectionID  uint                   `json:"connection_id" validate:"required"`
	AnalysisType  string                 `json:"analysis_type" validate:"required,oneof=zombie rightsize tidal health"` // zombie, rightsize, tidal, health
	Config        map[string]interface{} `json:"config"`
}
