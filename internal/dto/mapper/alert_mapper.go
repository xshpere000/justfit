// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// AlertMapper 告警数据映射器
type AlertMapper struct{}

// NewAlertMapper 创建告警映射器
func NewAlertMapper() *AlertMapper {
	return &AlertMapper{}
}

// ToDTO 转换为响应 DTO
func (m *AlertMapper) ToDTO(model *storage.Alert) *response.AlertResponse {
	if model == nil {
		return nil
	}

	return &response.AlertResponse{
		ID:             model.ID,
		TargetType:     model.TargetType,
		TargetKey:      model.TargetKey,
		TargetName:     model.TargetName,
		AlertType:      model.AlertType,
		Severity:       model.Severity,
		Title:          model.Title,
		Message:        model.Message,
		Data:           model.Data,
		Acknowledged:   model.Acknowledged,
		AcknowledgedAt: model.AcknowledgedAt,
		CreatedAt:      model.CreatedAt,
	}
}

// ToListItem 转换为列表项
func (m *AlertMapper) ToListItem(model *storage.Alert) *response.AlertListItem {
	if model == nil {
		return nil
	}

	return &response.AlertListItem{
		ID:           model.ID,
		TargetType:   model.TargetType,
		TargetName:   model.TargetName,
		AlertType:    model.AlertType,
		Severity:     model.Severity,
		Title:        model.Title,
		Message:      model.Message,
		Acknowledged: model.Acknowledged,
		CreatedAt:    model.CreatedAt,
	}
}

// ToDTOList 批量转换
func (m *AlertMapper) ToDTOList(models []storage.Alert) []response.AlertResponse {
	if len(models) == 0 {
		return []response.AlertResponse{}
	}

	result := make([]response.AlertResponse, len(models))
	for i := range models {
		if dto := m.ToDTO(&models[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}

// ToListItemList 批量转换为列表项
func (m *AlertMapper) ToListItemList(models []storage.Alert) []response.AlertListItem {
	if len(models) == 0 {
		return []response.AlertListItem{}
	}

	result := make([]response.AlertListItem, len(models))
	for i := range models {
		if dto := m.ToListItem(&models[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}
