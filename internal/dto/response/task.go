// Package response 定义任务相关响应 DTO
package response

import "time"

// TaskResponse 任务响应
type TaskResponse struct {
	ID            uint       `json:"id"`
	Type          string     `json:"type"`
	Name          string     `json:"name"`
	Status        string     `json:"status"`
	Progress      int        `json:"progress"`
	Error         string     `json:"error,omitempty"`
	CreatedAt     time.Time  `json:"created_at"`
	StartedAt     *time.Time `json:"started_at,omitempty"`
	CompletedAt   *time.Time `json:"completed_at,omitempty"`
	DurationMs    int64      `json:"duration_ms,omitempty"`
	ConnectionID  uint       `json:"connection_id,omitempty"`
	ConnectionName string    `json:"connection_name,omitempty"`
	Platform      string     `json:"platform,omitempty"`
	TotalVMs      int32      `json:"total_vms,omitempty"`
	CollectedVMs  int32      `json:"collected_vms,omitempty"`
}

// TaskDetailResponse 任务详情响应
type TaskDetailResponse struct {
	TaskResponse
	CurrentStep     string                 `json:"current_step,omitempty"`
	Config          map[string]interface{} `json:"config,omitempty"`
	Result          map[string]interface{} `json:"result,omitempty"`
	AnalysisResults map[string]bool        `json:"analysis_results,omitempty"`
}

// TaskLogEntry 任务日志条目
type TaskLogEntry struct {
	Timestamp string                 `json:"timestamp"` // ISO 8601
	Level     string                 `json:"level"`     // info, warning, error
	Message   string                 `json:"message"`
	Fields    map[string]interface{} `json:"fields,omitempty"` // 保留用于扩展
}
