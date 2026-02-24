// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// VMMapper VM 数据映射器
type VMMapper struct{}

// NewVMMapper 创建 VM 映射器
func NewVMMapper() *VMMapper {
	return &VMMapper{}
}

// ToDTO 转换为响应 DTO
func (m *VMMapper) ToDTO(model *storage.VM) *response.VMResponse {
	if model == nil {
		return nil
	}

	return &response.VMResponse{
		ID:            model.ID,
		Name:          model.Name,
		Datacenter:    model.Datacenter,
		UUID:          model.UUID,
		CPUCount:      model.CpuCount,
		MemoryMB:      model.MemoryMB,
		MemoryGB:      float64(model.MemoryMB) / 1024,
		PowerState:    model.PowerState,
		IPAddress:     model.IPAddress,
		GuestOS:       model.GuestOS,
		HostName:      model.HostName,
		OverallStatus: model.OverallStatus,
		CollectedAt:   model.CollectedAt,
	}
}

// ToDTOList 批量转换
func (m *VMMapper) ToDTOList(models []storage.VM) []response.VMResponse {
	if len(models) == 0 {
		return []response.VMResponse{}
	}

	result := make([]response.VMResponse, len(models))
	for i := range models {
		if dto := m.ToDTO(&models[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}
