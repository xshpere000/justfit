// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// HostMapper 主机数据映射器
type HostMapper struct{}

// NewHostMapper 创建主机映射器
func NewHostMapper() *HostMapper {
	return &HostMapper{}
}

// ToDTO 转换为响应 DTO
func (m *HostMapper) ToDTO(model *storage.Host) *response.HostResponse {
	if model == nil {
		return nil
	}

	return &response.HostResponse{
		ID:            model.ID,
		Name:          model.Name,
		Datacenter:    model.Datacenter,
		IPAddress:     model.IPAddress,
		CPUCores:      model.CpuCores,
		CPUMHz:        model.CpuMhz,
		MemoryMB:      model.Memory,
		MemoryGB:      float64(model.Memory) / (1024 * 1024),
		NumVMs:        model.NumVMs,
		PowerState:    model.PowerState,
		OverallStatus: model.OverallStatus,
		CollectedAt:   model.CollectedAt,
	}
}

// ToDTOList 批量转换
func (m *HostMapper) ToDTOList(models []storage.Host) []response.HostResponse {
	if len(models) == 0 {
		return []response.HostResponse{}
	}

	result := make([]response.HostResponse, len(models))
	for i := range models {
		if dto := m.ToDTO(&models[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}
