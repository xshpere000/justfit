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

// SaveZombieVMResults 保存僵尸 VM 分析结果到指定任务
func (rs *ResultStorage) SaveZombieVMResults(taskID uint, results []ZombieVMResult) error {
	findings := make([]storage.AnalysisFinding, len(results))

	for i, r := range results {
		data, err := json.Marshal(r)
		if err != nil {
			return fmt.Errorf("序列化数据失败: %w", err)
		}

		severity := "info"
		if r.Confidence >= 80 {
			severity = "critical"
		} else if r.Confidence >= 60 {
			severity = "warning"
		}

		findings[i] = storage.AnalysisFinding{
			TaskID:     taskID,
			JobType:    "zombie",
			TargetType: "vm",
			TargetKey:  r.VMKey,
			TargetName: r.VMName,
			Severity:   severity,
			Category:   "zombie",
			Title:      fmt.Sprintf("僵尸VM: %s", r.VMName),
			Description: fmt.Sprintf("该虚拟机在 %d 天内CPU使用率低于 %d%%，内存使用率低于 %d%%",
				r.DaysLowUsage, r.CPUUsage, r.MemoryUsage),
			Action:  r.Recommendation,
			Reason:  estimateResourceSaving(r.CPUCount, r.MemoryMB, 0, 0),
			Details: string(data),
		}
	}

	return rs.repos.AnalysisFinding.BatchCreate(findings)
}

// SaveRightSizeResults 保存 Right Size 分析结果到指定任务
func (rs *ResultStorage) SaveRightSizeResults(taskID uint, results []RightSizeResult) error {
	findings := make([]storage.AnalysisFinding, len(results))

	for i, r := range results {
		data, err := json.Marshal(r)
		if err != nil {
			return fmt.Errorf("序列化数据失败: %w", err)
		}

		severity := "info"
		category := "normal"
		if r.AdjustmentType == "overprovisioned" {
			severity = "warning"
			category = "overprovisioned"
		} else if r.AdjustmentType == "underprovisioned" {
			severity = "warning"
			category = "underprovisioned"
		}

		findings[i] = storage.AnalysisFinding{
			TaskID:     taskID,
			JobType:    "rightsize",
			TargetType: "vm",
			TargetKey:  r.VMKey,
			TargetName: r.VMName,
			Severity:   severity,
			Category:   category,
			Title:      fmt.Sprintf("资源配置优化: %s", r.VMName),
			Description: fmt.Sprintf("%s: %d → %d vCPU, %d → %d MB RAM",
				r.AdjustmentType,
				r.CurrentCPU, r.RecommendedCPU,
				r.CurrentMemoryMB, r.RecommendedMemoryMB),
			Action:       fmt.Sprintf("建议调整配置为: %d vCPU, %d MB RAM", r.RecommendedCPU, r.RecommendedMemoryMB),
			Reason:       r.EstimatedSaving,
			SavingCPU:    r.CurrentCPU - r.RecommendedCPU,
			SavingMemory: r.CurrentMemoryMB - r.RecommendedMemoryMB,
			SavingCost:   r.EstimatedSaving,
			Details:      string(data),
		}
	}

	return rs.repos.AnalysisFinding.BatchCreate(findings)
}

// SaveTidalResults 保存潮汐分析结果到指定任务
func (rs *ResultStorage) SaveTidalResults(taskID uint, results []TidalResult) error {
	findings := make([]storage.AnalysisFinding, len(results))

	for i, r := range results {
		data, err := json.Marshal(r)
		if err != nil {
			return fmt.Errorf("序列化数据失败: %w", err)
		}

		severity := "info"
		if r.StabilityScore >= 80 {
			severity = "warning" // 高稳定性表示存在明显的潮汐模式
		}

		findings[i] = storage.AnalysisFinding{
			TaskID:     taskID,
			JobType:    "tidal",
			TargetType: "vm",
			TargetKey:  r.VMKey,
			TargetName: r.VMName,
			Severity:   severity,
			Category:   "tidal_pattern",
			Title:      fmt.Sprintf("潮汐模式: %s", r.VMName),
			Description: fmt.Sprintf("检测到潮汐模式，稳定度: %.0f%%。峰值时段: %s, 峰值日: %s",
				r.StabilityScore, r.PeakHours, r.PeakDays),
			Action:  r.Recommendation,
			Reason:  r.EstimatedSaving,
			Details: string(data),
		}
	}

	return rs.repos.AnalysisFinding.BatchCreate(findings)
}

// SaveHealthScoreResult 保存健康评分结果到指定任务
func (rs *ResultStorage) SaveHealthScoreResult(taskID uint, result HealthScoreResult) error {
	data, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("序列化数据失败: %w", err)
	}

	// 合并所有风险项和建议
	action := ""
	if len(result.Recommendations) > 0 {
		action = "建议: " + joinStrings(result.Recommendations, "; ")
	}

	severity := "info"
	if result.OverallScore >= 80 {
		severity = "critical"
	} else if result.OverallScore >= 60 {
		severity = "warning"
	}

	findings := make([]storage.AnalysisFinding, 0)

	// 主评分记录
	mainFinding := storage.AnalysisFinding{
		TaskID:     taskID,
		JobType:    "health",
		TargetType: "connection",
		TargetKey:  fmt.Sprintf("%d", result.ConnectionID),
		TargetName: result.ConnectionName,
		Severity:   severity,
		Category:   "health_risk",
		Title:      fmt.Sprintf("平台健康评分: %.0f", result.OverallScore),
		Description: fmt.Sprintf("健康度: %s, 资源平衡: %.0f, 过分配风险: %.0f",
			result.HealthLevel, result.ResourceBalance, result.OvercommitRisk),
		Action: action,
		Reason: fmt.Sprintf("总集群: %d, 总主机: %d, 总虚拟机: %d",
			result.ClusterCount, result.HostCount, result.VMCount),
		Details: string(data),
	}
	findings = append(findings, mainFinding)

	// 风险项作为单独的发现
	for _, risk := range result.RiskItems {
		findings = append(findings, storage.AnalysisFinding{
			TaskID:      taskID,
			JobType:     "health",
			TargetType:  "connection",
			TargetKey:   fmt.Sprintf("%d", result.ConnectionID),
			TargetName:  result.ConnectionName,
			Severity:    "warning",
			Category:    "health_risk",
			Title:       fmt.Sprintf("风险: %s", risk),
			Description: risk,
			Action:      action,
			Details:     string(data),
		})
	}

	return rs.repos.AnalysisFinding.BatchCreate(findings)
}

// CreateFinding 创建单个分析发现
func (rs *ResultStorage) CreateFinding(taskID uint, jobType, targetType, targetKey, targetName, severity, category, title, description, action string) error {
	finding := storage.AnalysisFinding{
		TaskID:      taskID,
		JobType:     jobType,
		TargetType:  targetType,
		TargetKey:   targetKey,
		TargetName:  targetName,
		Severity:    severity,
		Category:    category,
		Title:       title,
		Description: description,
		Action:      action,
	}

	return rs.repos.AnalysisFinding.Create(&finding)
}

// ==============================================================================
// 向后兼容方法 (不再使用 ReportID，改用 TaskID)
// ==============================================================================

// SaveZombieVMResultsToConnection 保存僵尸VM结果到连接 (向后兼容)
func (rs *ResultStorage) SaveZombieVMResultsToConnection(connectionID uint, results []ZombieVMResult) error {
	// 这个方法不再使用 ReportID，所以使用 taskID=0
	// 调用方应该使用新的带 taskID 的方法
	return rs.SaveZombieVMResults(0, results)
}

// SaveRightSizeResultsToConnection 保存Right Size结果到连接 (向后兼容)
func (rs *ResultStorage) SaveRightSizeResultsToConnection(connectionID uint, results []RightSizeResult) error {
	return rs.SaveRightSizeResults(0, results)
}

// SaveTidalResultsToConnection 保存潮汐分析结果到连接 (向后兼容)
func (rs *ResultStorage) SaveTidalResultsToConnection(connectionID uint, results []TidalResult) error {
	return rs.SaveTidalResults(0, results)
}

// CreateAlert 创建告警 (向后兼容，转换为 AnalysisFinding)
func (rs *ResultStorage) CreateAlert(targetType, targetKey, targetName, alertType, severity, title, message string, data interface{}) error {
	dataJSON, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("序列化数据失败: %w", err)
	}

	finding := storage.AnalysisFinding{
		JobType:     alertType,
		TargetType:  targetType,
		TargetKey:   targetKey,
		TargetName:  targetName,
		Severity:    severity,
		Category:    alertType,
		Title:       title,
		Description: message,
		Details:     string(dataJSON),
	}

	return rs.repos.AnalysisFinding.Create(&finding)
}

// CreateAlerts 批量创建告警 (向后兼容)
func (rs *ResultStorage) CreateAlerts(alerts []storage.Alert) error {
	// 转换为 AnalysisFinding
	findings := make([]storage.AnalysisFinding, len(alerts))
	for i, a := range alerts {
		findings[i] = storage.AnalysisFinding{
			JobType:     a.AlertType,
			TargetType:  a.TargetType,
			TargetKey:   a.TargetKey,
			TargetName:  a.TargetName,
			Severity:    a.Severity,
			Category:    a.AlertType,
			Title:       a.Title,
			Description: a.Message,
			Details:     a.Data,
		}
	}
	return rs.repos.AnalysisFinding.BatchCreate(findings)
}

// ==============================================================================
// 辅助函数
// ==============================================================================

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
