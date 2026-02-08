// Package etl 提供数据采集服务
package etl

import (
	"context"
	"fmt"
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
func (c *Collector) CollectMetrics(ctx context.Context, connectionID uint, days int, passwordOverride string) (int, error) {
	conn, err := c.repos.Connection.GetByID(connectionID)
	if err != nil {
		return 0, fmt.Errorf("获取连接失败: %w", err)
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
		return 0, fmt.Errorf("创建连接器失败: %w", err)
	}

	// 这里为了稳定，我们还是使用 client.GetVMs() 以确保 vCenter 侧的准确性（如 PowerState）
	// 但必须并行化！
	vms, err := client.GetVMs()
	if err != nil {
		return 0, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	totalMetrics := 0
	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -days)

	// 并发控制
	concurrency := 5 // 限制并发数，避免压垮 vCenter
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, concurrency)
	var mu sync.Mutex

	for _, vm := range vms {
		if vm.PowerState != "poweredOn" {
			continue
		}

		wg.Add(1)
		semaphore <- struct{}{} // 获取信号量

		go func(targetVM connector.VMInfo) {
			defer wg.Done()
			defer func() { <-semaphore }() // 释放信号量

			vmKey := fmt.Sprintf("%s:%s", targetVM.Datacenter, targetVM.Name)
			metrics, err := client.GetVMMetrics(targetVM.Datacenter, targetVM.Name, startTime, endTime, targetVM.CpuCount)
			if err != nil {
				// 获取指标失败，忽略
				return
			}

			if err := c.processor.ProcessVMMetrics(vmKey, metrics); err != nil {
				return
			}

			count := countMetrics(metrics)
			mu.Lock()
			totalMetrics += count
			mu.Unlock()
		}(vm)
	}

	wg.Wait()
	return totalMetrics, nil
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
