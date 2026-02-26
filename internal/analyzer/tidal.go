// Package analyzer 提供潮汐模式分析功能
package analyzer

import (
	"fmt"
	"math"
	"sort"
	"time"

	"justfit/internal/storage"
)

// TidalPattern 潮汐模式
type TidalPattern string

const (
	PatternDaily  TidalPattern = "daily"  // 日周期
	PatternWeekly TidalPattern = "weekly" // 周期
	PatternNone   TidalPattern = "none"   // 无明显模式
)

// TidalResult 潮汐分析结果
type TidalResult struct {
	VMAnalysisResult
	Pattern        TidalPattern `json:"pattern"`
	StabilityScore float64      `json:"stabilityScore"` // 稳定性评分 0-100
	PeakHours      []int        `json:"peakHours"`      // 高峰时段 (0-23)
	PeakDays       []int        `json:"peakDays"`       // 高峰日期 (0-6, 0=周日)
	TroughHours    []int        `json:"troughHours"`    // 低谷时段
	TroughDays     []int        `json:"troughDays"`     // 低谷日期

	// 推荐
	Recommendation  string `json:"recommendation"`
	EstimatedSaving string `json:"estimatedSaving"`
}

// TidalConfig 潮汐分析配置
type TidalConfig struct {
	AnalysisDays int     // 分析天数
	MinStability float64 // 最小稳定性评分
	MinVariation float64 // 最小变化幅度
}

// DefaultTidalConfig 默认潮汐分析配置
func DefaultTidalConfig() *TidalConfig {
	return &TidalConfig{
		AnalysisDays: 30,
		MinStability: 60.0,
		MinVariation: 30.0, // 30% 变化幅度
	}
}

// DetectTidalPattern 检测潮汐模式
func (e *Engine) DetectTidalPattern(connectionID uint, config *TidalConfig) ([]TidalResult, error) {
	if config == nil {
		config = DefaultTidalConfig()
	}

	// 获取虚拟机列表
	vms, err := e.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -config.AnalysisDays)

	var results []TidalResult

	for _, vm := range vms {
		// 跳过已关机的虚拟机
		if vm.PowerState != "poweredOn" {
			continue
		}

		// 获取 CPU 指标
		cpuMetrics, err := e.repos.Metric.ListByVMAndType(vm.ID, "cpu", startTime, endTime)
		if err != nil || len(cpuMetrics) == 0 {
			continue
		}

		// 分析日周期
		_, dailyStability := analyzeDailyPattern(cpuMetrics)

		// 分析周周期
		_, weeklyStability := analyzeWeeklyPattern(cpuMetrics)

		// 确定最终模式
		var pattern TidalPattern
		var stabilityScore float64
		var peakHours, peakDays, troughHours, troughDays []int

		if dailyStability > weeklyStability && dailyStability >= config.MinStability {
			pattern = PatternDaily
			stabilityScore = dailyStability
			peakHours, troughHours = extractPeakTroughHours(cpuMetrics)
		} else if weeklyStability >= config.MinStability {
			pattern = PatternWeekly
			stabilityScore = weeklyStability
			peakDays, troughDays = extractPeakTroughDays(cpuMetrics)
		} else {
			pattern = PatternNone
			stabilityScore = math.Max(dailyStability, weeklyStability)
		}

		// 只有检测到模式时才添加结果
		if pattern != PatternNone {
			result := TidalResult{
				VMAnalysisResult: VMAnalysisResult{
					VMKey:      vm.VMKey,
					VMName:     vm.Name,
					Datacenter: vm.Datacenter,
					Host:       vm.HostName,
					CPUCount:   vm.CpuCount,
					MemoryMB:   vm.MemoryMB,
					PowerState: string(vm.PowerState),
				},
				Pattern:         pattern,
				StabilityScore:  stabilityScore,
				PeakHours:       peakHours,
				PeakDays:        peakDays,
				TroughHours:     troughHours,
				TroughDays:      troughDays,
				Recommendation:  buildTidalRecommendation(vm.Name, pattern, peakHours, peakDays, troughHours, troughDays),
				EstimatedSaving: estimateTidalSaving(stabilityScore),
			}
			results = append(results, result)
		}
	}

	return results, nil
}

// analyzeDailyPattern 分析日周期模式
func analyzeDailyPattern(metrics []storage.Metric) (TidalPattern, float64) {
	// 按小时分组
	hourlyData := make(map[int][]float64)

	for _, m := range metrics {
		hour := m.Timestamp.Hour()
		hourlyData[hour] = append(hourlyData[hour], m.Value)
	}

	// 计算每小时的平均值
	hourlyAvg := make([]float64, 24)
	for hour := 0; hour < 24; hour++ {
		if values, ok := hourlyData[hour]; ok && len(values) > 0 {
			hourlyAvg[hour] = average(values)
		}
	}

	// 检查是否有明显的日模式
	// 计算方差
	mean := average(hourlyAvg)
	variance := 0.0
	for _, v := range hourlyAvg {
		diff := v - mean
		variance += diff * diff
	}
	variance /= 24

	stdDev := math.Sqrt(variance)
	cv := stdDev / mean * 100 // 变异系数

	// 变异系数越高，说明日间差异越大
	// 如果 CV > 20%，认为有明显日模式
	if cv > 20 {
		return PatternDaily, math.Min(100, cv*2)
	}

	return PatternNone, cv * 2
}

// analyzeWeeklyPattern 分析周周期模式
func analyzeWeeklyPattern(metrics []storage.Metric) (TidalPattern, float64) {
	// 按星期分组
	dailyData := make(map[int][]float64)

	for _, m := range metrics {
		day := int(m.Timestamp.Weekday())
		dailyData[day] = append(dailyData[day], m.Value)
	}

	// 计算每天的平均值
	dailyAvg := make([]float64, 7)
	for day := 0; day < 7; day++ {
		if values, ok := dailyData[day]; ok && len(values) > 0 {
			dailyAvg[day] = average(values)
		}
	}

	// 计算方差
	mean := average(dailyAvg)
	variance := 0.0
	for _, v := range dailyAvg {
		diff := v - mean
		variance += diff * diff
	}
	variance /= 7

	stdDev := math.Sqrt(variance)
	cv := stdDev / mean * 100

	// 如果 CV > 15%，认为有明显周模式
	if cv > 15 {
		return PatternWeekly, math.Min(100, cv*2.5)
	}

	return PatternNone, cv * 2.5
}

// extractPeakTroughHours 提取高峰和低谷时段
func extractPeakTroughHours(metrics []storage.Metric) (peakHours, troughHours []int) {
	// 按小时分组
	hourlyData := make(map[int][]float64)

	for _, m := range metrics {
		hour := m.Timestamp.Hour()
		hourlyData[hour] = append(hourlyData[hour], m.Value)
	}

	// 计算每小时的平均值
	type hourAvg struct {
		hour int
		avg  float64
	}

	var avgs []hourAvg
	for hour := 0; hour < 24; hour++ {
		if values, ok := hourlyData[hour]; ok && len(values) > 0 {
			avgs = append(avgs, hourAvg{hour: hour, avg: average(values)})
		}
	}

	// 排序
	sort.Slice(avgs, func(i, j int) bool {
		return avgs[i].avg > avgs[j].avg
	})

	// 取前 25% 作为高峰，后 25% 作为低谷
	topCount := len(avgs) / 4
	if topCount < 1 {
		topCount = 1
	}

	for i := 0; i < topCount && i < len(avgs); i++ {
		peakHours = append(peakHours, avgs[i].hour)
	}

	for i := len(avgs) - 1; i >= len(avgs)-topCount && i >= 0; i-- {
		troughHours = append(troughHours, avgs[i].hour)
	}

	return peakHours, troughHours
}

// extractPeakTroughDays 提取高峰和低谷日期
func extractPeakTroughDays(metrics []storage.Metric) (peakDays, troughDays []int) {
	// 按星期分组
	dailyData := make(map[int][]float64)

	for _, m := range metrics {
		day := int(m.Timestamp.Weekday())
		dailyData[day] = append(dailyData[day], m.Value)
	}

	// 计算每天的平均值
	type dayAvg struct {
		day int
		avg float64
	}

	var avgs []dayAvg
	for day := 0; day < 7; day++ {
		if values, ok := dailyData[day]; ok && len(values) > 0 {
			avgs = append(avgs, dayAvg{day: day, avg: average(values)})
		}
	}

	// 排序
	sort.Slice(avgs, func(i, j int) bool {
		return avgs[i].avg > avgs[j].avg
	})

	// 取前 1-2 天作为高峰，后 1-2 天作为低谷
	topCount := 2
	if len(avgs) < 2 {
		topCount = len(avgs)
	}

	for i := 0; i < topCount; i++ {
		peakDays = append(peakDays, avgs[i].day)
	}

	for i := len(avgs) - 1; i >= len(avgs)-topCount && i >= 0; i-- {
		troughDays = append(troughDays, avgs[i].day)
	}

	return peakDays, troughDays
}

// buildTidalRecommendation 构建潮汐建议
func buildTidalRecommendation(vmName string, pattern TidalPattern, peakHours, peakDays, troughHours, troughDays []int) string {
	var rec string

	if pattern == PatternDaily {
		if len(peakHours) > 0 && len(troughHours) > 0 {
			rec = fmt.Sprintf("虚拟机 %s 具有明显的日周期模式，建议在低谷时段（%d:00-%d:00）关机",
				vmName, troughHours[0], troughHours[len(troughHours)-1])
		} else {
			rec = fmt.Sprintf("虚拟机 %s 具有日周期模式，建议根据负载变化调整运行时间", vmName)
		}
	} else if pattern == PatternWeekly {
		dayNames := []string{"周日", "周一", "周二", "周三", "周四", "周五", "周六"}
		if len(peakDays) > 0 && len(troughDays) > 0 {
			rec = fmt.Sprintf("虚拟机 %s 具有明显的周周期模式，建议在低谷日期（%s）关机",
				vmName, joinDays(dayNames, troughDays))
		} else {
			rec = fmt.Sprintf("虚拟机 %s 具有周周期模式，建议根据工作日/周末调整运行策略", vmName)
		}
	}

	return rec
}

// joinDays 连接日期名称
func joinDays(dayNames []string, days []int) string {
	if len(days) == 0 {
		return ""
	}

	result := dayNames[days[0]]
	for i := 1; i < len(days); i++ {
		result += "、" + dayNames[days[i]]
	}
	return result
}

// estimateTidalSaving 估算潮汐节省
func estimateTidalSaving(stabilityScore float64) string {
	// 稳定性越高，节省越大
	if stabilityScore >= 80 {
		return "约 50-70%"
	} else if stabilityScore >= 60 {
		return "约 30-50%"
	}
	return "约 10-30%"
}
