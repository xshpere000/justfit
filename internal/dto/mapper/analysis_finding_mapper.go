// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// AnalysisFindingMapper 分析发现数据映射器
type AnalysisFindingMapper struct{}

// NewAnalysisFindingMapper 创建分析发现映射器
func NewAnalysisFindingMapper() *AnalysisFindingMapper {
	return &AnalysisFindingMapper{}
}

// ToDTO 转换为响应 DTO
func (m *AnalysisFindingMapper) ToDTO(finding *storage.AnalysisFinding) *response.AnalysisFindingResponse {
	if finding == nil {
		return nil
	}

	return &response.AnalysisFindingResponse{
		ID:           finding.ID,
		TaskID:       finding.TaskID,
		JobType:      finding.JobType,
		TargetType:   finding.TargetType,
		TargetKey:    finding.TargetKey,
		TargetName:   finding.TargetName,
		Severity:     finding.Severity,
		Category:     finding.Category,
		Title:        finding.Title,
		Description:  finding.Description,
		Action:       finding.Action,
		Reason:       finding.Reason,
		SavingCPU:    finding.SavingCPU,
		SavingMemory: finding.SavingMemory,
		SavingCost:   finding.SavingCost,
		Details:      finding.Details,
		CreatedAt:    finding.CreatedAt,
	}
}

// ToDTOList 批量转换
func (m *AnalysisFindingMapper) ToDTOList(findings []storage.AnalysisFinding) []response.AnalysisFindingResponse {
	if len(findings) == 0 {
		return []response.AnalysisFindingResponse{}
	}

	result := make([]response.AnalysisFindingResponse, len(findings))
	for i := range findings {
		if dto := m.ToDTO(&findings[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}

// ToListResponse 转换为列表响应
func (m *AnalysisFindingMapper) ToListResponse(findings []storage.AnalysisFinding, total int) response.AnalysisFindingListResponse {
	return response.AnalysisFindingListResponse{
		Total: total,
		Items: m.ToDTOList(findings),
	}
}

// ToStatsResponse 转换为统计响应
func (m *AnalysisFindingMapper) ToStatsResponse(
	total int64,
	bySeverity, byCategory, byJobType map[string]int64,
	totalSavingCPU, totalSavingMemory int64,
) response.AnalysisFindingStatsResponse {
	return response.AnalysisFindingStatsResponse{
		Total:             total,
		BySeverity:        bySeverity,
		ByCategory:        byCategory,
		ByJobType:         byJobType,
		TotalSavingCPU:    totalSavingCPU,
		TotalSavingMemory: totalSavingMemory,
	}
}
