// Package request 提供请求数据传输对象
package request

// SetAnalysisModeRequest 设置评估模式请求
type SetAnalysisModeRequest struct {
	Mode   string          `json:"mode" validate:"required,oneof=safe saving aggressive custom"`
	Config *AnalysisConfig `json:"config"`
}

// AnalysisConfig 分析配置
type AnalysisConfig struct {
	ZombieVM  *ZombieVMConfig  `json:"zombieVM,omitempty"`
	RightSize *RightSizeConfig `json:"rightSize,omitempty"`
	Tidal     *TidalConfig     `json:"tidal,omitempty"`
	Health    *HealthConfig    `json:"health,omitempty"`
}

// ZombieVMConfig 僵尸VM配置
type ZombieVMConfig struct {
	AnalysisDays     int     `json:"analysisDays" validate:"min=1,max=90"`
	CPUThreshold     float64 `json:"cpuThreshold" validate:"min=0,max=100"`
	MemoryThreshold  float64 `json:"memoryThreshold" validate:"min=0,max=100"`
	IOThreshold      float64 `json:"ioThreshold" validate:"min=0,max=1000"`
	NetworkThreshold float64 `json:"networkThreshold" validate:"min=0,max=1000"`
	MinConfidence    float64 `json:"minConfidence" validate:"min=0,max=100"`
}

// RightSizeConfig RightSize配置
type RightSizeConfig struct {
	AnalysisDays int     `json:"analysisDays" validate:"min=1,max=30"`
	BufferRatio  float64 `json:"bufferRatio" validate:"min=1.0,max=2.0"`
	P95Threshold float64 `json:"p95Threshold" validate:"min=50,max=99"`
	SmallMargin  float64 `json:"smallMargin" validate:"min=0,max=1"`
	LargeMargin  float64 `json:"largeMargin" validate:"min=0,max=1"`
}

// TidalConfig 潮汐配置
type TidalConfig struct {
	AnalysisDays int     `json:"analysisDays" validate:"min=1,max=90"`
	MinStability float64 `json:"minStability" validate:"min=0,max=100"`
	MinVariation float64 `json:"minVariation" validate:"min=0,max=100"`
}

// HealthConfig 健康评分配置
type HealthConfig struct {
	ResourceBalanceWeight float64 `json:"resourceBalanceWeight" validate:"min=0,max=1"`
	OvercommitRiskWeight  float64 `json:"overcommitRiskWeight" validate:"min=0,max=1"`
	HotspotWeight         float64 `json:"hotspotWeight" validate:"min=0,max=1"`
}
