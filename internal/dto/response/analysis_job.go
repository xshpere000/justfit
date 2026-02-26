// Package response 定义分析子任务相关响应 DTO
package response

import "time"

// TaskAnalysisJobResponse 分析子任务响应
type TaskAnalysisJobResponse struct {
	ID          uint       `json:"id"`
	TaskID      uint       `json:"taskId"`
	JobType     string     `json:"jobType"`     // zombie, rightsize, tidal, health
	Status      string     `json:"status"`       // pending, running, completed, failed
	Progress    int        `json:"progress"`
	Error       string     `json:"error,omitempty"`
	ResultCount int        `json:"resultCount"`
	StartedAt   *time.Time `json:"startedAt,omitempty"`
	CompletedAt *time.Time `json:"completedAt,omitempty"`
	CreatedAt   time.Time  `json:"createdAt"`
}

// TaskAnalysisJobListResponse 分析子任务列表响应
type TaskAnalysisJobListResponse struct {
	Total int                        `json:"total"`
	Items []TaskAnalysisJobResponse   `json:"items"`
}
