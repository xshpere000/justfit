// Package service 提供业务服务层实现
package service

import (
	"context"
	"encoding/json"
	"fmt"

	"justfit/internal/analyzer"
	"justfit/internal/etl"
	applogger "justfit/internal/logger"
	"justfit/internal/storage"
	"justfit/internal/task"
)

// CollectionExecutor 采集任务执行器
type CollectionExecutor struct {
	collector *etl.Collector
	repos     *storage.Repositories
	log       applogger.Logger
}

// NewCollectionExecutor 创建采集任务执行器
func NewCollectionExecutor(collector *etl.Collector, repos *storage.Repositories) *CollectionExecutor {
	return &CollectionExecutor{
		collector: collector,
		repos:     repos,
		log:       applogger.With(applogger.Str("component", "CollectionExecutor")),
	}
}

// Execute 执行采集任务
func (e *CollectionExecutor) Execute(ctx context.Context, t *task.Task, progressCh chan<- float64) (*task.TaskResult, error) {
	// 从配置中提取参数
	// 支持 float64 (JSON 解码) 和 uint (直接传值) 两种类型
	var connectionID uint
	switch v := t.Config["connectionId"].(type) {
	case float64:
		connectionID = uint(v)
	case uint:
		connectionID = v
	default:
		return &task.TaskResult{
			Success: false,
			Message: "无效的 connection_id 配置",
		}, fmt.Errorf("无效的 connection_id 配置，期望 float64 或 uint 类型，实际得到 %T", t.Config["connectionId"])
	}

	// 获取数据类型配置
	dataTypes, _ := t.Config["dataTypes"].([]string)
	if len(dataTypes) == 0 {
		dataTypes = []string{"clusters", "hosts", "vms"}
	}

	// 获取采集天数配置
	metricsDaysFloat, ok := t.Config["metricsDays"].(float64)
	metricsDays := 7
	if ok {
		metricsDays = int(metricsDaysFloat)
	}

	// 获取密码（从配置中）
	password, _ := t.Config["password"].(string)

	progressCh <- 10

	// 构建采集配置
	config := &etl.CollectionConfig{
		ConnectionID: connectionID,
		DataTypes:    dataTypes,
		MetricsDays:  metricsDays,
		Concurrency:  3,
		Password:     password,
	}

	// 执行采集
	result, err := e.collector.Collect(ctx, config)
	progressCh <- 30 // 基础数据采集完成

	if err != nil {
		return &task.TaskResult{
			Success: false,
			Message: fmt.Sprintf("采集失败: %v", err),
		}, err
	}

	// 如果需要采集性能指标
	metricCount := 0
	metricScope := ""
	failedVMCount := 0
	failedMetricCount := 0
	metricReasons := []string{}
	if containsString(dataTypes, "metrics") && metricsDays > 0 {
		// 获取用户选择的虚拟机列表
		selectedVMs := getSelectedVMsFromConfig(t.Config)

		// 计算进度范围：30% → 90%（60%范围给性能指标采集）
		startProgress := 30.0
		endProgress := 90.0

		metricStats, metricErr := e.collector.CollectMetrics(ctx, t.ID, connectionID, metricsDays, password, selectedVMs,
			func(current, total int, message string) {
				// 计算当前进度：30% + (完成比例 * 60%)
				if total > 0 {
					progress := startProgress + (float64(current)/float64(total))*float64(endProgress-startProgress)
					progressCh <- progress
				}
			})
		if metricStats != nil {
			metricCount = metricStats.CollectedMetricCount
			metricScope = metricStats.Scope
			failedVMCount = metricStats.FailedVMCount
			failedMetricCount = metricStats.FailedMetricCount
			metricReasons = metricStats.Reasons
		}

		err = metricErr
		if err != nil {
			// 性能指标采集失败不影响基础数据采集结果
			e.log.Warn("采集性能指标失败", applogger.Uint("taskID", t.ID), applogger.Err(err))
		}
	}

	// 保存快照：90% → 100%
	progressCh <- 95 // 开始保存快照

	if snapshotErr := e.captureTaskVMSnapshots(t.ID, connectionID, getSelectedVMsFromConfig(t.Config)); snapshotErr != nil {
		e.log.Warn("保存任务虚拟机快照失败", applogger.Uint("taskID", t.ID), applogger.Err(snapshotErr))
	}

	progressCh <- 100 // 全部完成

	return &task.TaskResult{
		Success: true,
		Message: "采集成功",
		Data: map[string]interface{}{
			"clusters":             result.Clusters,
			"hosts":                result.Hosts,
			"vms":                  result.VMs,
			"metrics":              metricCount,
			"metrics_scope":        metricScope,
			"metrics_failed_vms":   failedVMCount,
			"metrics_failed_count": failedMetricCount,
			"metrics_reasons":      metricReasons,
			"duration":             result.Duration.Milliseconds(),
		},
	}, nil
}

// containsString 检查字符串切片是否包含指定元素
func containsString(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// AnalysisExecutor 分析任务执行器
type AnalysisExecutor struct {
	analyzer *analyzer.Engine
	repos    *storage.Repositories
	log      applogger.Logger
}

// NewAnalysisExecutor 创建分析任务执行器
func NewAnalysisExecutor(analyzer *analyzer.Engine, repos *storage.Repositories) *AnalysisExecutor {
	return &AnalysisExecutor{
		analyzer: analyzer,
		repos:    repos,
		log:      applogger.With(applogger.Str("component", "AnalysisExecutor")),
	}
}

// Execute 执行分析任务
func (e *AnalysisExecutor) Execute(ctx context.Context, t *task.Task, progressCh chan<- float64) (*task.TaskResult, error) {
	log := e.log.With(applogger.Uint("taskID", t.ID))

	log.Info("开始执行分析任务", applogger.Any("config", t.Config))

	// 从配置中提取参数
	analysisType, ok := t.Config["analysisType"].(string)
	if !ok {
		log.Warn("无效的 analysis_type 配置")
		return &task.TaskResult{
			Success: false,
			Message: "无效的 analysis_type 配置",
		}, fmt.Errorf("无效的 analysis_type 配置")
	}
	log.Debug("分析类型", applogger.String("type", analysisType))

	// 支持 float64 (JSON 解码) 和 uint (直接传值) 两种类型
	var connectionID uint
	switch v := t.Config["connectionId"].(type) {
	case float64:
		connectionID = uint(v)
	case uint:
		connectionID = v
	default:
		log.Warn("无效的 connection_id 配置", applogger.String("type", fmt.Sprintf("%T", t.Config["connectionId"])))
		return &task.TaskResult{
			Success: false,
			Message: "无效的 connection_id 配置",
		}, fmt.Errorf("无效的 connection_id 配置，期望 float64 或 uint 类型，实际得到 %T", t.Config["connectionId"])
	}
	log.Debug("连接ID", applogger.Uint("id", connectionID))

	progressCh <- 10

	var result interface{}
	var err error

	log.Debug("开始调用具体分析方法", applogger.String("type", analysisType))
	switch analysisType {
	case "zombie":
		result, err = e.executeZombieVMAnalysis(t.ID, connectionID, t.Config, progressCh)
	case "rightsize":
		result, err = e.executeRightSizeAnalysis(t.ID, connectionID, t.Config, progressCh)
	case "tidal":
		result, err = e.executeTidalAnalysis(t.ID, connectionID, t.Config, progressCh)
	case "health":
		result, err = e.executeHealthScoreAnalysis(connectionID, progressCh)
	default:
		log.Warn("不支持的分析类型", applogger.String("type", analysisType))
		return &task.TaskResult{
			Success: false,
			Message: fmt.Sprintf("不支持的分析类型: %s", analysisType),
		}, fmt.Errorf("不支持的分析类型: %s", analysisType)
	}

	progressCh <- 100

	if err != nil {
		log.Error("分析执行失败", applogger.Err(err))
		return &task.TaskResult{
			Success: false,
			Message: fmt.Sprintf("分析失败: %v", err),
		}, err
	}
	log.Info("分析执行成功", applogger.String("resultType", fmt.Sprintf("%T", result)))

	if saveErr := e.saveTaskAnalysisResult(t.ID, analysisType, result); saveErr != nil {
		log.Error("保存任务分析结果失败", applogger.Uint("taskID", t.ID), applogger.String("type", analysisType), applogger.Err(saveErr))
	} else {
		log.Info("保存任务分析结果成功", applogger.Uint("taskID", t.ID), applogger.String("type", analysisType))
	}

	return &task.TaskResult{
		Success: true,
		Message: "分析成功",
		Data: map[string]interface{}{
			"analysis_type": analysisType,
			"result":        result,
		},
	}, nil
}

func (e *CollectionExecutor) captureTaskVMSnapshots(taskID, connectionID uint, selectedVMs []string) error {
	log := e.log.With(
		applogger.Uint("taskID", taskID),
		applogger.Uint("connectionID", connectionID),
		applogger.Int("selectedVMs", len(selectedVMs)))

	log.Info("开始捕获任务快照")

	vms, err := e.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		log.Error("获取虚拟机列表失败", applogger.Err(err))
		return fmt.Errorf("获取虚拟机列表失败: %w", err)
	}
	log.Debug("数据库中的虚拟机数量", applogger.Int("count", len(vms)))

	// 如果用户选择了虚拟机，只保存选中的
	var filteredVMs []storage.VM
	if len(selectedVMs) > 0 {
		selectedSet := make(map[string]bool)
		for _, vmKey := range selectedVMs {
			selectedSet[vmKey] = true
		}
		for _, vm := range vms {
			if selectedSet[vm.VMKey] {
				filteredVMs = append(filteredVMs, vm)
			}
		}
		log.Debug("过滤后的虚拟机数量", applogger.Int("count", len(filteredVMs)))
	} else {
		filteredVMs = vms
		log.Debug("保存所有虚拟机", applogger.Int("count", len(filteredVMs)))
	}

	snapshots := make([]storage.TaskVMSnapshot, 0, len(filteredVMs))
	for _, vm := range filteredVMs {
		snapshots = append(snapshots, storage.TaskVMSnapshot{
			TaskID:          taskID,
			ConnectionID:    connectionID,
			VMKey:           vm.VMKey,
			UUID:            vm.UUID,
			Name:            vm.Name,
			Datacenter:      vm.Datacenter,
			CpuCount:        vm.CpuCount,
			MemoryMB:        vm.MemoryMB,
			PowerState:      vm.PowerState,
			ConnectionState: vm.ConnectionState,
			IPAddress:       vm.IPAddress,
			GuestOS:         vm.GuestOS,
			HostName:        vm.HostName,
			HostIP:          vm.HostIP,
			OverallStatus:   vm.OverallStatus,
			CollectedAt:     vm.CollectedAt,
		})
	}

	err = e.repos.TaskVMSnapshot.ReplaceByTaskID(taskID, snapshots)
	if err != nil {
		log.Error("保存快照失败", applogger.Err(err))
		return err
	}
	log.Info("快照保存成功", applogger.Uint("taskID", taskID), applogger.Int("count", len(snapshots)))
	return nil
}

func (e *AnalysisExecutor) saveTaskAnalysisResult(taskID uint, analysisType string, result interface{}) error {
	log := e.log.With(
		applogger.Uint("taskID", taskID),
		applogger.String("analysisType", analysisType))

	log.Debug("开始保存任务分析结果")

	payload, err := json.Marshal(result)
	if err != nil {
		log.Error("序列化分析结果失败", applogger.Err(err))
		return fmt.Errorf("序列化分析结果失败: %w", err)
	}
	log.Debug("序列化成功", applogger.Int("bytes", len(payload)))

	record := &storage.TaskAnalysisJob{
		TaskID:  taskID,
		JobType: analysisType,
		Status:  "completed",
		Result:  string(payload),
	}

	// 计算结果数量
	if m, ok := result.(map[string]interface{}); ok {
		if count, ok := m["count"].(float64); ok {
			record.ResultCount = int(count)
		}
	}

	if err := e.repos.TaskAnalysisJob.Create(record); err != nil {
		log.Error("数据库保存失败", applogger.Err(err))
		return err
	}
	log.Info("数据库保存成功", applogger.Uint("id", record.ID))
	return nil
}

// executeZombieVMAnalysis 执行僵尸VM分析
func (e *AnalysisExecutor) executeZombieVMAnalysis(taskID uint, connectionID uint, config map[string]interface{}, progressCh chan<- float64) (interface{}, error) {
	log := e.log.With(
		applogger.Uint("taskID", taskID),
		applogger.Uint("connectionID", connectionID),
		applogger.String("analysis", "zombie"))

	log.Info("开始执行僵尸VM分析")

	zombieConfig := parseZombieVMConfig(config)
	log.Debug("僵尸VM配置",
		applogger.Int("analysisDays", zombieConfig.AnalysisDays),
		applogger.Float64("cpuThreshold", zombieConfig.CPUThreshold),
		applogger.Float64("memoryThreshold", zombieConfig.MemoryThreshold))

	progressCh <- 30

	results, err := e.analyzer.DetectZombieVMs(taskID, connectionID, zombieConfig)
	if err != nil {
		log.Error("僵尸VM分析失败", applogger.Err(err))
		return nil, err
	}
	log.Info("僵尸VM分析完成", applogger.Int("count", len(results)))

	progressCh <- 80

	// 转换结果（使用驼峰命名）
	output := make([]map[string]interface{}, len(results))
	for i, r := range results {
		output[i] = map[string]interface{}{
			"vmName":         r.VMName,
			"datacenter":     r.Datacenter,
			"host":           r.Host,
			"cpuCount":       r.CPUCount,
			"memoryMb":       r.MemoryMB,
			"cpuUsage":       r.CPUUsage,
			"memoryUsage":    r.MemoryUsage,
			"confidence":     r.Confidence,
			"daysLowUsage":   r.DaysLowUsage,
			"evidence":       r.Evidence,
			"recommendation": r.Recommendation,
		}
	}

	return map[string]interface{}{
		"count":   len(results),
		"results": output,
	}, nil
}

// executeRightSizeAnalysis 执行Right Size分析
func (e *AnalysisExecutor) executeRightSizeAnalysis(taskID uint, connectionID uint, config map[string]interface{}, progressCh chan<- float64) (interface{}, error) {
	rightSizeConfig := parseRightSizeConfig(config)

	progressCh <- 30

	results, err := e.analyzer.AnalyzeRightSize(taskID, connectionID, rightSizeConfig)
	if err != nil {
		return nil, err
	}

	progressCh <- 80

	// 转换结果（使用驼峰命名）
	output := make([]map[string]interface{}, len(results))
	for i, r := range results {
		output[i] = map[string]interface{}{
			"vmName":              r.VMName,
			"datacenter":          r.Datacenter,
			"currentCpu":          r.CurrentCPU,
			"currentMemoryMb":     r.CurrentMemoryMB,
			"recommendedCpu":      r.RecommendedCPU,
			"recommendedMemoryMb": r.RecommendedMemoryMB,
			"adjustmentType":      r.AdjustmentType,
			"riskLevel":           r.RiskLevel,
			"estimatedSaving":     r.EstimatedSaving,
			"confidence":          r.Confidence,
		}
	}

	return map[string]interface{}{
		"count":   len(results),
		"results": output,
	}, nil
}

// executeTidalAnalysis 执行潮汐分析
func (e *AnalysisExecutor) executeTidalAnalysis(taskID uint, connectionID uint, config map[string]interface{}, progressCh chan<- float64) (interface{}, error) {
	tidalConfig := parseTidalConfig(config)

	progressCh <- 30

	results, err := e.analyzer.DetectTidalPattern(taskID, connectionID, tidalConfig)
	if err != nil {
		return nil, err
	}

	progressCh <- 80

	// 转换结果（使用驼峰命名）
	output := make([]map[string]interface{}, len(results))
	for i, r := range results {
		output[i] = map[string]interface{}{
			"vmName":          r.VMName,
			"datacenter":      r.Datacenter,
			"pattern":         string(r.Pattern),
			"stabilityScore":  r.StabilityScore,
			"peakHours":       r.PeakHours,
			"peakDays":        r.PeakDays,
			"recommendation":  r.Recommendation,
			"estimatedSaving": r.EstimatedSaving,
		}
	}

	return map[string]interface{}{
		"count":   len(results),
		"results": output,
	}, nil
}

// executeHealthScoreAnalysis 执行健康度分析
func (e *AnalysisExecutor) executeHealthScoreAnalysis(connectionID uint, progressCh chan<- float64) (interface{}, error) {
	progressCh <- 30

	result, err := e.analyzer.AnalyzeHealthScore(connectionID, nil)
	if err != nil {
		return nil, err
	}

	progressCh <- 80

	return map[string]interface{}{
		"connectionId":         result.ConnectionID,
		"connectionName":       result.ConnectionName,
		"overallScore":         result.OverallScore,
		"healthLevel":          result.HealthLevel,
		"resourceBalance":      result.ResourceBalance,
		"overcommitRisk":       result.OvercommitRisk,
		"hotspotConcentration": result.HotspotConcentration,
		"clusterCount":         result.ClusterCount,
		"hostCount":            result.HostCount,
		"vmCount":              result.VMCount,
		"riskItems":            result.RiskItems,
		"recommendations":      result.Recommendations,
	}, nil
}

// parseZombieVMConfig 解析僵尸VM配置
func parseZombieVMConfig(config map[string]interface{}) *analyzer.ZombieVMConfig {
	result := analyzer.DefaultZombieVMConfig()

	if v, ok := config["analysisDays"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["cpuThreshold"].(float64); ok {
		result.CPUThreshold = v
	}
	if v, ok := config["memoryThreshold"].(float64); ok {
		result.MemoryThreshold = v
	}
	if v, ok := config["minConfidence"].(float64); ok {
		result.MinConfidence = v
	}

	return result
}

// parseRightSizeConfig 解析Right Size配置
func parseRightSizeConfig(config map[string]interface{}) *analyzer.RightSizeConfig {
	result := analyzer.DefaultRightSizeConfig()

	if v, ok := config["analysisDays"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["bufferRatio"].(float64); ok {
		result.BufferRatio = v
	}

	return result
}

// parseTidalConfig 解析潮汐配置
func parseTidalConfig(config map[string]interface{}) *analyzer.TidalConfig {
	result := analyzer.DefaultTidalConfig()

	if v, ok := config["analysisDays"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["minStability"].(float64); ok {
		result.MinStability = v
	}

	return result
}

// getSelectedVMsFromConfig 从配置中获取用户选择的虚拟机列表
func getSelectedVMsFromConfig(config map[string]interface{}) []string {
	v, ok := config["selectedVMs"]
	if !ok {
		return []string{}
	}

	if direct, ok := v.([]string); ok {
		return direct
	}

	if rawList, ok := v.([]interface{}); ok {
		result := make([]string, 0, len(rawList))
		for _, item := range rawList {
			if s, ok := item.(string); ok {
				result = append(result, s)
			}
		}
		return result
	}

	return []string{}
}
