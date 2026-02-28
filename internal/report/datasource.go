package report

import (
	"fmt"
	"log"
	"time"

	"justfit/internal/storage"
)

// StorageDataSource 数据库数据源实现
type StorageDataSource struct {
	clusterRepo *storage.ClusterRepository
	hostRepo    *storage.HostRepository
	vmRepo      *storage.VMRepository
	findingRepo *storage.AnalysisFindingRepository
	taskRepo    *storage.TaskRepository
	taskID      uint // 可选，如果指定则只获取该任务的数据
}

// NewStorageDataSource 创建存储层数据源（获取所有数据）
func NewStorageDataSource(repos *storage.Repositories) *StorageDataSource {
	return &StorageDataSource{
		clusterRepo: repos.Cluster,
		hostRepo:    repos.Host,
		vmRepo:      repos.VM,
		findingRepo: repos.AnalysisFinding,
		taskRepo:    repos.AssessmentTask,
		taskID:      0, // 0 表示获取所有数据
	}
}

// NewDataSourceByTaskID 创建按任务ID过滤的数据源
func NewDataSourceByTaskID(repos *storage.Repositories, taskID uint) *StorageDataSource {
	return &StorageDataSource{
		clusterRepo: repos.Cluster,
		hostRepo:    repos.Host,
		vmRepo:      repos.VM,
		findingRepo: repos.AnalysisFinding,
		taskRepo:    repos.AssessmentTask,
		taskID:      taskID,
	}
}

// GetClusters 获取集群信息
func (ds *StorageDataSource) GetClusters() ([]ClusterInfo, error) {
	var clusters []storage.Cluster
	var err error

	log.Printf("[ReportDataSource] GetClusters: taskID=%d", ds.taskID)

	if ds.taskID > 0 {
		// 按任务获取：需要从任务信息获取 connectionID
		task, taskErr := ds.taskRepo.GetByID(ds.taskID)
		if taskErr != nil {
			log.Printf("[ReportDataSource] GetClusters: 获取任务信息失败: %v", taskErr)
			return nil, fmt.Errorf("获取任务信息失败: %w", taskErr)
		}
		log.Printf("[ReportDataSource] GetClusters: 使用 connectionID=%d", task.ConnectionID)
		clusters, err = ds.clusterRepo.ListByConnectionID(task.ConnectionID)
	} else {
		// 获取所有集群
		log.Printf("[ReportDataSource] GetClusters: 获取所有集群")
		clusters, err = ds.clusterRepo.ListByConnectionID(0)
	}

	if err != nil {
		log.Printf("[ReportDataSource] GetClusters: 查询失败: %v", err)
		return nil, err
	}

	log.Printf("[ReportDataSource] GetClusters: 找到 %d 个集群", len(clusters))

	result := make([]ClusterInfo, len(clusters))
	for i, c := range clusters {
		result[i] = ClusterInfo{
			Name:        c.Name,
			Datacenter:  c.Datacenter,
			TotalCpu:    c.TotalCpu,
			TotalMemory: c.TotalMemory,
			NumHosts:    c.NumHosts,
			NumVMs:      c.NumVMs,
			Status:      c.Status,
			CollectedAt: c.CollectedAt,
		}
	}

	return result, nil
}

// GetHosts 获取主机信息
func (ds *StorageDataSource) GetHosts() ([]HostInfo, error) {
	var hosts []storage.Host
	var err error

	if ds.taskID > 0 {
		task, taskErr := ds.taskRepo.GetByID(ds.taskID)
		if taskErr != nil {
			return nil, fmt.Errorf("获取任务信息失败: %w", taskErr)
		}
		hosts, err = ds.hostRepo.ListByConnectionID(task.ConnectionID)
	} else {
		hosts, err = ds.hostRepo.ListByConnectionID(0)
	}

	if err != nil {
		return nil, err
	}

	result := make([]HostInfo, len(hosts))
	for i, h := range hosts {
		result[i] = HostInfo{
			Name:          h.Name,
			Datacenter:    h.Datacenter,
			IPAddress:     h.IPAddress,
			CpuCores:      h.CpuCores,
			CpuMhz:        h.CpuMhz,
			Memory:        h.Memory,
			NumVMs:        h.NumVMs,
			PowerState:    h.PowerState,
			OverallStatus: h.OverallStatus,
			CollectedAt:   h.CollectedAt,
		}
	}

	return result, nil
}

// GetVMs 获取虚拟机信息
func (ds *StorageDataSource) GetVMs() ([]VMInfo, error) {
	var vms []storage.VM
	var err error

	if ds.taskID > 0 {
		task, taskErr := ds.taskRepo.GetByID(ds.taskID)
		if taskErr != nil {
			return nil, fmt.Errorf("获取任务信息失败: %w", taskErr)
		}
		vms, err = ds.vmRepo.ListByConnectionID(task.ConnectionID)
	} else {
		vms, err = ds.vmRepo.ListByConnectionID(0)
	}

	if err != nil {
		return nil, err
	}

	result := make([]VMInfo, len(vms))
	for i, v := range vms {
		result[i] = VMInfo{
			Name:          v.Name,
			Datacenter:    v.Datacenter,
			CpuCount:      v.CpuCount,
			MemoryMB:      v.MemoryMB,
			PowerState:    v.PowerState,
			GuestOS:       v.GuestOS,
			HostName:      v.HostName,
			HostIP:        v.HostIP,
			OverallStatus: v.OverallStatus,
			CollectedAt:   v.CollectedAt,
		}
	}

	return result, nil
}

// GetAnalysisFindings 获取分析结果
func (ds *StorageDataSource) GetAnalysisFindings(jobType string) ([]AnalysisFinding, error) {
	if ds.taskID == 0 {
		// 如果没有指定任务ID，返回空结果
		// 因为分析结果是按任务存储的，无法跨任务聚合
		return []AnalysisFinding{}, nil
	}

	// 从 AnalysisFinding 表查询指定任务和类型的分析结果
	findings, err := ds.findingRepo.ListByTaskAndJobType(ds.taskID, jobType)
	if err != nil {
		return nil, fmt.Errorf("获取分析结果失败: %w", err)
	}

	result := make([]AnalysisFinding, len(findings))
	for i, f := range findings {
		result[i] = AnalysisFinding{
			JobType:     f.JobType,
			TargetName:  f.TargetName,
			Severity:    f.Severity,
			Title:       f.Title,
			Description: f.Description,
			Action:      f.Action,
			Reason:      f.Reason,
			SavingCost:  f.SavingCost,
			Details:     f.Details, // 添加 Details 字段
		}
	}

	return result, nil
}

// GetTaskInfo 获取任务信息
func (ds *StorageDataSource) GetTaskInfo() (*TaskInfo, error) {
	var task *storage.AssessmentTask
	var err error

	log.Printf("[ReportDataSource] GetTaskInfo: taskID=%d", ds.taskID)

	if ds.taskID > 0 {
		task, err = ds.taskRepo.GetByID(ds.taskID)
		if err != nil {
			log.Printf("[ReportDataSource] GetTaskInfo: 按ID获取任务失败: %v", err)
			return nil, fmt.Errorf("获取任务信息失败: %w", err)
		}
		log.Printf("[ReportDataSource] GetTaskInfo: 找到任务 name=%s connectionID=%d", task.Name, task.ConnectionID)
	} else {
		// 获取最新任务
		tasks, listErr := ds.taskRepo.List(1, 0)
		if listErr != nil {
			log.Printf("[ReportDataSource] GetTaskInfo: 获取最新任务失败: %v", listErr)
			return nil, listErr
		}
		if len(tasks) > 0 {
			task = &tasks[0]
			log.Printf("[ReportDataSource] GetTaskInfo: 找到最新任务 name=%s connectionID=%d", task.Name, task.ConnectionID)
		}
	}

	if err != nil {
		return nil, fmt.Errorf("获取任务信息失败: %w", err)
	}

	if task == nil {
		// 返回默认信息（用于测试或无数据情况）
		log.Printf("[ReportDataSource] GetTaskInfo: 未找到任务，返回默认信息")
		return &TaskInfo{
			Name:        "资源评估报告",
			Platform:    "Unknown",
			StartedAt:   time.Now(),
			MetricsDays: 30,
		}, nil
	}

	var startedAt time.Time
	if task.StartedAt != nil {
		startedAt = *task.StartedAt
	} else {
		startedAt = task.CreatedAt
	}

	return &TaskInfo{
		Name:           task.Name,
		ConnectionName: task.ConnectionName,
		Platform:       task.Platform,
		StartedAt:      startedAt,
		MetricsDays:    task.MetricsDays,
	}, nil
}
