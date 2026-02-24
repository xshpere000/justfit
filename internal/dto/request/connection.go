// Package request 定义 API 请求 DTO
package request

// CreateConnectionRequest 创建连接请求
type CreateConnectionRequest struct {
	Name     string `json:"name" validate:"required,min=1,max=100"`
	Platform string `json:"platform" validate:"required,oneof=vcenter h3c-uis"`
	Host     string `json:"host" validate:"required,ip|hostname"`
	Port     int    `json:"port" validate:"required,min=1,max=65535"`
	Username string `json:"username" validate:"required,min=1,max=100"`
	Password string `json:"password" validate:"required,min=1"`
	Insecure bool   `json:"insecure"`
}

// UpdateConnectionRequest 更新连接请求
type UpdateConnectionRequest struct {
	ID       uint   `json:"id" validate:"required"`
	Name     string `json:"name" validate:"required,min=1,max=100"`
	Platform string `json:"platform" validate:"required,oneof=vcenter h3c-uis"`
	Host     string `json:"host" validate:"required,ip|hostname"`
	Port     int    `json:"port" validate:"required,min=1,max=65535"`
	Username string `json:"username" validate:"required,min=1,max=100"`
	Password string `json:"password" validate:"omitempty,min=1"` // 可选
	Insecure bool   `json:"insecure"`
}

// TestConnectionRequest 测试连接请求
type TestConnectionRequest struct {
	ID   uint   `json:"id" validate:"required"`
	Host string `json:"host" validate:"required"`
	Port int    `json:"port" validate:"required"`
}
