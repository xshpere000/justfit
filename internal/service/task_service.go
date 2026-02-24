// Package service 提供业务服务层实现
package service

import (
	"context"
	"encoding/json"
	"fmt"

	"justfit/internal/analyzer"
	"justfit/internal/etl"
	"justfit/internal/storage"
	"justfit/internal/task"
)

// CollectionExecutor 采集任务执行器
type CollectionExecutor struct {
	collector *etl.Collector
	repos     *storage.Repositories
}

// NewCollectionExecutor 创建采集任务执行器
func NewCollectionExecutor(collector *etl.Collector, repos *storage.Repositories) *CollectionExecutor {
	return &CollectionExecutor{
		collector: collector,
		repos:     repos,
	}
}

// Execute 执行采集任务
func (e *CollectionExecutor) Execute(ctx context.Context, t *task.Task, progressCh chan<- float64) (*task.TaskResult, error) {
	// 从配置中提取参数
	// 支持 float64 (JSON 解码) 和 uint (直接传值) 两种类型
	var connectionID uint
	switch v := t.Config["connection_id"].(type) {
	case float64:
		connectionID = uint(v)
	case uint:
		connectionID = v
	default:
		return &task.TaskResult{
			Success: false,
			Message: "无效的 connection_id 配置",
		}, fmt.Errorf("无效的 connection_id 配置，期望 float64 或 uint 类型，实际得到 %T", t.Config["connection_id"])
	}

	// 获取数据类型配置
	dataTypes, _ := t.Config["data_types"].([]string)
	if len(dataTypes) == 0 {
		dataTypes = []string{"clusters", "hosts", "vms"}
	}

	// 获取采集天数配置
	metricsDaysFloat, ok := t.Config["metrics_days"].(float64)
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

	progressCh <- 20

	// 执行采集
	result, err := e.collector.Collect(ctx, config)
	progressCh <- 80

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

		metricStats, metricErr := e.collector.CollectMetrics(ctx, connectionID, metricsDays, password, selectedVMs)
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
			fmt.Printf("采集性能指标失败: %v\n", err)
		}
	}

	if snapshotErr := e.captureTaskVMSnapshots(t.ID, connectionID, getSelectedVMsFromConfig(t.Config)); snapshotErr != nil {
		fmt.Printf("保存任务虚拟机快照失败 task=%d: %v\n", t.ID, snapshotErr)
	}

	progressCh <- 100

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
}

// NewAnalysisExecutor 创建分析任务执行器
func NewAnalysisExecutor(analyzer *analyzer.Engine, repos *storage.Repositories) *AnalysisExecutor {
	return &AnalysisExecutor{
		analyzer: analyzer,
		repos:    repos,
	}
}

// Execute 执行分析任务
func (e *AnalysisExecutor) Execute(ctx context.Context, t *task.Task, progressCh chan<- float64) (*task.TaskResult, error) {
	fmt.Printf("[AnalysisExecutor.Execute] 开始执行分析任务: taskID=%d, config=%+v\n", t.ID, t.Config)

	// 从配置中提取参数
	analysisType, ok := t.Config["analysis_type"].(string)
	if !ok {
		fmt.Printf("[AnalysisExecutor.Execute] 错误：无效的 analysis_type 配置\n")
		return &task.TaskResult{
			Success: false,
			Message: "无效的 analysis_type 配置",
		}, fmt.Errorf("无效的 analysis_type 配置")
	}
	fmt.Printf("[AnalysisExecutor.Execute] 分析类型: %s\n", analysisType)

	// 支持 float64 (JSON 解码) 和 uint (直接传值) 两种类型
	var connectionID uint
	switch v := t.Config["connection_id"].(type) {
	case float64:
		connectionID = uint(v)
	case uint:
		connectionID = v
	default:
		fmt.Printf("[AnalysisExecutor.Execute] 错误：无效的 connection_id 配置, type=%T\n", t.Config["connection_id"])
		return &task.TaskResult{
			Success: false,
			Message: "无效的 connection_id 配置",
		}, fmt.Errorf("无效的 connection_id 配置，期望 float64 或 uint 类型，实际得到 %T", t.Config["connection_id"])
	}
	fmt.Printf("[AnalysisExecutor.Execute] 连接ID: %d\n", connectionID)

	progressCh <- 10

	var result interface{}
	var err error

	fmt.Printf("[AnalysisExecutor.Execute] 开始调用具体分析方法: %s\n", analysisType)
	switch analysisType {
	case "zombie_vm":
		result, err = e.executeZombieVMAnalysis(connectionID, t.Config, progressCh)
	case "right_size":
		result, err = e.executeRightSizeAnalysis(connectionID, t.Config, progressCh)
	case "tidal":
		result, err = e.executeTidalAnalysis(connectionID, t.Config, progressCh)
	case "health_score":
		result, err = e.executeHealthScoreAnalysis(connectionID, progressCh)
	default:
		fmt.Printf("[AnalysisExecutor.Execute] 错误：不支持的分析类型: %s\n", analysisType)
		return &task.TaskResult{
			Success: false,
			Message: fmt.Sprintf("不支持的分析类型: %s", analysisType),
		}, fmt.Errorf("不支持的分析类型: %s", analysisType)
	}

	progressCh <- 100

	if err != nil {
		fmt.Printf("[AnalysisExecutor.Execute] 分析执行失败: %v\n", err)
		return &task.TaskResult{
			Success: false,
			Message: fmt.Sprintf("分析失败: %v", err),
		}, err
	}
	fmt.Printf("[AnalysisExecutor.Execute] 分析执行成功: result type=%T\n", result)

	if saveErr := e.saveTaskAnalysisResult(t.ID, analysisType, result); saveErr != nil {
		fmt.Printf("[AnalysisExecutor] 保存任务分析结果失败 task=%d type=%s: %v\n", t.ID, analysisType, saveErr)
	} else {
		fmt.Printf("[AnalysisExecutor] 保存任务分析结果成功 task=%d type=%s\n", t.ID, analysisType)
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
	fmt.Printf("[captureTaskVMSnapshots] 开始捕获任务快照, taskID=%d, connectionID=%d, 选中VM数=%d\n", taskID, connectionID, len(selectedVMs))
	vms, err := e.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		fmt.Printf("[captureTaskVMSnapshots] 获取虚拟机列表失败: %v\n", err)
		return fmt.Errorf("获取虚拟机列表失败: %w", err)
	}
	fmt.Printf("[captureTaskVMSnapshots] 数据库中有 %d 台虚拟机\n", len(vms))

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
		fmt.Printf("[captureTaskVMSnapshots] 过滤后 %d 台虚拟机（用户选择）\n", len(filteredVMs))
	} else {
		filteredVMs = vms
		fmt.Printf("[captureTaskVMSnapshots] 保存所有 %d 台虚拟机\n", len(filteredVMs))
	}

	snapshots := make([]storage.TaskVMSnapshot, 0, len(filteredVMs))
	for _, vm := range filteredVMs {
		snapshots = append(snapshots, storage.TaskVMSnapshot{
			TaskID:        taskID,
			ConnectionID:  connectionID,
			VMKey:         vm.VMKey,
			UUID:          vm.UUID,
			Name:          vm.Name,
			Datacenter:    vm.Datacenter,
			CpuCount:      vm.CpuCount,
			MemoryMB:      vm.MemoryMB,
			PowerState:    vm.PowerState,
			IPAddress:     vm.IPAddress,
			GuestOS:       vm.GuestOS,
			HostName:      vm.HostName,
			OverallStatus: vm.OverallStatus,
			CollectedAt:   vm.CollectedAt,
		})
	}

	err = e.repos.TaskVMSnapshot.ReplaceByTaskID(taskID, snapshots)
	if err != nil {
		fmt.Printf("[captureTaskVMSnapshots] 保存快照失败: %v\n", err)
		return err
	}
	fmt.Printf("[captureTaskVMSnapshots] 快照保存成功, taskID=%d, 数量=%d\n", taskID, len(snapshots))
	return nil
}

func (e *AnalysisExecutor) saveTaskAnalysisResult(taskID uint, analysisType string, result interface{}) error {
	fmt.Printf("[saveTaskAnalysisResult] 开始保存: taskID=%d, analysisType=%s\n", taskID, analysisType)
	payload, err := json.Marshal(result)
	if err != nil {
		fmt.Printf("[saveTaskAnalysisResult] 序列化失败: %v\n", err)
		return fmt.Errorf("序列化分析结果失败: %w", err)
	}
	fmt.Printf("[saveTaskAnalysisResult] 序列化成功，数据大小=%d bytes\n", len(payload))

	record := &storage.TaskAnalysisResult{
		TaskID:       taskID,
		AnalysisType: analysisType,
		Data:         string(payload),
	}

	if err := e.repos.TaskAnalysis.Create(record); err != nil {
		fmt.Printf("[saveTaskAnalysisResult] 数据库保存失败: %v\n", err)
		return err
	}
	fmt.Printf("[saveTaskAnalysisResult] 数据库保存成功: id=%d\n", record.ID)
	return nil
}

// executeZombieVMAnalysis 执行僵尸VM分析
func (e *AnalysisExecutor) executeZombieVMAnalysis(connectionID uint, config map[string]interface{}, progressCh chan<- float64) (interface{}, error) {
	fmt.Printf("[executeZombieVMAnalysis] 开始执行僵尸VM分析, connectionID=%d\n", connectionID)
	zombieConfig := parseZombieVMConfig(config)
	fmt.Printf("[executeZombieVMAnalysis] 配置: analysisDays=%d, cpuThreshold=%f, memoryThreshold=%f\n",
		zombieConfig.AnalysisDays, zombieConfig.CPUThreshold, zombieConfig.MemoryThreshold)

	progressCh <- 30

	fmt.Printf("[executeZombieVMAnalysis] 调用 analyzer.DetectZombieVMs\n")
	results, err := e.analyzer.DetectZombieVMs(connectionID, zombieConfig)
	if err != nil {
		fmt.Printf("[executeZombieVMAnalysis] 分析失败: %v\n", err)
		return nil, err
	}
	fmt.Printf("[executeZombieVMAnalysis] 分析完成，找到 %d 个僵尸VM\n", len(results))

	progressCh <- 80

	// 转换结果
	output := make([]map[string]interface{}, len(results))
	for i, r := range results {
		output[i] = map[string]interface{}{
			"vm_name":        r.VMName,
			"datacenter":     r.Datacenter,
			"host":           r.Host,
			"cpu_count":      r.CPUCount,
			"memory_mb":      r.MemoryMB,
			"cpu_usage":      r.CPUUsage,
			"memory_usage":   r.MemoryUsage,
			"confidence":     r.Confidence,
			"days_low_usage": r.DaysLowUsage,
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
func (e *AnalysisExecutor) executeRightSizeAnalysis(connectionID uint, config map[string]interface{}, progressCh chan<- float64) (interface{}, error) {
	rightSizeConfig := parseRightSizeConfig(config)

	progressCh <- 30

	results, err := e.analyzer.AnalyzeRightSize(connectionID, rightSizeConfig)
	if err != nil {
		return nil, err
	}

	progressCh <- 80

	// 转换结果
	output := make([]map[string]interface{}, len(results))
	for i, r := range results {
		output[i] = map[string]interface{}{
			"vm_name":               r.VMName,
			"datacenter":            r.Datacenter,
			"current_cpu":           r.CurrentCPU,
			"current_memory_mb":     r.CurrentMemoryMB,
			"recommended_cpu":       r.RecommendedCPU,
			"recommended_memory_mb": r.RecommendedMemoryMB,
			"adjustment_type":       r.AdjustmentType,
			"risk_level":            r.RiskLevel,
			"estimated_saving":      r.EstimatedSaving,
			"confidence":            r.Confidence,
		}
	}

	return map[string]interface{}{
		"count":   len(results),
		"results": output,
	}, nil
}

// executeTidalAnalysis 执行潮汐分析
func (e *AnalysisExecutor) executeTidalAnalysis(connectionID uint, config map[string]interface{}, progressCh chan<- float64) (interface{}, error) {
	tidalConfig := parseTidalConfig(config)

	progressCh <- 30

	results, err := e.analyzer.DetectTidalPattern(connectionID, tidalConfig)
	if err != nil {
		return nil, err
	}

	progressCh <- 80

	// 转换结果
	output := make([]map[string]interface{}, len(results))
	for i, r := range results {
		output[i] = map[string]interface{}{
			"vm_name":          r.VMName,
			"datacenter":       r.Datacenter,
			"pattern":          string(r.Pattern),
			"stability_score":  r.StabilityScore,
			"peak_hours":       r.PeakHours,
			"peak_days":        r.PeakDays,
			"recommendation":   r.Recommendation,
			"estimated_saving": r.EstimatedSaving,
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
		"connection_id":         result.ConnectionID,
		"connection_name":       result.ConnectionName,
		"overall_score":         result.OverallScore,
		"health_level":          result.HealthLevel,
		"resource_balance":      result.ResourceBalance,
		"overcommit_risk":       result.OvercommitRisk,
		"hotspot_concentration": result.HotspotConcentration,
		"total_clusters":        result.TotalClusters,
		"total_hosts":           result.TotalHosts,
		"total_vms":             result.TotalVMs,
		"risk_items":            result.RiskItems,
		"recommendations":       result.Recommendations,
	}, nil
}

// parseZombieVMConfig 解析僵尸VM配置
func parseZombieVMConfig(config map[string]interface{}) *analyzer.ZombieVMConfig {
	result := analyzer.DefaultZombieVMConfig()

	if v, ok := config["analysis_days"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["cpu_threshold"].(float64); ok {
		result.CPUThreshold = v
	}
	if v, ok := config["memory_threshold"].(float64); ok {
		result.MemoryThreshold = v
	}
	if v, ok := config["min_confidence"].(float64); ok {
		result.MinConfidence = v
	}

	return result
}

// parseRightSizeConfig 解析Right Size配置
func parseRightSizeConfig(config map[string]interface{}) *analyzer.RightSizeConfig {
	result := analyzer.DefaultRightSizeConfig()

	if v, ok := config["analysis_days"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["buffer_ratio"].(float64); ok {
		result.BufferRatio = v
	}

	return result
}

// parseTidalConfig 解析潮汐配置
func parseTidalConfig(config map[string]interface{}) *analyzer.TidalConfig {
	result := analyzer.DefaultTidalConfig()

	if v, ok := config["analysis_days"].(float64); ok {
		result.AnalysisDays = int(v)
	}
	if v, ok := config["min_stability"].(float64); ok {
		result.MinStability = v
	}

	return result
}

// getSelectedVMsFromConfig 从配置中获取用户选择的虚拟机列表
func getSelectedVMsFromConfig(config map[string]interface{}) []string {
	v, ok := config["selected_vms"]
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
