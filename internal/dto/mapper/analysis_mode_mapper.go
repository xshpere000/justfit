// Package mapper 提供数据映射器
package mapper

import (
	"encoding/json"

	"justfit/internal/analyzer"
	"justfit/internal/dto/request"
	"justfit/internal/dto/response"
)

// AnalysisModeMapper 分析模式映射器
type AnalysisModeMapper struct{}

// NewAnalysisModeMapper 创建分析模式映射器
func NewAnalysisModeMapper() *AnalysisModeMapper {
	return &AnalysisModeMapper{}
}

// ToModeResponse 将分析模式转换为响应DTO
func (m *AnalysisModeMapper) ToModeResponse(mode analyzer.AnalysisMode, config *analyzer.AnalysisConfig) *response.AnalysisModeResponse {
	name, description := analyzer.GetModeInfo(mode)

	// 构建所有可用模式列表
	var availableModes []response.AnalysisModeInfo
	for _, modeType := range analyzer.ListAllModes() {
		modeName, modeDesc := analyzer.GetModeInfo(modeType)
		availableModes = append(availableModes, response.AnalysisModeInfo{
			Mode:        string(modeType),
			Name:        modeName,
			Description: modeDesc,
		})
	}

	return &response.AnalysisModeResponse{
		Mode:           string(mode),
		ModeName:       name,
		Description:    description,
		Config:         m.configToResponse(config),
		AvailableModes: availableModes,
	}
}

// configToResponse 将内部配置转换为响应DTO
func (m *AnalysisModeMapper) configToResponse(config *analyzer.AnalysisConfig) *response.AnalysisConfig {
	if config == nil {
		return nil
	}

	result := &response.AnalysisConfig{}

	if config.ZombieVM != nil {
		result.ZombieVM = &response.ZombieVMConfig{
			AnalysisDays:     config.ZombieVM.AnalysisDays,
			CPUThreshold:     config.ZombieVM.CPUThreshold,
			MemoryThreshold:  config.ZombieVM.MemoryThreshold,
			IOThreshold:      config.ZombieVM.IOThreshold,
			NetworkThreshold: config.ZombieVM.NetworkThreshold,
			MinConfidence:    config.ZombieVM.MinConfidence,
		}
	}

	if config.RightSize != nil {
		result.RightSize = &response.RightSizeConfig{
			AnalysisDays: config.RightSize.AnalysisDays,
			BufferRatio:  config.RightSize.BufferRatio,
			P95Threshold: config.RightSize.P95Threshold,
			SmallMargin:  config.RightSize.SmallMargin,
			LargeMargin:  config.RightSize.LargeMargin,
		}
	}

	if config.Tidal != nil {
		result.Tidal = &response.TidalConfig{
			AnalysisDays: config.Tidal.AnalysisDays,
			MinStability: config.Tidal.MinStability,
			MinVariation: config.Tidal.MinVariation,
		}
	}

	if config.Health != nil {
		result.Health = &response.HealthConfig{
			ResourceBalanceWeight: config.Health.ResourceBalanceWeight,
			OvercommitRiskWeight:  config.Health.OvercommitRiskWeight,
			HotspotWeight:         config.Health.HotspotWeight,
		}
	}

	return result
}

// RequestToConfig 将请求DTO转换为内部配置
func (m *AnalysisModeMapper) RequestToConfig(req *request.AnalysisConfig) *analyzer.AnalysisConfig {
	if req == nil {
		return nil
	}

	result := &analyzer.AnalysisConfig{}

	if req.ZombieVM != nil {
		result.ZombieVM = &analyzer.ZombieVMConfig{
			AnalysisDays:     req.ZombieVM.AnalysisDays,
			CPUThreshold:     req.ZombieVM.CPUThreshold,
			MemoryThreshold:  req.ZombieVM.MemoryThreshold,
			IOThreshold:      req.ZombieVM.IOThreshold,
			NetworkThreshold: req.ZombieVM.NetworkThreshold,
			MinConfidence:    req.ZombieVM.MinConfidence,
		}
	}

	if req.RightSize != nil {
		result.RightSize = &analyzer.RightSizeConfig{
			AnalysisDays: req.RightSize.AnalysisDays,
			BufferRatio:  req.RightSize.BufferRatio,
			P95Threshold: req.RightSize.P95Threshold,
			SmallMargin:  req.RightSize.SmallMargin,
			LargeMargin:  req.RightSize.LargeMargin,
		}
	}

	if req.Tidal != nil {
		result.Tidal = &analyzer.TidalConfig{
			AnalysisDays: req.Tidal.AnalysisDays,
			MinStability: req.Tidal.MinStability,
			MinVariation: req.Tidal.MinVariation,
		}
	}

	if req.Health != nil {
		result.Health = &analyzer.HealthConfig{
			ResourceBalanceWeight: req.Health.ResourceBalanceWeight,
			OvercommitRiskWeight:  req.Health.OvercommitRiskWeight,
			HotspotWeight:         req.Health.HotspotWeight,
		}
	}

	return result
}

// ConfigToJSON 将配置序列化为JSON
func (m *AnalysisModeMapper) ConfigToJSON(config *analyzer.AnalysisConfig) (string, error) {
	if config == nil {
		return "", nil
	}

	data, err := json.Marshal(config)
	if err != nil {
		return "", err
	}

	return string(data), nil
}

// JSONToConfig 从JSON反序列化配置
func (m *AnalysisModeMapper) JSONToConfig(jsonStr string) (*analyzer.AnalysisConfig, error) {
	if jsonStr == "" {
		return nil, nil
	}

	var config analyzer.AnalysisConfig
	err := json.Unmarshal([]byte(jsonStr), &config)
	if err != nil {
		return nil, err
	}

	return &config, nil
}
