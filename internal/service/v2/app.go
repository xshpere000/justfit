// Package v2 提供新版本的应用服务层
// 使用 DTO 模式和统一的日志/错误处理
package v2

import (
	"context"

	"justfit/internal/connector"
	"justfit/internal/dto/mapper"
	"justfit/internal/dto/request"
	"justfit/internal/dto/response"
	apperrors "justfit/internal/errors"
	"justfit/internal/logger"
	"justfit/internal/security"
	"justfit/internal/storage"
	"justfit/internal/task"
)

// Services 应用服务集合
type Services struct {
	Connection *ConnectionService
	Resource   *ResourceService
	Task       *TaskService
}

// NewServices 创建所有服务
func NewServices(
	ctx context.Context,
	repos *storage.Repositories,
	connMgr *connector.ConnectorManager,
	credentialMgr *security.CredentialManager,
	taskScheduler *task.Scheduler,
	taskLogger *task.Logger,
) *Services {
	return &Services{
		Connection: NewConnectionService(ctx, repos, connMgr, credentialMgr),
		Resource:   NewResourceService(ctx, repos),
		Task:       NewTaskService(ctx, repos, taskScheduler, taskLogger),
	}
}

// TaskService 任务服务
type TaskService struct {
	ctx           context.Context
	repos         *storage.Repositories
	taskScheduler *task.Scheduler
	taskLogger    *task.Logger
	mapper        *mapper.TaskMapper
	log           logger.Logger
}

// NewTaskService 创建任务服务
func NewTaskService(
	ctx context.Context,
	repos *storage.Repositories,
	taskScheduler *task.Scheduler,
	taskLogger *task.Logger,
) *TaskService {
	return &TaskService{
		ctx:           ctx,
		repos:         repos,
		taskScheduler: taskScheduler,
		taskLogger:    taskLogger,
		mapper:        mapper.NewTaskMapper(),
		log:           logger.With(logger.Str("service", "task")),
	}
}

// List 获取任务列表
func (s *TaskService) List(status string, limit, offset int) ([]response.TaskResponse, error) {
	s.log.Debug("获取任务列表", logger.String("status", status), logger.Int("limit", limit))

	var taskStatus task.TaskStatus
	if status != "" {
		taskStatus = task.TaskStatus(status)
	}

	tasks, err := s.taskScheduler.List(taskStatus, limit, offset)
	if err != nil {
		s.log.Error("获取任务列表失败", logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取任务列表失败")
	}

	result := s.mapper.ToDTOList(tasks)
	s.log.Info("获取任务列表成功", logger.Int("count", len(result)))
	return result, nil
}

// GetByID 获取任务详情
func (s *TaskService) GetByID(id uint) (*response.TaskDetailResponse, error) {
	s.log.Debug("获取任务详情", logger.Uint("id", id))

	t, err := s.taskScheduler.Get(id)
	if err != nil {
		s.log.Error("获取任务失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrTaskNotFound
	}

	// 获取分析结果
	analysisResults := map[string]bool{
		"zombie":    false,
		"rightsize": false,
		"tidal":     false,
		"health":    false,
	}

	if analysisRows, analysisErr := s.repos.TaskAnalysisJob.ListByTaskID(id); analysisErr == nil {
		for _, row := range analysisRows {
			switch row.JobType {
			case "zombie":
				analysisResults["zombie"] = true
			case "rightsize":
				analysisResults["rightsize"] = true
			case "tidal":
				analysisResults["tidal"] = true
			case "health":
				analysisResults["health"] = true
			}
		}
	}

	return s.mapper.ToDetailDTO(t, analysisResults), nil
}

// GetLogs 获取任务日志
func (s *TaskService) GetLogs(id uint, limit int) ([]response.TaskLogEntry, error) {
	s.log.Debug("获取任务日志", logger.Uint("id", id), logger.Int("limit", limit))

	if s.taskLogger == nil {
		return []response.TaskLogEntry{}, nil
	}

	entries := s.taskLogger.GetEntries(id, limit)
	return s.mapper.ToLogEntryList(entries), nil
}

// Stop 停止任务
func (s *TaskService) Stop(id uint) error {
	s.log.Info("停止任务", logger.Uint("id", id))
	return s.taskScheduler.Cancel(id)
}

// Retry 重试任务
func (s *TaskService) Retry(id uint) (uint, error) {
	s.log.Info("重试任务", logger.Uint("id", id))

	oldTask, err := s.taskScheduler.Get(id)
	if err != nil {
		s.log.Error("获取任务失败", logger.Uint("id", id), logger.Err(err))
		return 0, apperrors.ErrTaskNotFound
	}

	// 创建新任务
	taskName := oldTask.Name + " (重试)"
	newTask, err := s.taskScheduler.Create(oldTask.Type, taskName, oldTask.Config)
	if err != nil {
		s.log.Error("创建任务失败", logger.Err(err))
		return 0, apperrors.ErrInternalError.Wrap(err, "创建任务失败")
	}

	// 提交执行
	go func() {
		_ = s.taskScheduler.Submit(s.ctx, newTask.ID)
	}()

	s.log.Info("重试任务成功", logger.Uint("old_id", id), logger.Uint("new_id", newTask.ID))
	return newTask.ID, nil
}

// CreateCollection 创建采集任务
func (s *TaskService) CreateCollection(req *request.CreateCollectionRequest) (uint, error) {
	s.log.Info("创建采集任务", logger.Uint("connection_id", req.ConnectionID))

	taskConfig := map[string]interface{}{
		"connection_id":   req.ConnectionID,
		"connection_name": req.ConnectionName,
		"platform":        req.Platform,
		"data_types":      req.DataTypes,
		"metrics_days":    req.MetricsDays,
		"vmCount":         req.VMCount,
		"selectedVMs":     req.SelectedVMs,
	}

	taskName := "采集任务"
	t, err := s.taskScheduler.Create(task.TypeCollection, taskName, taskConfig)
	if err != nil {
		s.log.Error("创建任务失败", logger.Err(err))
		return 0, apperrors.ErrInternalError.Wrap(err, "创建任务失败")
	}

	// 提交执行
	go func() {
		_ = s.taskScheduler.Submit(s.ctx, t.ID)
	}()

	s.log.Info("创建采集任务成功", logger.Uint("task_id", t.ID))
	return t.ID, nil
}

// CreateAnalysis 创建分析任务
func (s *TaskService) CreateAnalysis(req *request.CreateAnalysisRequest) (uint, error) {
	s.log.Info("创建分析任务", logger.String("type", req.AnalysisType), logger.Uint("connection_id", req.ConnectionID))

	// 前端类型到后端类型的映射
	typeMapping := map[string]string{
		"zombie":    "zombie",
		"rightsize": "rightsize",
		"health":    "health",
	}

	backendType := req.AnalysisType
	if mapped, ok := typeMapping[req.AnalysisType]; ok {
		backendType = mapped
	}

	taskConfig := map[string]interface{}{
		"analysis_type": backendType,
		"connection_id": req.ConnectionID,
	}

	// 合并用户配置
	for k, v := range req.Config {
		taskConfig[k] = v
	}

	taskName := "分析任务 - " + backendType
	t, err := s.taskScheduler.Create(task.TypeAnalysis, taskName, taskConfig)
	if err != nil {
		s.log.Error("创建任务失败", logger.Err(err))
		return 0, apperrors.ErrInternalError.Wrap(err, "创建任务失败")
	}

	// 提交执行
	go func() {
		_ = s.taskScheduler.Submit(s.ctx, t.ID)
	}()

	s.log.Info("创建分析任务成功", logger.Uint("task_id", t.ID))
	return t.ID, nil
}
