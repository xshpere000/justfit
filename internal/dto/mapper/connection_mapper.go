// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// ConnectionMapper 连接数据映射器
type ConnectionMapper struct{}

// NewConnectionMapper 创建连接映射器
func NewConnectionMapper() *ConnectionMapper {
	return &ConnectionMapper{}
}

// ToDTO 转换为响应 DTO
func (m *ConnectionMapper) ToDTO(model *storage.Connection) *response.ConnectionResponse {
	if model == nil {
		return nil
	}

	return &response.ConnectionResponse{
		ID:        model.ID,
		Name:      model.Name,
		Platform:  model.Platform,
		Host:      model.Host,
		Port:      model.Port,
		Username:  model.Username,
		Insecure:  model.Insecure,
		Status:    model.Status,
		CreatedAt: model.CreatedAt,
		LastSync:  model.LastSync,
	}
}

// ToListItem 转换为列表项
func (m *ConnectionMapper) ToListItem(model *storage.Connection, vmCount int) *response.ConnectionListItem {
	if model == nil {
		return nil
	}

	var lastSync *string
	if model.LastSync != nil {
		s := model.LastSync.Format("2006-01-02 15:04:05")
		lastSync = &s
	}

	return &response.ConnectionListItem{
		ID:       model.ID,
		Name:     model.Name,
		Platform: model.Platform,
		Host:     model.Host,
		Status:   model.Status,
		VMCount:  vmCount,
		LastSync: lastSync,
	}
}

// ToDTOList 批量转换
func (m *ConnectionMapper) ToDTOList(models []storage.Connection) []response.ConnectionResponse {
	if len(models) == 0 {
		return []response.ConnectionResponse{}
	}

	result := make([]response.ConnectionResponse, len(models))
	for i := range models {
		if dto := m.ToDTO(&models[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}
