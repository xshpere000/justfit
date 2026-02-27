// Package analyzer 提供资源配置分析功能
package analyzer

import (
	"fmt"
	"math"
	"sort"
	"time"

	"justfit/internal/storage"
)

// RightSizeResult Right Size 分析结果
type RightSizeResult struct {
	VMAnalysisResult
	CurrentCPU      int32 `json:"currentCpu"`
	CurrentMemoryMB int32 `json:"currentMemoryMb"`

	// 分析数据
	CPUP95     float64 `json:"cpuP95"`     // 95分位 CPU 使用率
	CPUPeak    float64 `json:"cpuPeak"`    // 峰值 CPU 使用率
	CPUAvg     float64 `json:"cpuAvg"`     // 平均 CPU 使用率
	MemoryP95  float64 `json:"memoryP95"`  // 95分位内存使用率
	MemoryPeak float64 `json:"memoryPeak"` // 峰值内存使用率
	MemoryAvg  float64 `json:"memoryAvg"`  // 平均内存使用率

	// 推荐配置
	RecommendedCPU      int32  `json:"recommendedCpu"`
	RecommendedMemoryMB int32  `json:"recommendedMemoryMb"`
	AdjustmentType      string `json:"adjustmentType"` // "大幅缩容", "小幅缩容", "保持", "小幅扩容", "大幅扩容"

	// 评估
	RiskLevel       string  `json:"riskLevel"`       // "低", "中", "高"
	EstimatedSaving string  `json:"estimatedSaving"` // 节省估算
	Confidence      float64 `json:"confidence"`      // 置信度
}

// RightSizeConfig Right Size 分析配置
type RightSizeConfig struct {
	AnalysisDays int     // 分析天数
	BufferRatio  float64 // 缓冲比例 (默认 0.2)
	P95Threshold float64 // P95 阈值
	SmallMargin  float64 // 小幅调整阈值
	LargeMargin  float64 // 大幅调整阈值
}

// DefaultRightSizeConfig 默认 Right Size 配置
func DefaultRightSizeConfig() *RightSizeConfig {
	return &RightSizeConfig{
		AnalysisDays: 7,
		BufferRatio:  1.2, // 默认 1.2倍 (预留20%)
		P95Threshold: 95.0,
		SmallMargin:  0.3, // 30%
		LargeMargin:  0.7, // 70%
	}
}

// AnalyzeRightSize 分析资源配置合理性
func (e *Engine) AnalyzeRightSize(taskID, connectionID uint, config *RightSizeConfig) ([]RightSizeResult, error) {
	if config == nil {
		config = DefaultRightSizeConfig()
	}

	// 兼容前端可能传过来的 0.X 格式
	if config.BufferRatio < 1.0 {
		config.BufferRatio += 1.0
	}

	// 获取虚拟机列表
	vms, err := e.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -config.AnalysisDays)

	var results []RightSizeResult

	for _, vm := range vms {
		// 跳过已关机的虚拟机
		if vm.PowerState != "poweredOn" {
			continue
		}

		// 获取 CPU 指标 (单位: Cores, 使用 TaskID 过滤)
		cpuMetrics, err := e.repos.Metric.ListByTaskAndVMAndType(taskID, vm.ID, "cpu", startTime, endTime)
		if err != nil || len(cpuMetrics) == 0 {
			continue
		}

		// 获取内存指标 (单位: MB, 使用 TaskID 过滤)
		memMetrics, err := e.repos.Metric.ListByTaskAndVMAndType(taskID, vm.ID, "memory", startTime, endTime)
		if err != nil || len(memMetrics) == 0 {
			continue
		}

		// 计算统计值
		cpuValues := extractMetricValues(cpuMetrics)
		memValues := extractMetricValues(memMetrics)

		cpuP95 := percentile(cpuValues, config.P95Threshold)
		cpuPeak := max(cpuValues)
		cpuAvg := average(cpuValues)

		memP95 := percentile(memValues, config.P95Threshold)
		memPeak := max(memValues)
		memAvg := average(memValues)

		// 计算推荐配置
		recCPU := calculateRecommendedCPU(cpuP95, config.BufferRatio)
		recMem := calculateRecommendedMemory(memP95, config.BufferRatio)

		// 确定调整类型
		adjType := determineAdjustmentType(vm.CpuCount, recCPU, vm.MemoryMB, recMem, config)

		// 评估风险 (需要传入当前配置以计算波动率)
		riskLevel := assessRightSizeRisk(cpuValues, memValues, float64(vm.CpuCount), float64(vm.MemoryMB))

		// 估算节省
		saving := estimateSaving(vm.CpuCount, recCPU, vm.MemoryMB, recMem)

		result := RightSizeResult{
			VMAnalysisResult: VMAnalysisResult{
				VMKey:      vm.VMKey,
				VMName:     vm.Name,
				Datacenter: vm.Datacenter,
				Host:       vm.HostName,
				CPUCount:   vm.CpuCount,
				MemoryMB:   vm.MemoryMB,
				PowerState: string(vm.PowerState),
			},
			CurrentCPU:          vm.CpuCount,
			CurrentMemoryMB:     vm.MemoryMB,
			CPUP95:              cpuP95,
			CPUPeak:             cpuPeak,
			CPUAvg:              cpuAvg,
			MemoryP95:           memP95,
			MemoryPeak:          memPeak,
			MemoryAvg:           memAvg,
			RecommendedCPU:      recCPU,
			RecommendedMemoryMB: recMem,
			AdjustmentType:      adjType,
			RiskLevel:           riskLevel,
			EstimatedSaving:     saving,
			Confidence:          calculateRightSizeConfidence(len(cpuValues), len(memValues), config.AnalysisDays),
		}

		results = append(results, result)
	}

	return results, nil
}

// extractMetricValues 提取指标值
func extractMetricValues(metrics []storage.Metric) []float64 {
	values := make([]float64, len(metrics))
	for i, m := range metrics {
		values[i] = m.Value
	}
	return values
}

// percentile 计算百分位数
func percentile(values []float64, p float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sorted := make([]float64, len(values))
	copy(sorted, values)
	sortFloats(sorted)

	index := (p / 100) * float64(len(sorted)-1)
	low := int(math.Floor(index))
	high := int(math.Ceil(index))

	if low == high {
		return sorted[low]
	}

	return sorted[low]*(float64(high)-index) + sorted[high]*(index-float64(low))
}

// sortFloats 排序浮点数切片
func sortFloats(values []float64) {
	sort.Slice(values, func(i, j int) bool {
		return values[i] < values[j]
	})
}

// max 获取最大值
func max(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	m := values[0]
	for _, v := range values[1:] {
		if v > m {
			m = v
		}
	}
	return m
}

// calculateRecommendedCPU 计算推荐的 CPU 配置
func calculateRecommendedCPU(usageP95 float64, bufferRatio float64) int32 {
	// usageP95 单位为 Cores
	// bufferRatio 例如 1.2
	requiredCPU := usageP95 * bufferRatio

	// 规范化到 1, 2, 4, 8, 16, 32, 64, 128
	return normalizeCPU(int32(math.Ceil(requiredCPU)))
}

// normalizeCPU 规范化 CPU 数量
func normalizeCPU(cpu int32) int32 {
	standards := []int32{1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128}

	for _, s := range standards {
		if cpu <= s {
			return s
		}
	}
	return 128
}

// calculateRecommendedMemory 计算推荐的内存配置
func calculateRecommendedMemory(usageP95 float64, bufferRatio float64) int32 {
	// usageP95 单位为 MB
	requiredMem := usageP95 * bufferRatio

	// 规范化到 512MB 的倍数
	return normalizeMemory(int32(math.Ceil(requiredMem)))
}

// normalizeMemory 规范化内存大小 (以 512MB 为单位)
func normalizeMemory(memMB int32) int32 {
	// 最小 512MB
	if memMB < 512 {
		return 512
	}

	// 规范化算法：
	// < 4GB (4096): 512MB 步进
	// < 16GB: 1GB 步进
	// >= 16GB: 2GB 步进

	if memMB < 4096 {
		return ((memMB + 511) / 512) * 512
	} else if memMB < 16384 {
		return ((memMB + 1023) / 1024) * 1024
	} else {
		return ((memMB + 2047) / 2048) * 2048
	}
}

// determineAdjustmentType 确定调整类型
func determineAdjustmentType(currentCPU, recCPU int32, currentMem, recMem int32, config *RightSizeConfig) string {
	cpuRatio := float64(recCPU) / float64(currentCPU)
	memRatio := float64(recMem) / float64(currentMem)
	avgRatio := (cpuRatio + memRatio) / 2

	if avgRatio <= (1 - config.LargeMargin) {
		return "大幅缩容"
	} else if avgRatio <= (1 - config.SmallMargin) {
		return "小幅缩容"
	} else if avgRatio >= (1 + config.LargeMargin) {
		return "大幅扩容"
	} else if avgRatio >= (1 + config.SmallMargin) {
		return "小幅扩容"
	}

	return "保持"
}

// assessRightSizeRisk 评估调整风险
func assessRightSizeRisk(cpuValues, memValues []float64, currentCPUCap, currentMemCap float64) string {
	// 计算标准差
	cpuStd := stdDev(cpuValues)
	memStd := stdDev(memValues)

	// 计算变异系数 (CV) 或 相对标准差
	// 如果容量为0 (不可能)，处理为0
	var cpuStdPercent, memStdPercent float64
	if currentCPUCap > 0 {
		cpuStdPercent = (cpuStd / currentCPUCap) * 100
	}
	if currentMemCap > 0 {
		memStdPercent = (memStd / currentMemCap) * 100
	}

	// 高波动表示从平均值偏离较大，风险较高
	if cpuStdPercent > 40 || memStdPercent > 40 {
		return "高"
	} else if cpuStdPercent > 20 || memStdPercent > 20 {
		return "中"
	}
	return "低"
}

// stdDev 计算标准差
func stdDev(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	avg := average(values)
	sum := 0.0
	for _, v := range values {
		diff := v - avg
		sum += diff * diff
	}

	return math.Sqrt(sum / float64(len(values)))
}

// estimateSaving 估算节省
func estimateSaving(currentCPU, recCPU int32, currentMem, recMem int32) string {
	cpuSaving := (1 - float64(recCPU)/float64(currentCPU)) * 100
	memSaving := (1 - float64(recMem)/float64(currentMem)) * 100

	if cpuSaving <= 0 && memSaving <= 0 {
		return "无节省（需要扩容）"
	}

	avgSaving := (cpuSaving + memSaving) / 2
	return fmt.Sprintf("约 %.1f%%", avgSaving)
}

// calculateRightSizeConfidence 计算 Right Size 置信度
func calculateRightSizeConfidence(cpuSamples, memSamples int, analysisDays int) float64 {
	// 数据点越多，置信度越高
	expectedSamples := analysisDays * 288 // 5分钟间隔，每天288个点

	ratio := float64(cpuSamples+memSamples) / (2 * float64(expectedSamples))

	confidence := ratio * 100
	if confidence > 100 {
		confidence = 100
	}

	return confidence
}
