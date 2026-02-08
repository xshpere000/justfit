// Package analyzer 提供资源分析功能
package analyzer

import (
	"fmt"
	"math"
	"time"

	"justfit/internal/storage"
)

// Engine 分析引擎
type Engine struct {
	repos *storage.Repositories
}

// NewEngine 创建分析引擎
func NewEngine(repos *storage.Repositories) *Engine {
	return &Engine{repos: repos}
}

// VMAnalysisResult 虚拟机分析结果
type VMAnalysisResult struct {
	VMKey      string `json:"vm_key"`
	VMName     string `json:"vm_name"`
	Datacenter string `json:"datacenter"`
	Host       string `json:"host"`
	CPUCount   int32  `json:"cpu_count"`
	MemoryMB   int32  `json:"memory_mb"`
	PowerState string `json:"power_state"`
}

// ZombieVMResult 僵尸 VM 分析结果
type ZombieVMResult struct {
	VMAnalysisResult
	CPUUsage       float64  `json:"cpu_usage"`      // 平均 CPU 使用率
	MemoryUsage    float64  `json:"memory_usage"`   // 平均内存使用率
	DiskIORate     float64  `json:"disk_io_rate"`   // 平均磁盘 I/O 速率
	NetworkRate    float64  `json:"network_rate"`   // 平均网络速率
	Confidence     float64  `json:"confidence"`     // 置信度 0-100
	DaysLowUsage   int      `json:"days_low_usage"` // 低负载天数
	Evidence       []string `json:"evidence"`       // 证据列表
	Recommendation string   `json:"recommendation"`
}

// ZombieVMConfig 僵尸 VM 检测配置
type ZombieVMConfig struct {
	AnalysisDays     int     // 分析天数
	CPUThreshold     float64 // CPU 阈值 (%)
	MemoryThreshold  float64 // 内存阈值 (%)
	IOThreshold      float64 // I/O 阈值
	NetworkThreshold float64 // 网络阈值
	MinConfidence    float64 // 最小置信度
}

// DefaultZombieVMConfig 默认僵尸 VM 检测配置
func DefaultZombieVMConfig() *ZombieVMConfig {
	return &ZombieVMConfig{
		AnalysisDays:     14,
		CPUThreshold:     5.0,
		MemoryThreshold:  10.0,
		IOThreshold:      10.0,
		NetworkThreshold: 10.0,
		MinConfidence:    80.0,
	}
}

// DetectZombieVMs 检测僵尸虚拟机
func (e *Engine) DetectZombieVMs(connectionID uint, config *ZombieVMConfig) ([]ZombieVMResult, error) {
	if config == nil {
		config = DefaultZombieVMConfig()
	}

	// 获取虚拟机列表
	vms, err := e.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -config.AnalysisDays)

	var results []ZombieVMResult

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

		// 获取内存指标
		memMetrics, err := e.repos.Metric.ListByVMAndType(vm.ID, "memory", startTime, endTime)
		if err != nil || len(memMetrics) == 0 {
			continue
		}

		// 计算平均值 (绝对值)
		avgCPUAbs := averageMetrics(cpuMetrics)
		avgMemoryAbs := averageMetrics(memMetrics)

		// 转换为百分比
		var avgCPUPercent, avgMemoryPercent float64
		if vm.CpuCount > 0 {
			avgCPUPercent = (avgCPUAbs / float64(vm.CpuCount)) * 100
		}
		if vm.MemoryMB > 0 {
			avgMemoryPercent = (avgMemoryAbs / float64(vm.MemoryMB)) * 100
		}

		// 获取 I/O 指标（可选）
		diskReadMetrics, _ := e.repos.Metric.ListByVMAndType(vm.ID, "disk_read", startTime, endTime)
		diskWriteMetrics, _ := e.repos.Metric.ListByVMAndType(vm.ID, "disk_write", startTime, endTime)
		netRxMetrics, _ := e.repos.Metric.ListByVMAndType(vm.ID, "net_rx", startTime, endTime)
		netTxMetrics, _ := e.repos.Metric.ListByVMAndType(vm.ID, "net_tx", startTime, endTime)

		avgDiskIO := (averageMetrics(diskReadMetrics) + averageMetrics(diskWriteMetrics)) / 2
		avgNetwork := (averageMetrics(netRxMetrics) + averageMetrics(netTxMetrics)) / 2

		// 计算低负载天数 (需要将百分比阈值转为绝对值阈值进行比较)
		absCPUThreshold := (config.CPUThreshold / 100.0) * float64(vm.CpuCount)
		absMemThreshold := (config.MemoryThreshold / 100.0) * float64(vm.MemoryMB)

		lowUsageDays := calculateLowUsageDays(cpuMetrics, memMetrics, absCPUThreshold, absMemThreshold)

		// 计算置信度 (使用百分比)
		confidence := calculateZombieConfidence(avgCPUPercent, avgMemoryPercent, avgDiskIO, avgNetwork, lowUsageDays, config.AnalysisDays)

		// 判断是否为僵尸 VM
		if confidence >= config.MinConfidence {
			result := ZombieVMResult{
				VMAnalysisResult: VMAnalysisResult{
					VMKey:      vm.VMKey,
					VMName:     vm.Name,
					Datacenter: vm.Datacenter,
					Host:       vm.HostName,
					CPUCount:   vm.CpuCount,
					MemoryMB:   vm.MemoryMB,
					PowerState: string(vm.PowerState),
				},
				CPUUsage:       avgCPUPercent,    // 返回百分比
				MemoryUsage:    avgMemoryPercent, // 返回百分比
				DiskIORate:     avgDiskIO,
				NetworkRate:    avgNetwork,
				Confidence:     confidence,
				DaysLowUsage:   lowUsageDays,
				Evidence:       buildZombieEvidence(avgCPUPercent, avgMemoryPercent, avgDiskIO, avgNetwork, lowUsageDays, config),
				Recommendation: buildZombieRecommendation(vm.Name, confidence),
			}
			results = append(results, result)
		}
	}

	return results, nil
}

// averageMetrics 计算指标平均值
func averageMetrics(metrics []storage.Metric) float64 {
	if len(metrics) == 0 {
		return 0
	}

	sum := 0.0
	for _, m := range metrics {
		sum += m.Value
	}
	return sum / float64(len(metrics))
}

// calculateLowUsageDays 计算低负载天数
func calculateLowUsageDays(cpuMetrics, memMetrics []storage.Metric, absCpuThreshold, absMemThreshold float64) int {
	// 按天分组
	type DayAccumulator struct {
		CpuSum   float64
		CpuCount int
		MemSum   float64
		MemCount int
	}
	dailyData := make(map[string]*DayAccumulator)

	for _, m := range cpuMetrics {
		day := m.Timestamp.Format("2006-01-02")
		if _, exists := dailyData[day]; !exists {
			dailyData[day] = &DayAccumulator{}
		}
		dailyData[day].CpuSum += m.Value
		dailyData[day].CpuCount++
	}

	for _, m := range memMetrics {
		day := m.Timestamp.Format("2006-01-02")
		if _, exists := dailyData[day]; !exists {
			dailyData[day] = &DayAccumulator{}
		}
		dailyData[day].MemSum += m.Value
		dailyData[day].MemCount++
	}

	// 统计低负载天数
	lowDays := 0
	for _, acc := range dailyData {
		avgCpu := 0.0
		if acc.CpuCount > 0 {
			avgCpu = acc.CpuSum / float64(acc.CpuCount)
		}

		avgMem := 0.0
		if acc.MemCount > 0 {
			avgMem = acc.MemSum / float64(acc.MemCount)
		}

		// 判断：CPU 和 内存的平均绝对值 都低于 绝对阈值
		// 或者使用 平均使用率 < 阈值 ?
		// 这里使用 绝对值 < 绝对阈值
		if avgCpu < absCpuThreshold && avgMem < absMemThreshold {
			lowDays++
		}
	}

	return lowDays
}

// average 计算浮点数切片平均值
func average(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

// calculateZombieConfidence 计算僵尸 VM 置信度
func calculateZombieConfidence(cpu, memory, diskIO, network float64, lowDays, totalDays int) float64 {
	score := 0.0
	weights := 0.0

	// CPU 使用率评分 (40% 权重)
	if cpu < 5 {
		score += 40
	} else if cpu < 10 {
		score += 30
	} else if cpu < 20 {
		score += 10
	}
	weights += 40

	// 内存使用率评分 (30% 权重)
	if memory < 10 {
		score += 30
	} else if memory < 20 {
		score += 20
	} else if memory < 30 {
		score += 10
	}
	weights += 30

	// I/O 评分 (15% 权重)
	if diskIO < 10 {
		score += 15
	} else if diskIO < 50 {
		score += 5
	}
	weights += 15

	// 网络评分 (15% 权重)
	if network < 10 {
		score += 15
	} else if network < 50 {
		score += 5
	}
	weights += 15

	// 低负载天数加成
	if totalDays > 0 {
		dayRatio := float64(lowDays) / float64(totalDays)
		if dayRatio > 0.8 {
			score += 10
		} else if dayRatio > 0.5 {
			score += 5
		}
	}

	return math.Min(100, score)
}

// buildZombieEvidence 构建证据列表
func buildZombieEvidence(cpu, memory, diskIO, network float64, lowDays int, config *ZombieVMConfig) []string {
	var evidence []string

	if cpu < config.CPUThreshold {
		evidence = append(evidence, fmt.Sprintf("CPU 平均使用率 %.2f%% 低于阈值 %.2f%%", cpu, config.CPUThreshold))
	}

	if memory < config.MemoryThreshold {
		evidence = append(evidence, fmt.Sprintf("内存平均使用率 %.2f%% 低于阈值 %.2f%%", memory, config.MemoryThreshold))
	}

	if diskIO < config.IOThreshold {
		evidence = append(evidence, fmt.Sprintf("磁盘 I/O 平均速率 %.2f 低于阈值 %.2f", diskIO, config.IOThreshold))
	}

	if network < config.NetworkThreshold {
		evidence = append(evidence, fmt.Sprintf("网络平均速率 %.2f 低于阈值 %.2f", network, config.NetworkThreshold))
	}

	if lowDays > 0 {
		evidence = append(evidence, fmt.Sprintf("在过去 %d 天中有 %d 天处于低负载状态", config.AnalysisDays, lowDays))
	}

	return evidence
}

// buildZombieRecommendation 构建建议
func buildZombieRecommendation(vmName string, confidence float64) string {
	if confidence >= 90 {
		return fmt.Sprintf("虚拟机 %s 极有可能是僵尸机，建议关机或删除", vmName)
	} else if confidence >= 80 {
		return fmt.Sprintf("虚拟机 %s 很可能是僵尸机，建议进一步确认后处理", vmName)
	}
	return fmt.Sprintf("虚拟机 %s 可能是僵尸机，建议关注", vmName)
}
