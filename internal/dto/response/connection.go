// Package response 定义连接相关响应 DTO
package response

import "time"

// ConnectionResponse 连接响应
type ConnectionResponse struct {
	ID        uint       `json:"id"`
	Name      string     `json:"name"`
	Platform  string     `json:"platform"`
	Host      string     `json:"host"`
	Port      int        `json:"port"`
	Username  string     `json:"username"`
	Insecure  bool       `json:"insecure"`
	Status    string     `json:"status"`
	CreatedAt time.Time  `json:"created_at"`
	LastSync  *time.Time `json:"last_sync,omitempty"`
}

// ConnectionListItem 连接列表项
type ConnectionListItem struct {
	ID        uint    `json:"id"`
	Name      string  `json:"name"`
	Platform  string  `json:"platform"`
	Host      string  `json:"host"`
	Status    string  `json:"status"`
	VMCount   int     `json:"vm_count"`
	LastSync  *string `json:"last_sync,omitempty"`
}

// TestConnectionResponse 测试连接响应
type TestConnectionResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Version string `json:"version,omitempty"`
	Product string `json:"product,omitempty"`
	Latency int    `json:"latency,omitempty"` // 毫秒
}
