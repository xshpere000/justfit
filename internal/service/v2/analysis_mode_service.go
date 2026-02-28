// Package v2 提供新版本的服务层，使用 DTO 模式
package v2

import (
	"context"
	"encoding/json"

	"justfit/internal/analyzer"
	"justfit/internal/dto/mapper"
	"justfit/internal/dto/request"
	"justfit/internal/dto/response"
	apperrors "justfit/internal/errors"
	"justfit/internal/logger"
	"justfit/internal/storage"
)

// AnalysisModeService 评估模式服务
type AnalysisModeService struct {
	ctx    context.Context
	repos  *storage.Repositories
	mapper *mapper.AnalysisModeMapper
	log    logger.Logger
}

// NewAnalysisModeService 创建评估模式服务
func NewAnalysisModeService(
	ctx context.Context,
	repos *storage.Repositories,
) *AnalysisModeService {
	return &AnalysisModeService{
		ctx:    ctx,
		repos:  repos,
		mapper: mapper.NewAnalysisModeMapper(),
		log:    logger.With(logger.Str("service", "analysis_mode")),
	}
}

// GetAnalysisMode 获取任务的当前评估模式
func (s *AnalysisModeService) GetAnalysisMode(taskID uint) (*response.AnalysisModeResponse, error) {
	s.log.Debug("获取评估模式", logger.Uint("task_id", taskID))

	// 获取任务
	task, err := s.repos.AssessmentTask.GetByID(taskID)
	if err != nil {
		s.log.Error("获取任务失败", logger.Uint("task_id", taskID), logger.Err(err))
		return nil, apperrors.ErrTaskNotFound
	}

	// 解析模式
	mode := analyzer.AnalysisMode(task.AnalysisMode)
	if mode == "" {
		mode = analyzer.ModeSafe // 默认安全模式
	}

	// 解析自定义配置
	var customConfig *analyzer.AnalysisConfig
	if task.AnalysisConfig != "" {
		customConfig, err = s.mapper.JSONToConfig(task.AnalysisConfig)
		if err != nil {
			s.log.Warn("解析自定义配置失败", logger.Uint("task_id", taskID), logger.Err(err))
		}
	}

	// 获取有效配置
	config := analyzer.GetEffectiveConfig(mode, customConfig)

	return s.mapper.ToModeResponse(mode, config), nil
}

// SetAnalysisMode 设置任务的评估模式
func (s *AnalysisModeService) SetAnalysisMode(taskID uint, req *request.SetAnalysisModeRequest) error {
	s.log.Debug("设置评估模式", logger.Uint("task_id", taskID), logger.String("mode", req.Mode))

	// 验证模式
	if !analyzer.IsValidMode(req.Mode) {
		return apperrors.ErrInvalidInput.Wrap(nil, "无效的评估模式")
	}

	mode := analyzer.AnalysisMode(req.Mode)

	// 获取任务
	task, err := s.repos.AssessmentTask.GetByID(taskID)
	if err != nil {
		s.log.Error("获取任务失败", logger.Uint("task_id", taskID), logger.Err(err))
		return apperrors.ErrTaskNotFound
	}

	// 更新模式
	task.AnalysisMode = req.Mode

	// 如果是自定义模式，保存自定义配置
	if mode == analyzer.ModeCustom && req.Config != nil {
		config := s.mapper.RequestToConfig(req.Config)
		jsonConfig, err := s.mapper.ConfigToJSON(config)
		if err != nil {
			s.log.Error("序列化配置失败", logger.Err(err))
			return apperrors.ErrInternalError.Wrap(err, "序列化配置失败")
		}
		task.AnalysisConfig = jsonConfig
	} else {
		// 非自定义模式，清空自定义配置
		task.AnalysisConfig = ""
	}

	// 保存
	if err := s.repos.AssessmentTask.Update(task); err != nil {
		s.log.Error("更新任务失败", logger.Uint("task_id", taskID), logger.Err(err))
		return apperrors.ErrInternalError.Wrap(err, "更新任务失败")
	}

	s.log.Info("评估模式已更新", logger.Uint("task_id", taskID), logger.String("mode", req.Mode))
	return nil
}

// ListAnalysisModes 列出所有可用的评估模式
func (s *AnalysisModeService) ListAnalysisModes() ([]response.AnalysisModeInfo, error) {
	s.log.Debug("列出所有评估模式")

	var result []response.AnalysisModeInfo
	for _, mode := range analyzer.ListAllModes() {
		name, description := analyzer.GetModeInfo(mode)
		result = append(result, response.AnalysisModeInfo{
			Mode:        string(mode),
			Name:        name,
			Description: description,
		})
	}

	return result, nil
}

// GetEffectiveConfigForTask 获取任务的有效分析配置
// 用于分析引擎执行分析时获取正确的配置
func (s *AnalysisModeService) GetEffectiveConfigForTask(taskID uint) (*analyzer.AnalysisConfig, error) {
	s.log.Debug("获取任务有效配置", logger.Uint("task_id", taskID))

	// 获取任务
	task, err := s.repos.AssessmentTask.GetByID(taskID)
	if err != nil {
		s.log.Error("获取任务失败", logger.Uint("task_id", taskID), logger.Err(err))
		return nil, apperrors.ErrTaskNotFound
	}

	// 解析模式
	mode := analyzer.AnalysisMode(task.AnalysisMode)
	if mode == "" {
		mode = analyzer.ModeSafe
	}

	// 解析自定义配置
	var customConfig *analyzer.AnalysisConfig
	if task.AnalysisConfig != "" {
		customConfig, err = s.mapper.JSONToConfig(task.AnalysisConfig)
		if err != nil {
			s.log.Warn("解析自定义配置失败", logger.Uint("task_id", taskID), logger.Err(err))
		}
	}

	// 获取有效配置
	return analyzer.GetEffectiveConfig(mode, customConfig), nil
}

// GetAnalysisConfigAsJSON 获取任务的配置JSON（用于调试）
func (s *AnalysisModeService) GetAnalysisConfigAsJSON(taskID uint) (string, error) {
	config, err := s.GetEffectiveConfigForTask(taskID)
	if err != nil {
		return "", err
	}

	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return "", err
	}

	return string(data), nil
}
