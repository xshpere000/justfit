// Package response 定义任务相关响应 DTO
package response

import "time"

// TaskResponse 任务响应
type TaskResponse struct {
	ID               uint       `json:"id"`
	Type             string     `json:"type"`
	Name             string     `json:"name"`
	Status           string     `json:"status"`
	Progress         int        `json:"progress"`
	Error            string     `json:"error,omitempty"`
	CreatedAt        time.Time  `json:"createdAt"`
	StartedAt        *time.Time `json:"startedAt,omitempty"`
	CompletedAt      *time.Time `json:"completedAt,omitempty"`
	DurationMs       int64      `json:"durationMs,omitempty"`
	ConnectionID     uint       `json:"connectionId,omitempty"`
	ConnectionName   string     `json:"connectionName,omitempty"`
	Platform         string     `json:"platform,omitempty"`
	VMCount          int32      `json:"vmCount,omitempty"`
	CollectedVMCount int32      `json:"collectedVMCount,omitempty"`
}

// TaskDetailResponse 任务详情响应
type TaskDetailResponse struct {
	TaskResponse
	CurrentStep     string                 `json:"currentStep,omitempty"`
	Config          map[string]interface{} `json:"config,omitempty"`
	Result          map[string]interface{} `json:"result,omitempty"`
	AnalysisResults map[string]bool        `json:"analysisResults,omitempty"`
}

// TaskLogEntry 任务日志条目
type TaskLogEntry struct {
	Timestamp string                 `json:"timestamp"` // ISO 8601
	Level     string                 `json:"level"`     // info, warning, error
	Message   string                 `json:"message"`
	Fields    map[string]interface{} `json:"fields,omitempty"` // 保留用于扩展
}
