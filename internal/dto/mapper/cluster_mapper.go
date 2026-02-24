// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// ClusterMapper 集群数据映射器
type ClusterMapper struct{}

// NewClusterMapper 创建集群映射器
func NewClusterMapper() *ClusterMapper {
	return &ClusterMapper{}
}

// ToDTO 转换为响应 DTO
func (m *ClusterMapper) ToDTO(model *storage.Cluster) *response.ClusterResponse {
	if model == nil {
		return nil
	}

	return &response.ClusterResponse{
		ID:            model.ID,
		Name:          model.Name,
		Datacenter:    model.Datacenter,
		TotalCPU:      model.TotalCpu,
		TotalMemory:   model.TotalMemory,
		TotalMemoryGB: float64(model.TotalMemory) / (1024 * 1024 * 1024),
		NumHosts:      model.NumHosts,
		NumVMs:        model.NumVMs,
		Status:        model.Status,
		CollectedAt:   model.CollectedAt,
	}
}

// ToDTOList 批量转换
func (m *ClusterMapper) ToDTOList(models []storage.Cluster) []response.ClusterResponse {
	if len(models) == 0 {
		return []response.ClusterResponse{}
	}

	result := make([]response.ClusterResponse, len(models))
	for i := range models {
		if dto := m.ToDTO(&models[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}
