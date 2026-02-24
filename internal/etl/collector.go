// Package etl 提供数据采集服务
package etl

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"justfit/internal/connector"
	"justfit/internal/storage"
)

// Collector 数据采集器
type Collector struct {
	connMgr   *connector.ConnectorManager
	processor *Processor
	repos     *storage.Repositories
}

// NewCollector 创建采集器
func NewCollector(connMgr *connector.ConnectorManager, repos *storage.Repositories) *Collector {
	return &Collector{
		connMgr:   connMgr,
		processor: NewProcessor(repos),
		repos:     repos,
	}
}

// CollectionConfig 采集配置
type CollectionConfig struct {
	ConnectionID uint
	DataTypes    []string // clusters, hosts, vms, metrics
	MetricsDays  int      // 采集多少天的指标数据
	Concurrency  int      // 并发数
	Password     string   // 密码覆盖
	SelectedVMs  []string // 用户选择的虚拟机 vmKey 列表，为空则采集所有
}

// CollectionResult 采集结果
type CollectionResult struct {
	Success  bool
	Message  string
	Clusters int
	Hosts    int
	VMs      int
	Metrics  int
	Duration time.Duration
}

// MetricsCollectionStats 指标采集统计
type MetricsCollectionStats struct {
	TotalVMs             int      `json:"total_vms"`
	ScopedVMs            int      `json:"scoped_vms"`
	SkippedPoweredOff    int      `json:"skipped_powered_off"`
	SkippedAbnormal      int      `json:"skipped_abnormal"` // 跳过的异常状态虚拟机
	CollectedVMs         int      `json:"collected_vms"`
	FailedVMCount        int      `json:"failed_vm_count"`
	CollectedMetricCount int      `json:"collected_metric_count"`
	FailedMetricCount    int      `json:"failed_metric_count"`
	Scope                string   `json:"scope"`
	Reasons              []string `json:"reasons"`
}

// Collect 执行数据采集
func (c *Collector) Collect(ctx context.Context, config *CollectionConfig) (*CollectionResult, error) {
	startTime := time.Now()

	// 获取连接配置
	conn, err := c.repos.Connection.GetByID(config.ConnectionID)
	if err != nil {
		return nil, fmt.Errorf("获取连接失败: %w", err)
	}

	if config.Password != "" {
		conn.Password = config.Password
	}

	// 更新连接状态
	c.repos.Connection.UpdateStatus(config.ConnectionID, "connecting")

	// 创建连接器
	connConfig := &connector.ConnectionConfig{
		ID:       conn.ID,
		Name:     conn.Name,
		Platform: connector.PlatformType(conn.Platform),
		Host:     conn.Host,
		Port:     conn.Port,
		Username: conn.Username,
		Password: conn.Password,
		Insecure: conn.Insecure,
	}

	client, err := c.connMgr.Get(connConfig)
	if err != nil {
		c.repos.Connection.UpdateStatus(config.ConnectionID, "error")
		return nil, fmt.Errorf("创建连接器失败: %w", err)
	}

	// 测试连接
	if err := client.TestConnection(); err != nil {
		c.repos.Connection.UpdateStatus(config.ConnectionID, "error")
		return nil, fmt.Errorf("连接测试失败: %w", err)
	}

	c.repos.Connection.UpdateStatus(config.ConnectionID, "connected")

	result := &CollectionResult{}

	// 使用 WaitGroup 进行并发采集
	var wg sync.WaitGroup
	var mu sync.Mutex
	errors := make([]error, 0)

	// 采集集群
	if contains(config.DataTypes, "clusters") {
		wg.Add(1)
		go func() {
			defer wg.Done()
			clusters, err := client.GetClusters()
			if err != nil {
				mu.Lock()
				errors = append(errors, fmt.Errorf("采集集群失败: %w", err))
				mu.Unlock()
				return
			}

			for _, cluster := range clusters {
				if err := c.processor.ProcessCluster(config.ConnectionID, cluster); err != nil {
					mu.Lock()
					errors = append(errors, fmt.Errorf("处理集群 %s 失败: %w", cluster.Name, err))
					mu.Unlock()
				}
			}

			mu.Lock()
			result.Clusters = len(clusters)
			mu.Unlock()
		}()
	}

	// 采集主机
	if contains(config.DataTypes, "hosts") {
		wg.Add(1)
		go func() {
			defer wg.Done()
			hosts, err := client.GetHosts()
			if err != nil {
				mu.Lock()
				errors = append(errors, fmt.Errorf("采集主机失败: %w", err))
				mu.Unlock()
				return
			}

			for _, host := range hosts {
				if err := c.processor.ProcessHost(config.ConnectionID, host); err != nil {
					mu.Lock()
					errors = append(errors, fmt.Errorf("处理主机 %s 失败: %w", host.Name, err))
					mu.Unlock()
				}
			}

			mu.Lock()
			result.Hosts = len(hosts)
			mu.Unlock()
		}()
	}

	// 采集虚拟机
	if contains(config.DataTypes, "vms") {
		wg.Add(1)
		go func() {
			defer wg.Done()
			vms, err := client.GetVMs()
			if err != nil {
				mu.Lock()
				errors = append(errors, fmt.Errorf("采集虚拟机失败: %w", err))
				mu.Unlock()
				return
			}

			for _, vm := range vms {
				if err := c.processor.ProcessVM(config.ConnectionID, vm); err != nil {
					mu.Lock()
					errors = append(errors, fmt.Errorf("处理虚拟机 %s 失败: %w", vm.Name, err))
					mu.Unlock()
				}
			}

			mu.Lock()
			result.VMs = len(vms)
			mu.Unlock()
		}()
	}

	// 等待所有采集完成
	wg.Wait()

	// 更新最后同步时间
	now := time.Now()
	c.repos.Connection.UpdateLastSync(config.ConnectionID, now)

	result.Duration = time.Since(startTime)
	result.Success = len(errors) == 0

	if len(errors) > 0 {
		errorMsgs := make([]string, len(errors))
		for i, e := range errors {
			errorMsgs[i] = e.Error()
		}
		result.Message = fmt.Sprintf("采集完成，但有 %d 个错误: %s", len(errors), strings.Join(errorMsgs, "; "))
	} else {
		result.Message = "采集成功"
	}

	return result, nil
}

// CollectMetrics 采集性能指标
// selectedVMs: 用户选择的虚拟机 vmKey 列表，为空则采集所有符合条件的虚拟机
func (c *Collector) CollectMetrics(ctx context.Context, connectionID uint, days int, passwordOverride string, selectedVMs []string) (*MetricsCollectionStats, error) {
	stats := &MetricsCollectionStats{Scope: "poweredOn only"}
	reasonCounts := make(map[string]int)

	// 创建选中的虚拟机集合，用于快速查找
	selectedSet := make(map[string]bool)
	for _, vmKey := range selectedVMs {
		selectedSet[vmKey] = true
	}

	conn, err := c.repos.Connection.GetByID(connectionID)
	if err != nil {
		return stats, fmt.Errorf("获取连接失败: %w", err)
	}

	if passwordOverride != "" {
		conn.Password = passwordOverride
	}

	connConfig := &connector.ConnectionConfig{
		ID:       conn.ID,
		Name:     conn.Name,
		Platform: connector.PlatformType(conn.Platform),
		Host:     conn.Host,
		Port:     conn.Port,
		Username: conn.Username,
		Password: conn.Password,
		Insecure: conn.Insecure,
	}

	client, err := c.connMgr.Get(connConfig)
	if err != nil {
		return stats, fmt.Errorf("创建连接器失败: %w", err)
	}

	// 获取虚拟机列表
	vms, err := client.GetVMs()
	if err != nil {
		return stats, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}
	stats.TotalVMs = len(vms)

	// 先确保所有虚拟机都保存到数据库（ProcessVMMetrics 需要虚拟机已存在）
	for _, vm := range vms {
		if err := c.processor.ProcessVM(connectionID, vm); err != nil {
			// 记录错误但继续处理其他虚拟机
			addMetricReason(reasonCounts, fmt.Sprintf("%s: 保存虚拟机信息失败: %v", buildVMKey(vm), err))
		}
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -days)

	// 并发控制
	concurrency := 5 // 限制并发数，避免压垮 vCenter
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, concurrency)
	var mu sync.Mutex

	for _, vm := range vms {
		vmKey := buildVMKey(vm)

		// 如果用户指定了虚拟机列表，只采集选中的
		if len(selectedSet) > 0 && !selectedSet[vmKey] {
			stats.SkippedPoweredOff++ // 使用此计数表示被过滤掉的虚拟机
			continue
		}

		// 检查连接状态，跳过异常连接状态的虚拟机
		if vm.ConnectionState != "" && vm.ConnectionState != "connected" {
			stats.SkippedAbnormal++
			addMetricReason(reasonCounts, fmt.Sprintf("%s: 连接状态异常 (%s)", vmKey, vm.ConnectionState))
			continue
		}

		// 只采集开机状态的虚拟机
		if vm.PowerState != "poweredOn" {
			stats.SkippedPoweredOff++
			continue
		}
		stats.ScopedVMs++

		wg.Add(1)
		semaphore <- struct{}{} // 获取信号量

		go func(targetVM connector.VMInfo) {
			defer wg.Done()
			defer func() { <-semaphore }() // 释放信号量

			vmKey := buildVMKey(targetVM)
			metrics, err := client.GetVMMetrics(targetVM.Datacenter, targetVM.Name, targetVM.UUID, startTime, endTime, targetVM.CpuCount)
			if err != nil {
				mu.Lock()
				stats.FailedVMCount++
				stats.FailedMetricCount += 6
				addMetricReason(reasonCounts, fmt.Sprintf("%s: 获取指标失败: %v", vmKey, err))
				mu.Unlock()
				return
			}

			if err := c.processor.ProcessVMMetrics(vmKey, metrics); err != nil {
				mu.Lock()
				stats.FailedVMCount++
				stats.FailedMetricCount += 6
				addMetricReason(reasonCounts, fmt.Sprintf("%s: 写入指标失败: %v", vmKey, err))
				mu.Unlock()
				return
			}

			count := countMetrics(metrics)
			mu.Lock()
			if count == 0 {
				stats.FailedVMCount++
				stats.FailedMetricCount += 6
				addMetricReason(reasonCounts, fmt.Sprintf("%s: 指标为空", vmKey))
			} else {
				stats.CollectedVMs++
				stats.CollectedMetricCount += count
			}
			mu.Unlock()
		}(vm)
	}

	wg.Wait()
	stats.Reasons = renderMetricReasons(reasonCounts)

	if stats.CollectedVMs == 0 && stats.ScopedVMs > 0 {
		reasonStr := ""
		if len(stats.Reasons) > 0 {
			reasonStr = "\n失败原因: " + stats.Reasons[0]
			if len(stats.Reasons) > 1 {
				reasonStr += fmt.Sprintf(" 等 %d 种原因", len(stats.Reasons))
			}
		}
		return stats, fmt.Errorf("性能指标采集失败：已筛选 %d 台开机虚拟机，但全部采集失败%s", stats.ScopedVMs, reasonStr)
	}

	return stats, nil
}

func addMetricReason(counts map[string]int, reason string) {
	trimmed := strings.TrimSpace(reason)
	if trimmed == "" {
		return
	}
	if len(trimmed) > 240 {
		trimmed = trimmed[:240]
	}
	counts[trimmed]++
}

func renderMetricReasons(counts map[string]int) []string {
	if len(counts) == 0 {
		return []string{}
	}

	type pair struct {
		reason string
		count  int
	}
	pairs := make([]pair, 0, len(counts))
	for reason, count := range counts {
		pairs = append(pairs, pair{reason: reason, count: count})
	}

	sort.Slice(pairs, func(i, j int) bool {
		if pairs[i].count == pairs[j].count {
			return pairs[i].reason < pairs[j].reason
		}
		return pairs[i].count > pairs[j].count
	})

	limit := len(pairs)
	if limit > 20 {
		limit = 20
	}
	result := make([]string, 0, limit)
	for i := 0; i < limit; i++ {
		result = append(result, fmt.Sprintf("%s (x%d)", pairs[i].reason, pairs[i].count))
	}

	return result
}

// contains 检查字符串切片是否包含指定元素
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// countMetrics 统计指标数量
func countMetrics(metrics *connector.VMMetrics) int {
	count := 0
	count += len(metrics.CPU)
	count += len(metrics.Memory)
	count += len(metrics.DiskRead)
	count += len(metrics.DiskWrite)
	count += len(metrics.NetRx)
	count += len(metrics.NetTx)
	return count
}
