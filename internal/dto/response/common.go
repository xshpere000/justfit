// Package response 定义 API 响应 DTO
package response

// Response 标准 API 响应结构（泛型）
type Response[T any] struct {
	Success bool   `json:"success"`
	Data    T      `json:"data,omitempty"`
	Message string `json:"message,omitempty"`
	Error   string `json:"error,omitempty"`
	Code    string `json:"code,omitempty"`
}

// NewSuccessResponse 创建成功响应
func NewSuccessResponse[T any](data T) *Response[T] {
	return &Response[T]{
		Success: true,
		Data:    data,
	}
}

// NewErrorResponse 创建错误响应
func NewErrorResponse(code, message string) *Response[any] {
	return &Response[any]{
		Success: false,
		Code:    code,
		Error:   message,
	}
}

// PagedResponse 分页响应结构（泛型）
type PagedResponse[T any] struct {
	Total int64 `json:"total"`
	Page  int   `json:"page"`
	Size  int   `json:"size"`
	Items []T   `json:"items"`
}

// NewPagedResponse 创建分页响应
func NewPagedResponse[T any](total int64, page, size int, items []T) *PagedResponse[T] {
	return &PagedResponse[T]{
		Total: total,
		Page:  page,
		Size:  size,
		Items: items,
	}
}
