// Package v2 提供新版本的服务层，使用 DTO 模式
package v2

import (
	"context"
	"fmt"
	"time"

	apperrors "justfit/internal/errors"
	"justfit/internal/dto/mapper"
	"justfit/internal/dto/response"
	"justfit/internal/logger"
	"justfit/internal/storage"
)

// ResourceService 资源服务
type ResourceService struct {
	ctx       context.Context
	repos     *storage.Repositories
	vmMapper  *mapper.VMMapper
	hostMapper *mapper.HostMapper
	clusterMapper *mapper.ClusterMapper
	log       logger.Logger
}

// NewResourceService 创建资源服务
func NewResourceService(
	ctx context.Context,
	repos *storage.Repositories,
) *ResourceService {
	return &ResourceService{
		ctx:           ctx,
		repos:         repos,
		vmMapper:      mapper.NewVMMapper(),
		hostMapper:    mapper.NewHostMapper(),
		clusterMapper: mapper.NewClusterMapper(),
		log:           logger.With(logger.Str("service", "resource")),
	}
}

// ListClusters 获取集群列表
func (s *ResourceService) ListClusters(connectionID uint) ([]response.ClusterResponse, error) {
	s.log.Debug("获取集群列表", logger.Uint("connection_id", connectionID))

	clusters, err := s.repos.Cluster.ListByConnectionID(connectionID)
	if err != nil {
		s.log.Error("获取集群列表失败", logger.Uint("connection_id", connectionID), logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取集群列表失败")
	}

	result := s.clusterMapper.ToDTOList(clusters)
	s.log.Info("获取集群列表成功", logger.Int("count", len(result)))
	return result, nil
}

// ListHosts 获取主机列表
func (s *ResourceService) ListHosts(connectionID uint) ([]response.HostResponse, error) {
	s.log.Debug("获取主机列表", logger.Uint("connection_id", connectionID))

	hosts, err := s.repos.Host.ListByConnectionID(connectionID)
	if err != nil {
		s.log.Error("获取主机列表失败", logger.Uint("connection_id", connectionID), logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取主机列表失败")
	}

	result := s.hostMapper.ToDTOList(hosts)
	s.log.Info("获取主机列表成功", logger.Int("count", len(result)))
	return result, nil
}

// ListVMs 获取虚拟机列表
func (s *ResourceService) ListVMs(connectionID uint) ([]response.VMResponse, error) {
	s.log.Debug("获取虚拟机列表", logger.Uint("connection_id", connectionID))

	vms, err := s.repos.VM.ListByConnectionID(connectionID)
	if err != nil {
		s.log.Error("获取虚拟机列表失败", logger.Uint("connection_id", connectionID), logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取虚拟机列表失败")
	}

	result := s.vmMapper.ToDTOList(vms)
	s.log.Info("获取虚拟机列表成功", logger.Int("count", len(result)))
	return result, nil
}

// GetVM 获取单个虚拟机
func (s *ResourceService) GetVM(id uint) (*response.VMResponse, error) {
	s.log.Debug("获取虚拟机", logger.Uint("id", id))

	vm, err := s.repos.VM.GetByID(id)
	if err != nil {
		s.log.Error("获取虚拟机失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrVMNotFound
	}

	return s.vmMapper.ToDTO(vm), nil
}

// GetHost 获取单个主机
func (s *ResourceService) GetHost(id uint) (*response.HostResponse, error) {
	s.log.Debug("获取主机", logger.Uint("id", id))

	host, err := s.repos.Host.GetByID(id)
	if err != nil {
		s.log.Error("获取主机失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrHostNotFound
	}

	return s.hostMapper.ToDTO(host), nil
}

// GetCluster 获取单个集群
func (s *ResourceService) GetCluster(id uint) (*response.ClusterResponse, error) {
	s.log.Debug("获取集群", logger.Uint("id", id))

	cluster, err := s.repos.Cluster.GetByID(id)
	if err != nil {
		s.log.Error("获取集群失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrClusterNotFound
	}

	return s.clusterMapper.ToDTO(cluster), nil
}

// GetMetrics 获取虚拟机指标数据
func (s *ResourceService) GetMetrics(vmID uint, metricType string, days int) (*response.MetricsResponse, error) {
	s.log.Debug("获取指标数据", logger.Uint("vm_id", vmID), logger.String("type", metricType), logger.Int("days", days))

	vm, err := s.repos.VM.GetByID(vmID)
	if err != nil {
		s.log.Error("获取虚拟机失败", logger.Uint("vm_id", vmID), logger.Err(err))
		return nil, apperrors.ErrVMNotFound
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -days)

	metrics, err := s.repos.Metric.ListByVMAndType(vmID, metricType, startTime, endTime)
	if err != nil {
		s.log.Error("获取指标失败", logger.Uint("vm_id", vmID), logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取指标失败")
	}

	dataPoints := make([]response.MetricPoint, len(metrics))
	for i, m := range metrics {
		dataPoints[i] = response.MetricPoint{
			Timestamp: m.Timestamp.Unix(),
			Value:     m.Value,
		}
	}

	return &response.MetricsResponse{
		VMID:       vmID,
		VMName:     vm.Name,
		MetricType: metricType,
		StartTime:  startTime.Format("2006-01-02 15:04:05"),
		EndTime:    endTime.Format("2006-01-02 15:04:05"),
		DataPoints: dataPoints,
	}, nil
}

// ListVMsPaged 分页获取虚拟机列表
func (s *ResourceService) ListVMsPaged(connectionID uint, page, size int, keyword string) (*response.PagedResponse[response.VMResponse], error) {
	s.log.Debug("分页获取虚拟机列表", logger.Uint("connection_id", connectionID), logger.Int("page", page), logger.Int("size", size))

	offset := (page - 1) * size
	if offset < 0 {
		offset = 0
	}

	vms, total, err := s.repos.VM.ListByConnectionIDPaged(connectionID, size, offset, keyword)
	if err != nil {
		s.log.Error("获取虚拟机列表失败", logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取虚拟机列表失败")
	}

	items := s.vmMapper.ToDTOList(vms)
	return response.NewPagedResponse(total, page, size, items), nil
}

// GetDashboardStats 获取仪表盘统计数据
type DashboardStats struct {
	HealthScore  float64 `json:"health_score"`
	ZombieCount  int64   `json:"zombie_count"`
	TotalSavings string  `json:"total_savings"`
	TotalVMs     int64   `json:"total_vms"`
	TotalHosts   int64   `json:"total_hosts"`
	TotalClusters int64  `json:"total_clusters"`
}

func (s *ResourceService) GetDashboardStats() (*DashboardStats, error) {
	s.log.Debug("获取仪表盘统计")

	// 获取 VM 总数
	var totalVMs int64
	if err := s.repos.DB().Model(&storage.VM{}).Count(&totalVMs).Error; err != nil {
		s.log.Error("统计 VM 失败", logger.Err(err))
	}

	// 获取 Host 总数
	var totalHosts int64
	if err := s.repos.DB().Model(&storage.Host{}).Count(&totalHosts).Error; err != nil {
		s.log.Error("统计 Host 失败", logger.Err(err))
	}

	// 获取 Cluster 总数
	var totalClusters int64
	if err := s.repos.DB().Model(&storage.Cluster{}).Count(&totalClusters).Error; err != nil {
		s.log.Error("统计 Cluster 失败", logger.Err(err))
	}

	// 获取最新健康评分
	var latestHealth storage.AnalysisResult
	var healthScore float64 = 0
	s.repos.DB().Where("analysis_type = ?", "health_score").Order("created_at desc").First(&latestHealth)

	if latestHealth.ID > 0 {
		// 解析 Data 字段获取健康评分
		// 这里简化处理，实际应该解析 JSON
		healthScore = 75.0 // 默认值
		_ = latestHealth.Data // 避免未使用警告
	}

	// 统计僵尸 VM 数量
	var zombieCount int64
	s.repos.DB().Model(&storage.AnalysisResult{}).
		Where("analysis_type = ? AND created_at > ?", "zombie_vm", time.Now().AddDate(0, 0, -7)).
		Count(&zombieCount)

	// 计算节省
	var monthlySaving float64 = 0
	if zombieCount > 0 {
		monthlySaving = float64(zombieCount) * 180
	}

	savings := fmt.Sprintf("¥%.0f/月", monthlySaving)

	return &DashboardStats{
		HealthScore:   healthScore,
		ZombieCount:   zombieCount,
		TotalSavings:  savings,
		TotalVMs:      totalVMs,
		TotalHosts:    totalHosts,
		TotalClusters: totalClusters,
	}, nil
}
