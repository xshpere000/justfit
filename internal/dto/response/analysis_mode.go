// Package response 提供响应数据传输对象
package response

// AnalysisModeResponse 评估模式响应
type AnalysisModeResponse struct {
	Mode           string             `json:"mode"`
	ModeName       string             `json:"modeName"`
	Description    string             `json:"description"`
	Config         *AnalysisConfig    `json:"config"`
	AvailableModes []AnalysisModeInfo `json:"availableModes"`
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
	AnalysisDays     int     `json:"analysisDays"`
	CPUThreshold     float64 `json:"cpuThreshold"`
	MemoryThreshold  float64 `json:"memoryThreshold"`
	IOThreshold      float64 `json:"ioThreshold"`
	NetworkThreshold float64 `json:"networkThreshold"`
	MinConfidence    float64 `json:"minConfidence"`
}

// RightSizeConfig RightSize配置
type RightSizeConfig struct {
	AnalysisDays int     `json:"analysisDays"`
	BufferRatio  float64 `json:"bufferRatio"`
	P95Threshold float64 `json:"p95Threshold"`
	SmallMargin  float64 `json:"smallMargin"`
	LargeMargin  float64 `json:"largeMargin"`
}

// TidalConfig 潮汐配置
type TidalConfig struct {
	AnalysisDays int     `json:"analysisDays"`
	MinStability float64 `json:"minStability"`
	MinVariation float64 `json:"minVariation"`
}

// HealthConfig 健康评分配置
type HealthConfig struct {
	ResourceBalanceWeight float64 `json:"resourceBalanceWeight"`
	OvercommitRiskWeight  float64 `json:"overcommitRiskWeight"`
	HotspotWeight         float64 `json:"hotspotWeight"`
}

// AnalysisModeInfo 模式信息
type AnalysisModeInfo struct {
	Mode        string `json:"mode"`
	Name        string `json:"name"`
	Description string `json:"description"`
}
