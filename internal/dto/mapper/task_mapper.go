// Package mapper 提供数据模型到 DTO 的映射器
package mapper

import (
	"time"

	"justfit/internal/dto/response"
	"justfit/internal/task"
)

// TaskMapper 任务数据映射器
type TaskMapper struct{}

// NewTaskMapper 创建任务映射器
func NewTaskMapper() *TaskMapper {
	return &TaskMapper{}
}

// ToDTO 转换为响应 DTO
func (m *TaskMapper) ToDTO(t *task.Task) *response.TaskResponse {
	if t == nil {
		return nil
	}

	dto := &response.TaskResponse{
		ID:        t.ID,
		Type:      string(t.Type),
		Name:      t.Name,
		Status:    string(t.Status),
		Progress:  int(t.Progress * 100),
		Error:     t.Error,
		CreatedAt: t.CreatedAt,
		StartedAt: t.StartedAt,
		CompletedAt: func() *time.Time {
			if t.CompletedAt != nil && !t.CompletedAt.IsZero() {
				return t.CompletedAt
			}
			return nil
		}(),
	}

	// 计算执行时长
	if t.StartedAt != nil {
		endTime := time.Now()
		if t.CompletedAt != nil && !t.CompletedAt.IsZero() {
			endTime = *t.CompletedAt
		}
		dto.DurationMs = endTime.Sub(*t.StartedAt).Milliseconds()
	}

	// 从配置中提取扩展信息
	if connectionID, ok := t.Config["connection_id"].(uint); ok {
		dto.ConnectionID = connectionID
	}
	if connectionName, ok := t.Config["connection_name"].(string); ok {
		dto.ConnectionName = connectionName
	}
	if platform, ok := t.Config["platform"].(string); ok {
		dto.Platform = platform
	}
	if totalVMs, ok := t.Config["total_vms"].(int); ok {
		dto.TotalVMs = int32(totalVMs)
	}

	// 从结果中提取已采集数量
	if t.Result != nil {
		if vms, ok := t.Result["vms"].(int); ok {
			dto.CollectedVMs = int32(vms)
		}
	}

	return dto
}

// ToDetailDTO 转换为详情响应 DTO
func (m *TaskMapper) ToDetailDTO(t *task.Task, analysisResults map[string]bool) *response.TaskDetailResponse {
	if t == nil {
		return nil
	}

	base := m.ToDTO(t)
	if base == nil {
		return nil
	}

	return &response.TaskDetailResponse{
		TaskResponse:    *base,
		CurrentStep:     getCurrentStep(t.Status),
		Config:          t.Config,
		Result:          t.Result,
		AnalysisResults: analysisResults,
	}
}

// ToDTOList 批量转换
func (m *TaskMapper) ToDTOList(tasks []*task.Task) []response.TaskResponse {
	if len(tasks) == 0 {
		return []response.TaskResponse{}
	}

	result := make([]response.TaskResponse, len(tasks))
	for i := range tasks {
		if tasks[i] != nil {
			if dto := m.ToDTO(tasks[i]); dto != nil {
				result[i] = *dto
			}
		}
	}
	return result
}

// getCurrentStep 根据任务状态获取当前步骤描述
func getCurrentStep(status task.TaskStatus) string {
	switch status {
	case task.StatusPending:
		return "等待执行"
	case task.StatusRunning:
		return "执行中"
	case task.StatusCompleted:
		return "已完成"
	case task.StatusFailed:
		return "执行失败"
	case task.StatusCancelled:
		return "已取消"
	default:
		return "未知状态"
	}
}

// ToLogEntry 转换任务日志条目
func (m *TaskMapper) ToLogEntry(entry task.LogEntry) response.TaskLogEntry {
	return response.TaskLogEntry{
		Timestamp: entry.Timestamp.Format(time.RFC3339),
		Level:     string(entry.Level),
		Message:   entry.Message,
		Fields:    make(map[string]interface{}),
	}
}

// ToLogEntryList 批量转换日志条目
func (m *TaskMapper) ToLogEntryList(entries []task.LogEntry) []response.TaskLogEntry {
	if len(entries) == 0 {
		return []response.TaskLogEntry{}
	}

	result := make([]response.TaskLogEntry, len(entries))
	for i, e := range entries {
		result[i] = m.ToLogEntry(e)
	}
	return result
}
