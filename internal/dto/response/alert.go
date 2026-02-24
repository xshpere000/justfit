// Package response 定义告警相关响应 DTO
package response

import "time"

// AlertResponse 告警响应
type AlertResponse struct {
	ID             uint       `json:"id"`
	TargetType     string     `json:"target_type"`     // cluster, host, vm
	TargetKey      string     `json:"target_key"`      // 目标唯一标识
	TargetName     string     `json:"target_name"`     // 目标名称
	AlertType      string     `json:"alert_type"`      // zombie_vm, overprovisioned, etc.
	Severity       string     `json:"severity"`        // info, warning, critical
	Title          string     `json:"title"`
	Message        string     `json:"message"`
	Data           string     `json:"data,omitempty"`  // JSON 字符串
	Acknowledged   bool       `json:"acknowledged"`
	AcknowledgedAt *time.Time `json:"acknowledged_at,omitempty"`
	CreatedAt      time.Time  `json:"created_at"`
}

// AlertListItem 告警列表项
type AlertListItem struct {
	ID             uint       `json:"id"`
	TargetType     string     `json:"target_type"`
	TargetName     string     `json:"target_name"`
	AlertType      string     `json:"alert_type"`
	Severity       string     `json:"severity"`
	Title          string     `json:"title"`
	Message        string     `json:"message"`
	Acknowledged   bool       `json:"acknowledged"`
	CreatedAt      time.Time  `json:"created_at"`
}

// AlertStats 告警统计
type AlertStats struct {
	Total          int64            `json:"total"`
	Unacknowledged int64            `json:"unacknowledged"`
	BySeverity     map[string]int64 `json:"by_severity"`
	ByType         map[string]int64 `json:"by_type"`
}
