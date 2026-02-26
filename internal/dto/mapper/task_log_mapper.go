// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"justfit/internal/dto/response"
	"justfit/internal/storage"
)

// TaskLogMapper 任务日志数据映射器
type TaskLogMapper struct{}

// NewTaskLogMapper 创建任务日志映射器
func NewTaskLogMapper() *TaskLogMapper {
	return &TaskLogMapper{}
}

// ToDTO 转换为响应 DTO
func (m *TaskLogMapper) ToDTO(log *storage.TaskLog) *response.TaskLogResponse {
	if log == nil {
		return nil
	}

	return &response.TaskLogResponse{
		ID:        log.ID,
		TaskID:    log.TaskID,
		JobID:     log.JobID,
		Operation: log.Operation,
		Category:  log.Category,
		Title:     log.Title,
		Message:   log.Message,
		Config:    log.Config,
		Result:    log.Result,
		Duration:  log.Duration,
		UserID:    log.UserID,
		IPAddress: log.IPAddress,
		CreatedAt: log.CreatedAt,
	}
}

// ToDTOList 批量转换
func (m *TaskLogMapper) ToDTOList(logs []storage.TaskLog) []response.TaskLogResponse {
	if len(logs) == 0 {
		return []response.TaskLogResponse{}
	}

	result := make([]response.TaskLogResponse, len(logs))
	for i := range logs {
		if dto := m.ToDTO(&logs[i]); dto != nil {
			result[i] = *dto
		}
	}
	return result
}

// ToListResponse 转换为列表响应
func (m *TaskLogMapper) ToListResponse(logs []storage.TaskLog, total int) response.TaskLogListResponse {
	return response.TaskLogListResponse{
		Total: total,
		Items: m.ToDTOList(logs),
	}
}
