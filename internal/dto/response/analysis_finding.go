// Package response 定义分析发现相关响应 DTO
package response

import "time"

// AnalysisFindingResponse 分析发现响应
type AnalysisFindingResponse struct {
	ID      uint   `json:"id"`
	TaskID  uint   `json:"taskId"`
	JobType string `json:"jobType"` // zombie, rightsize, tidal, health

	// 目标对象
	TargetType string `json:"targetType"` // vm, cluster, host
	TargetKey  string `json:"targetKey"`
	TargetName string `json:"targetName"`

	// 发现的问题
	Severity    string `json:"severity"` // critical, warning, info
	Category    string `json:"category"` // zombie, overprovisioned, underprovisioned, tidal_pattern, health_risk
	Title       string `json:"title"`
	Description string `json:"description"`

	// 建议
	Action string `json:"action"`
	Reason string `json:"reason"`

	// 估算收益
	SavingCPU    int32  `json:"savingCpu"`
	SavingMemory int32  `json:"savingMemory"`
	SavingCost   string `json:"savingCost"`

	// 详细数据
	Details string `json:"details"`

	CreatedAt time.Time `json:"createdAt"`
}

// AnalysisFindingListResponse 分析发现列表响应
type AnalysisFindingListResponse struct {
	Total int                       `json:"total"`
	Items []AnalysisFindingResponse `json:"items"`
}

// AnalysisFindingStatsResponse 分析发现统计响应
type AnalysisFindingStatsResponse struct {
	Total             int64            `json:"total"`
	BySeverity        map[string]int64 `json:"bySeverity"`
	ByCategory        map[string]int64 `json:"byCategory"`
	ByJobType         map[string]int64 `json:"byJobType"`
	TotalSavingCPU    int64            `json:"totalSavingCpu"`
	TotalSavingMemory int64            `json:"totalSavingMemory"`
}
