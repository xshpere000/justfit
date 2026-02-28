// Package analyzer 提供评估模式配置
package analyzer

// AnalysisMode 分析模式
type AnalysisMode string

const (
	ModeSafe       AnalysisMode = "safe"       // 安全模式
	ModeSaving     AnalysisMode = "saving"     // 节省模式
	ModeAggressive AnalysisMode = "aggressive" // 激进模式
	ModeCustom     AnalysisMode = "custom"     // 自定义模式
)

// AnalysisConfig 完整的分析配置
type AnalysisConfig struct {
	// 僵尸VM配置
	ZombieVM *ZombieVMConfig `json:"zombieVM,omitempty"`

	// RightSize配置
	RightSize *RightSizeConfig `json:"rightSize,omitempty"`

	// 潮汐检测配置
	Tidal *TidalConfig `json:"tidal,omitempty"`

	// 健康评分配置
	Health *HealthConfig `json:"health,omitempty"`
}

// GetModeConfig 获取指定模式的预设配置
func GetModeConfig(mode AnalysisMode) *AnalysisConfig {
	switch mode {
	case ModeSafe:
		return safeModeConfig()
	case ModeSaving:
		return savingModeConfig()
	case ModeAggressive:
		return aggressiveModeConfig()
	case ModeCustom:
		// 自定义模式返回空配置，由用户填充
		return &AnalysisConfig{}
	default:
		return safeModeConfig()
	}
}

// safeModeConfig 安全模式配置
func safeModeConfig() *AnalysisConfig {
	return &AnalysisConfig{
		ZombieVM: &ZombieVMConfig{
			AnalysisDays:     30,
			CPUThreshold:     5.0,
			MemoryThreshold:  10.0,
			IOThreshold:      10.0,
			NetworkThreshold: 10.0,
			MinConfidence:    80.0,
		},
		RightSize: &RightSizeConfig{
			AnalysisDays: 7,
			BufferRatio:  1.3,
			P95Threshold: 95.0,
			SmallMargin:  0.4,
			LargeMargin:  0.6,
		},
		Tidal: &TidalConfig{
			AnalysisDays: 30,
			MinStability: 70.0,
			MinVariation: 40.0,
		},
		Health: &HealthConfig{
			ResourceBalanceWeight: 0.4,
			OvercommitRiskWeight:  0.3,
			HotspotWeight:         0.3,
		},
	}
}

// savingModeConfig 节省模式配置
func savingModeConfig() *AnalysisConfig {
	return &AnalysisConfig{
		ZombieVM: &ZombieVMConfig{
			AnalysisDays:     14,
			CPUThreshold:     10.0,
			MemoryThreshold:  20.0,
			IOThreshold:      20.0,
			NetworkThreshold: 20.0,
			MinConfidence:    60.0,
		},
		RightSize: &RightSizeConfig{
			AnalysisDays: 7,
			BufferRatio:  1.2,
			P95Threshold: 90.0,
			SmallMargin:  0.3,
			LargeMargin:  0.5,
		},
		Tidal: &TidalConfig{
			AnalysisDays: 21,
			MinStability: 60.0,
			MinVariation: 30.0,
		},
		Health: &HealthConfig{
			ResourceBalanceWeight: 0.4,
			OvercommitRiskWeight:  0.3,
			HotspotWeight:         0.3,
		},
	}
}

// aggressiveModeConfig 激进模式配置
func aggressiveModeConfig() *AnalysisConfig {
	return &AnalysisConfig{
		ZombieVM: &ZombieVMConfig{
			AnalysisDays:     7,
			CPUThreshold:     15.0,
			MemoryThreshold:  30.0,
			IOThreshold:      30.0,
			NetworkThreshold: 30.0,
			MinConfidence:    50.0,
		},
		RightSize: &RightSizeConfig{
			AnalysisDays: 5,
			BufferRatio:  1.1,
			P95Threshold: 85.0,
			SmallMargin:  0.2,
			LargeMargin:  0.4,
		},
		Tidal: &TidalConfig{
			AnalysisDays: 14,
			MinStability: 50.0,
			MinVariation: 20.0,
		},
		Health: &HealthConfig{
			ResourceBalanceWeight: 0.3,
			OvercommitRiskWeight:  0.3,
			HotspotWeight:         0.4,
		},
	}
}

// GetEffectiveConfig 获取有效的分析配置
// 1. 如果是预设模式，返回预设配置
// 2. 如果是自定义模式，合并用户配置和默认配置
func GetEffectiveConfig(mode AnalysisMode, customConfig *AnalysisConfig) *AnalysisConfig {
	baseConfig := GetModeConfig(mode)

	if mode != ModeCustom || customConfig == nil {
		return baseConfig
	}

	// 合并自定义配置
	result := &AnalysisConfig{}

	// 复制基础配置
	if baseConfig.ZombieVM != nil {
		result.ZombieVM = baseConfig.ZombieVM
	}
	if baseConfig.RightSize != nil {
		result.RightSize = baseConfig.RightSize
	}
	if baseConfig.Tidal != nil {
		result.Tidal = baseConfig.Tidal
	}
	if baseConfig.Health != nil {
		result.Health = baseConfig.Health
	}

	// 覆盖自定义配置
	if customConfig.ZombieVM != nil {
		result.ZombieVM = customConfig.ZombieVM
	}
	if customConfig.RightSize != nil {
		result.RightSize = customConfig.RightSize
	}
	if customConfig.Tidal != nil {
		result.Tidal = customConfig.Tidal
	}
	if customConfig.Health != nil {
		result.Health = customConfig.Health
	}

	return result
}

// GetModeInfo 获取模式信息
func GetModeInfo(mode AnalysisMode) (name, description string) {
	switch mode {
	case ModeSafe:
		return "安全模式", "保守识别，适合生产环境谨慎操作。使用较长周期(30天)、低阈值(5% CPU)、高置信度(80%)，确保识别准确。"
	case ModeSaving:
		return "节省模式", "平衡风险与成本，推荐大多数场景。使用中等周期(14天)、中等阈值，在准确性和节省之间取得平衡。"
	case ModeAggressive:
		return "激进模式", "最大化资源利用率。使用短周期(7天)、高阈值(15% CPU)、低置信度(50%)，捕捉更多优化机会。"
	case ModeCustom:
		return "自定义模式", "根据业务特点精调参数。可以手动调整各项阈值和分析天数。"
	default:
		return "未知模式", ""
	}
}

// ListAllModes 列出所有可用模式
func ListAllModes() []AnalysisMode {
	return []AnalysisMode{ModeSafe, ModeSaving, ModeAggressive, ModeCustom}
}

// IsValidMode 验证模式是否有效
func IsValidMode(mode string) bool {
	switch AnalysisMode(mode) {
	case ModeSafe, ModeSaving, ModeAggressive, ModeCustom:
		return true
	default:
		return false
	}
}
