// Package analyzer 提供分析结果存储功能
package analyzer

import (
	"encoding/json"
	"fmt"

	"justfit/internal/storage"
)

// ResultStorage 分析结果存储服务
type ResultStorage struct {
	repos *storage.Repositories
}

// NewResultStorage 创建结果存储服务
func NewResultStorage(repos *storage.Repositories) *ResultStorage {
	return &ResultStorage{repos: repos}
}

// SaveZombieVMResults 保存僵尸 VM 分析结果
func (rs *ResultStorage) SaveZombieVMResults(connectionID uint, results []ZombieVMResult) error {
	storageResults := make([]storage.AnalysisResult, len(results))

	for i, r := range results {
		data, err := json.Marshal(r)
		if err != nil {
			return fmt.Errorf("序列化数据失败: %w", err)
		}

		storageResults[i] = storage.AnalysisResult{
			AnalysisType:   "zombie_vm",
			TargetType:     "vm",
			TargetKey:      r.VMKey,
			TargetName:     r.VMName,
			Data:           string(data),
			Recommendation: r.Recommendation,
			SavedAmount:    estimateResourceSaving(r.CPUCount, r.MemoryMB, 0, 0),
		}
	}

	return rs.repos.AnalysisResult.BatchCreate(storageResults)
}

// SaveRightSizeResults 保存 Right Size 分析结果
func (rs *ResultStorage) SaveRightSizeResults(connectionID uint, results []RightSizeResult) error {
	storageResults := make([]storage.AnalysisResult, len(results))

	for i, r := range results {
		data, err := json.Marshal(r)
		if err != nil {
			return fmt.Errorf("序列化数据失败: %w", err)
		}

		storageResults[i] = storage.AnalysisResult{
			AnalysisType:   "right_size",
			TargetType:     "vm",
			TargetKey:      r.VMKey,
			TargetName:     r.VMName,
			Data:           string(data),
			Recommendation: fmt.Sprintf("%s: %d → %d vCPU, %d → %d MB RAM",
				r.AdjustmentType,
				r.CurrentCPU, r.RecommendedCPU,
				r.CurrentMemoryMB, r.RecommendedMemoryMB),
			SavedAmount: r.EstimatedSaving,
		}
	}

	return rs.repos.AnalysisResult.BatchCreate(storageResults)
}

// SaveTidalResults 保存潮汐分析结果
func (rs *ResultStorage) SaveTidalResults(connectionID uint, results []TidalResult) error {
	storageResults := make([]storage.AnalysisResult, len(results))

	for i, r := range results {
		data, err := json.Marshal(r)
		if err != nil {
			return fmt.Errorf("序列化数据失败: %w", err)
		}

		storageResults[i] = storage.AnalysisResult{
			AnalysisType:   "tidal",
			TargetType:     "vm",
			TargetKey:      r.VMKey,
			TargetName:     r.VMName,
			Data:           string(data),
			Recommendation: r.Recommendation,
			SavedAmount:    r.EstimatedSaving,
		}
	}

	return rs.repos.AnalysisResult.BatchCreate(storageResults)
}

// SaveHealthScoreResult 保存健康评分结果
func (rs *ResultStorage) SaveHealthScoreResult(result HealthScoreResult) error {
	data, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("序列化数据失败: %w", err)
	}

	// 合并所有风险项和建议
	recommendation := ""
	if len(result.RiskItems) > 0 {
		recommendation = "风险项: " + joinStrings(result.RiskItems, "; ")
	}
	if len(result.Recommendations) > 0 {
		if recommendation != "" {
			recommendation += "\n"
		}
		recommendation += "建议: " + joinStrings(result.Recommendations, "; ")
	}

	storageResult := storage.AnalysisResult{
		AnalysisType:   "health_score",
		TargetType:     "connection",
		TargetKey:      fmt.Sprintf("%d", result.ConnectionID),
		TargetName:     result.ConnectionName,
		Data:           string(data),
		Recommendation: recommendation,
		SavedAmount:    fmt.Sprintf("健康评分: %.0f", result.OverallScore),
	}

	return rs.repos.AnalysisResult.Create(&storageResult)
}

// CreateAlert 创建告警
func (rs *ResultStorage) CreateAlert(targetType, targetKey, targetName, alertType, severity, title, message string, data interface{}) error {
	dataJSON, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("序列化数据失败: %w", err)
	}

	alert := storage.Alert{
		TargetType: targetType,
		TargetKey:  targetKey,
		TargetName: targetName,
		AlertType:  alertType,
		Severity:   severity,
		Title:      title,
		Message:    message,
		Data:       string(dataJSON),
	}

	return rs.repos.Alert.Create(&alert)
}

// CreateAlerts 批量创建告警
func (rs *ResultStorage) CreateAlerts(alerts []storage.Alert) error {
	return rs.repos.Alert.BatchCreate(alerts)
}

// 辅助函数

func estimateResourceSaving(currentCPU, currentMem, recommendedCPU, recommendedMem int32) string {
	cpuSaving := currentCPU - recommendedCPU
	memSaving := currentMem - recommendedMem

	if cpuSaving <= 0 && memSaving <= 0 {
		return "无"
	}

	parts := make([]string, 0)
	if cpuSaving > 0 {
		parts = append(parts, fmt.Sprintf("%d vCPU", cpuSaving))
	}
	if memSaving > 0 {
		parts = append(parts, fmt.Sprintf("%d MB 内存", memSaving))
	}

	return joinStrings(parts, ", ")
}

func joinStrings(strs []string, sep string) string {
	if len(strs) == 0 {
		return ""
	}
	result := strs[0]
	for i := 1; i < len(strs); i++ {
		result += sep + strs[i]
	}
	return result
}
