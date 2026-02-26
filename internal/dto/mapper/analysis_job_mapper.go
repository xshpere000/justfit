// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// AnalysisJobMapper 分析子任务数据映射器
type AnalysisJobMapper struct{}

// NewAnalysisJobMapper 创建分析子任务映射器
func NewAnalysisJobMapper() *AnalysisJobMapper {
	return &AnalysisJobMapper{}
}

// ToDTO 转换为响应 DTO
func (m *AnalysisJobMapper) ToDTO(job *storage.TaskAnalysisJob) *response.TaskAnalysisJobResponse {
	if job == nil {
		return nil
	}

	return &response.TaskAnalysisJobResponse{
		ID:          job.ID,
		TaskID:      job.TaskID,
		JobType:     job.JobType,
		Status:      job.Status,
		Progress:    job.Progress,
		Error:       job.Error,
		ResultCount: job.ResultCount,
		StartedAt:   job.StartedAt,
		CompletedAt: job.CompletedAt,
		CreatedAt:   job.CreatedAt,
	}
}

// ToDTOList 批量转换
func (m *AnalysisJobMapper) ToDTOList(jobs []storage.TaskAnalysisJob) []response.TaskAnalysisJobResponse {
	if len(jobs) == 0 {
		return []response.TaskAnalysisJobResponse{}
	}

	result := make([]response.TaskAnalysisJobResponse, len(jobs))
	for i := range jobs {
		if dto := m.ToDTO(&jobs[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}

// ToListResponse 转换为列表响应
func (m *AnalysisJobMapper) ToListResponse(jobs []storage.TaskAnalysisJob, total int) response.TaskAnalysisJobListResponse {
	return response.TaskAnalysisJobListResponse{
		Total: total,
		Items: m.ToDTOList(jobs),
	}
}
