// Package request 定义任务相关请求 DTO
package request

// CreateCollectionTaskRequest 创建采集任务请求
type CreateCollectionTaskRequest struct {
	ConnectionID uint     `json:"connection_id" validate:"required"`
	SelectedVMs  []string `json:"selected_vms"`
	DataTypes    []string `json:"data_types" validate:"required,dive,oneof=clusters hosts vms metrics"`
	MetricsDays  int      `json:"metrics_days" validate:"min=1,max=365"`
	Concurrency  int      `json:"concurrency" validate:"min=1,max=10"`
}

// CreateAnalysisTaskRequest 创建分析任务请求
type CreateAnalysisTaskRequest struct {
	ConnectionID  uint                   `json:"connection_id" validate:"required"`
	AnalysisTypes []string               `json:"analysis_types" validate:"required,dive,oneof=zombie_vm right_size tidal health_score"`
	Config        map[string]interface{} `json:"config"`
}

// ListTasksRequest 查询任务列表请求
type ListTasksRequest struct {
	Type   string `json:"type" validate:"omitempty,oneof=collection analysis report"`
	Status string `json:"status" validate:"omitempty,oneof=pending running completed failed cancelled"`
	Limit  int    `json:"limit" validate:"omitempty,min=1,max=100"`
	Offset int    `json:"offset" validate:"omitempty,min=0"`
}

// ListResourcesRequest 查询资源列表请求
type ListResourcesRequest struct {
	ConnectionID uint   `json:"connection_id" validate:"required"`
	Limit        int    `json:"limit" validate:"omitempty,min=1,max=500"`
	Offset       int    `json:"offset" validate:"omitempty,min=0"`
}

// GetMetricsRequest 获取指标请求
type GetMetricsRequest struct {
	VMID       uint   `json:"vm_id" validate:"required"`
	MetricType string `json:"metric_type" validate:"required,oneof=cpu memory disk_read disk_write net_rx net_tx"`
	Days       int    `json:"days" validate:"min=1,max=365"`
}
