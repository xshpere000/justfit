// Package request 定义 API 请求 DTO
package request

// CreateCollectionRequest 创建采集任务请求
type CreateCollectionRequest struct {
	ConnectionID   uint     `json:"connectionId" validate:"required"`
	ConnectionName string   `json:"connectionName"`
	Platform       string   `json:"platform"`
	DataTypes      []string `json:"dataTypes"`      // clusters, hosts, vms, metrics
	MetricsDays    int      `json:"metricsDays"`
	VMCount        int      `json:"vmCount"`       // 虚拟机总数
	SelectedVMs    []string `json:"selectedVMs"`   // 用户选择的虚拟机列表（vmKey 格式）
}

// CreateAnalysisRequest 创建分析任务请求
type CreateAnalysisRequest struct {
	ConnectionID  uint                   `json:"connectionId" validate:"required"`
	AnalysisType  string                 `json:"analysisType" validate:"required,oneof=zombie rightsize tidal health"` // zombie, rightsize, tidal, health
	Config        map[string]interface{} `json:"config"`
}
