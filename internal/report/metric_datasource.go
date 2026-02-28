package report

import (
	"fmt"
	"time"

	"justfit/internal/storage"
)

// metricDataSourceAdapter 指标数据源适配器
// 实现 MetricDataSource 接口，连接图表生成器与数据库
type metricDataSourceAdapter struct {
	metricRepo *storage.MetricRepository
	vmRepo     *storage.VMRepository
	hostRepo   *storage.HostRepository
	taskID     uint
}

// NewMetricDataSource 创建指标数据源适配器
func NewMetricDataSource(repos *storage.Repositories, taskID uint) MetricDataSource {
	return &metricDataSourceAdapter{
		metricRepo: repos.VMMetric,
		vmRepo:     repos.VM,
		hostRepo:   repos.Host,
		taskID:     taskID,
	}
}

// GetVMs 获取 VM ID 列表
func (a *metricDataSourceAdapter) GetVMs() ([]uint, error) {
	var vms []storage.VM
	var err error

	if a.taskID > 0 {
		// 按任务获取：需要从任务获取 connectionID
		// 这里简化处理，获取所有 VM
		vms, err = a.vmRepo.ListByConnectionID(0)
	} else {
		vms, err = a.vmRepo.ListByConnectionID(0)
	}

	if err != nil {
		return nil, fmt.Errorf("获取 VM 列表失败: %w", err)
	}

	ids := make([]uint, len(vms))
	for i, v := range vms {
		ids[i] = v.ID
	}

	return ids, nil
}

// GetVMMetrics 获取指定 VM 的指标数据
func (a *metricDataSourceAdapter) GetVMMetrics(vmID uint, metricType string, startTime, endTime time.Time) ([]MetricPoint, error) {
	if a.taskID == 0 {
		// 如果没有指定任务ID，尝试获取该 VM 的所有指标
		metrics, err := a.metricRepo.ListByVMAndType(vmID, metricType, startTime, endTime)
		if err != nil {
			return nil, err
		}

		points := make([]MetricPoint, len(metrics))
		for i, m := range metrics {
			points[i] = MetricPoint{
				Timestamp: m.Timestamp,
				Value:     m.Value,
			}
		}
		return points, nil
	}

	// 按任务获取指标
	metrics, err := a.metricRepo.ListByTaskAndVMAndType(a.taskID, vmID, metricType, startTime, endTime)
	if err != nil {
		return nil, fmt.Errorf("获取 VM %d 的 %s 指标失败: %w", vmID, metricType, err)
	}

	points := make([]MetricPoint, len(metrics))
	for i, m := range metrics {
		points[i] = MetricPoint{
			Timestamp: m.Timestamp,
			Value:     m.Value,
		}
	}

	return points, nil
}

// GetHosts 获取主机名称列表
func (a *metricDataSourceAdapter) GetHosts() ([]string, error) {
	hosts, err := a.hostRepo.ListByConnectionID(0)
	if err != nil {
		return nil, fmt.Errorf("获取主机列表失败: %w", err)
	}

	hostNames := make([]string, len(hosts))
	for i, h := range hosts {
		hostNames[i] = h.Name
	}

	return hostNames, nil
}

// GetVMsByHost 根据主机名获取关联的 VM ID 列表
func (a *metricDataSourceAdapter) GetVMsByHost(hostName string) ([]uint, error) {
	// 使用 VMRepository 的 ListByHostName 方法
	vms, err := a.vmRepo.ListByHostName(hostName)
	if err != nil {
		return nil, fmt.Errorf("获取主机 %s 的 VM 列表失败: %w", hostName, err)
	}

	ids := make([]uint, len(vms))
	for i, v := range vms {
		ids[i] = v.ID
	}

	return ids, nil
}
