// Package analyzer 提供平台健康度分析功能
package analyzer

import (
	"fmt"
	"math"

	"justfit/internal/storage"
)

// HealthScoreResult 健康评分结果
type HealthScoreResult struct {
	ConnectionID   uint   `json:"connection_id"`
	ConnectionName string `json:"connection_name"`

	// 总分
	OverallScore float64 `json:"overall_score"` // 0-100
	HealthLevel  string  `json:"health_level"`  // "优秀", "良好", "一般", "较差", "差"

	// 维度得分
	ResourceBalance      float64 `json:"resource_balance"`      // 资源均衡度 0-100
	OvercommitRisk       float64 `json:"overcommit_risk"`       // 超配风险 0-100
	HotspotConcentration float64 `json:"hotspot_concentration"` // 热点集中度 0-100

	// 详情
	TotalClusters int     `json:"total_clusters"`
	TotalHosts    int     `json:"total_hosts"`
	TotalVMs      int     `json:"total_vms"`
	TotalCPUCores int64   `json:"total_cpu_cores"`
	TotalMemoryGB float64 `json:"total_memory_gb"`

	AvgCPUUsage    float64 `json:"avg_cpu_usage"`
	AvgMemoryUsage float64 `json:"avg_memory_usage"`

	// 风险项
	RiskItems       []string `json:"risk_items"`
	Recommendations []string `json:"recommendations"`
}

// HealthConfig 健康评分配置
type HealthConfig struct {
	ResourceBalanceWeight float64 // 资源均衡度权重
	OvercommitRiskWeight  float64 // 超配风险权重
	HotspotWeight         float64 // 热点集中度权重
}

// DefaultHealthConfig 默认健康评分配置
func DefaultHealthConfig() *HealthConfig {
	return &HealthConfig{
		ResourceBalanceWeight: 0.4,
		OvercommitRiskWeight:  0.3,
		HotspotWeight:         0.3,
	}
}

// AnalyzeHealthScore 分析平台健康度
func (e *Engine) AnalyzeHealthScore(connectionID uint, config *HealthConfig) (*HealthScoreResult, error) {
	if config == nil {
		config = DefaultHealthConfig()
	}

	// 获取连接信息
	conn, err := e.repos.Connection.GetByID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取连接失败: %w", err)
	}

	// 获取集群列表
	clusters, err := e.repos.Cluster.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取集群列表失败: %w", err)
	}

	// 获取主机列表
	hosts, err := e.repos.Host.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取主机列表失败: %w", err)
	}

	// 获取虚拟机列表
	vms, err := e.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	// 计算各维度得分
	resourceBalance := calculateResourceBalance(hosts)
	overcommitRisk := calculateOvercommitRisk(hosts, vms)
	hotspotConcentration := calculateHotspotConcentration(hosts, vms)

	// 计算总分
	overallScore := resourceBalance*config.ResourceBalanceWeight +
		overcommitRisk*config.OvercommitRiskWeight +
		hotspotConcentration*config.HotspotWeight

	// 确定健康等级
	healthLevel := determineHealthLevel(overallScore)

	// 统计总资源
	totalCPUCores := int64(0)
	totalMemoryGB := 0.0
	for _, host := range hosts {
		totalCPUCores += int64(host.CpuCores)
		totalMemoryGB += float64(host.Memory) / (1024 * 1024 * 1024)
	}

	// 收集风险项和建议
	riskItems := collectRiskItems(resourceBalance, overcommitRisk, hotspotConcentration)
	recommendations := generateHealthRecommendations(riskItems, hosts, vms)

	result := &HealthScoreResult{
		ConnectionID:         connectionID,
		ConnectionName:       conn.Name,
		OverallScore:         overallScore,
		HealthLevel:          healthLevel,
		ResourceBalance:      resourceBalance,
		OvercommitRisk:       overcommitRisk,
		HotspotConcentration: hotspotConcentration,
		TotalClusters:        len(clusters),
		TotalHosts:           len(hosts),
		TotalVMs:             len(vms),
		TotalCPUCores:        totalCPUCores,
		TotalMemoryGB:        totalMemoryGB,
		RiskItems:            riskItems,
		Recommendations:      recommendations,
	}

	return result, nil
}

// calculateResourceBalance 计算资源均衡度
func calculateResourceBalance(hosts []storage.Host) float64 {
	if len(hosts) == 0 {
		return 0
	}

	// 计算每台主机的 VM 数量
	vmCounts := make([]int, len(hosts))
	for i, host := range hosts {
		vmCounts[i] = host.NumVMs
	}

	// 计算标准差
	mean := 0.0
	for _, count := range vmCounts {
		mean += float64(count)
	}
	mean /= float64(len(vmCounts))

	variance := 0.0
	for _, count := range vmCounts {
		diff := float64(count) - mean
		variance += diff * diff
	}
	variance /= float64(len(vmCounts))

	stdDev := math.Sqrt(variance)

	// 标准差越小，均衡度越高
	// 使用变异系数 (CV = std/mean) 来评估
	if mean == 0 {
		return 0
	}

	cv := stdDev / mean

	// CV < 0.3 优秀, CV < 0.5 良好, CV < 0.8 一般
	if cv < 0.3 {
		return 100
	} else if cv < 0.5 {
		return 80
	} else if cv < 0.8 {
		return 60
	} else if cv < 1.2 {
		return 40
	}
	return 20
}

// calculateOvercommitRisk 计算超配风险
func calculateOvercommitRisk(hosts []storage.Host, vms []storage.VM) float64 {
	if len(hosts) == 0 {
		return 50
	}

	// 计算总配置资源
	totalVMCPUs := int32(0)
	totalVMMemMB := int32(0)
	for _, vm := range vms {
		if vm.PowerState == "poweredOn" {
			totalVMCPUs += vm.CpuCount
			totalVMMemMB += vm.MemoryMB
		}
	}

	// 计算总物理资源
	totalHostCPUs := int32(0)
	totalHostMemMB := int32(0)
	for _, host := range hosts {
		totalHostCPUs += host.CpuCores
		totalHostMemMB += int32(host.Memory / (1024 * 1024))
	}

	// 计算超配比
	cpuOvercommit := 1.0
	memOvercommit := 1.0
	if totalHostCPUs > 0 {
		cpuOvercommit = float64(totalVMCPUs) / float64(totalHostCPUs)
	}
	if totalHostMemMB > 0 {
		memOvercommit = float64(totalVMMemMB) / float64(totalHostMemMB)
	}

	// 超配比越高，风险越低（分数越高）
	// 但超配过高也会有问题
	// 合理范围: CPU 2-4倍, 内存 1.5-2倍

	cpuScore := scoreOvercommit(cpuOvercommit, 2.0, 4.0)
	memScore := scoreOvercommit(memOvercommit, 1.5, 2.5)

	return (cpuScore + memScore) / 2
}

// scoreOvercommit 评分超配比
func scoreOvercommit(ratio, minIdeal, maxIdeal float64) float64 {
	if ratio < minIdeal {
		// 超配不足，资源浪费
		return ratio / minIdeal * 50
	} else if ratio <= maxIdeal {
		// 理想范围
		return 100
	} else if ratio <= maxIdeal*2 {
		// 轻度超配
		return 100 - (ratio-maxIdeal)/(maxIdeal)*30
	}
	// 重度超配
	return 40 - (ratio-maxIdeal*2)/(maxIdeal)*20
}

// calculateHotspotConcentration 计算热点集中度
func calculateHotspotConcentration(hosts []storage.Host, vms []storage.VM) float64 {
	if len(hosts) == 0 {
		return 50
	}

	// 计算每台主机的 VM 负载（按 vCPU 和内存）
	hostLoads := make([]float64, len(hosts))
	hostMap := make(map[string]int)

	for i, host := range hosts {
		hostMap[host.Name] = i
	}

	for _, vm := range vms {
		if vm.PowerState != "poweredOn" {
			continue
		}
		if idx, ok := hostMap[vm.HostName]; ok {
			// 简单负载计算: vCPU + 内存权重
			load := float64(vm.CpuCount) + float64(vm.MemoryMB)/8192
			hostLoads[idx] += load
		}
	}

	// 计算基尼系数来评估集中度
	sortedLoads := make([]float64, len(hostLoads))
	copy(sortedLoads, hostLoads)
	sortFloats(sortedLoads)

	// 过滤掉零负载的主机
	validLoads := make([]float64, 0)
	for _, load := range sortedLoads {
		if load > 0 {
			validLoads = append(validLoads, load)
		}
	}

	if len(validLoads) == 0 {
		return 100 // 没有负载，无热点
	}

	// 计算基尼系数
	n := float64(len(validLoads))
	sum := 0.0
	for _, load := range validLoads {
		sum += load
	}

	if sum == 0 {
		return 100
	}

	// 归一化
	normalizedLoads := make([]float64, len(validLoads))
	for _, load := range validLoads {
		normalizedLoads = append(normalizedLoads, load/sum)
	}

	// 计算基尼系数
	gini := 0.0
	for _, xi := range normalizedLoads {
		for _, xj := range normalizedLoads {
			gini += math.Abs(xi - xj)
		}
	}
	gini = gini / (2 * n)

	// 基尼系数越小，分布越均匀
	// 转换为分数: 均匀=100, 极度集中=0
	return (1 - gini) * 100
}

// determineHealthLevel 确定健康等级
func determineHealthLevel(score float64) string {
	if score >= 90 {
		return "优秀"
	} else if score >= 75 {
		return "良好"
	} else if score >= 60 {
		return "一般"
	} else if score >= 40 {
		return "较差"
	}
	return "差"
}

// collectRiskItems 收集风险项
func collectRiskItems(resourceBalance, overcommitRisk, hotspotConcentration float64) []string {
	var risks []string

	if resourceBalance < 60 {
		risks = append(risks, "资源分布不均衡，部分主机负载过高")
	}

	if overcommitRisk < 60 {
		risks = append(risks, "超配比例过高或过低，存在资源浪费或性能风险")
	}

	if hotspotConcentration < 60 {
		risks = append(risks, "存在明显的热点主机，负载集中度过高")
	}

	return risks
}

// generateHealthRecommendations 生成健康建议
func generateHealthRecommendations(risks []string, hosts []storage.Host, vms []storage.VM) []string {
	var recommendations []string

	// 基于风险项生成建议
	if len(risks) > 0 {
		recommendations = append(recommendations, "建议进行资源重新分配以平衡负载")
	}

	// 检查是否有僵尸 VM
	zombieCount := 0
	for _, vm := range vms {
		if vm.PowerState == "poweredOn" {
			// 简单判断：低配置 VM 可能是僵尸
			if vm.CpuCount <= 2 && vm.MemoryMB <= 2048 {
				zombieCount++
			}
		}
	}
	if zombieCount > 5 {
		recommendations = append(recommendations, fmt.Sprintf("发现 %d 个可能的低配置虚拟机，建议进行僵尸 VM 分析", zombieCount))
	}

	// 检查是否需要扩容
	if len(hosts) > 0 {
		avgVMsPerHost := float64(len(vms)) / float64(len(hosts))
		if avgVMsPerHost > 50 {
			recommendations = append(recommendations, "平均每台主机虚拟机数量较多，建议考虑扩容")
		}
	}

	return recommendations
}
