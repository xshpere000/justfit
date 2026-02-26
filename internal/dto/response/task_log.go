// Package response 定义任务日志相关响应 DTO
package response

import "time"

// TaskLogResponse 任务日志响应
type TaskLogResponse struct {
	ID         uint       `json:"id"`
	TaskID     uint       `json:"taskId"`
	JobID      *uint      `json:"jobId,omitempty"`

	// 操作信息
	Operation  string     `json:"operation"`  // task_created, data_collected, analysis_started, analysis_completed, error, etc.
	Category   string     `json:"category"`   // system, user, info, warning, error, success

	// 详细内容
	Title      string     `json:"title"`
	Message    string     `json:"message"`
	Config     string     `json:"config,omitempty"`   // 操作配置 (JSON)
	Result     string     `json:"result,omitempty"`   // 操作结果 (JSON)

	// 元数据
	Duration   int64      `json:"duration"`          // 执行耗时 (毫秒)
	UserID     string     `json:"userId,omitempty"`
	IPAddress  string     `json:"ipAddress,omitempty"`

	CreatedAt  time.Time  `json:"createdAt"`
}

// TaskLogListResponse 任务日志列表响应
type TaskLogListResponse struct {
	Total int                 `json:"total"`
	Items []TaskLogResponse   `json:"items"`
}
