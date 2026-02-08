// Package storage 数据仓储实现
package storage

import (
	"time"

	"gorm.io/gorm"
)

// ConnectionRepository 连接仓储
type ConnectionRepository struct {
	db *gorm.DB
}

// NewConnectionRepository 创建连接仓储
func NewConnectionRepository() *ConnectionRepository {
	return &ConnectionRepository{db: DB}
}

// Create 创建连接
func (r *ConnectionRepository) Create(conn *Connection) error {
	return r.db.Create(conn).Error
}

// Update 更新连接
func (r *ConnectionRepository) Update(conn *Connection) error {
	return r.db.Save(conn).Error
}

// Delete 删除连接
func (r *ConnectionRepository) Delete(id uint) error {
	return r.db.Delete(&Connection{}, id).Error
}

// GetByID 根据ID获取连接
func (r *ConnectionRepository) GetByID(id uint) (*Connection, error) {
	var conn Connection
	err := r.db.First(&conn, id).Error
	if err != nil {
		return nil, err
	}
	return &conn, nil
}

// List 获取连接列表
func (r *ConnectionRepository) List() ([]Connection, error) {
	var conns []Connection
	err := r.db.Find(&conns).Error
	return conns, err
}

// UpdateStatus 更新连接状态
func (r *ConnectionRepository) UpdateStatus(id uint, status string) error {
	return r.db.Model(&Connection{}).Where("id = ?", id).Update("status", status).Error
}

// UpdateLastSync 更新最后同步时间
func (r *ConnectionRepository) UpdateLastSync(id uint, t time.Time) error {
	return r.db.Model(&Connection{}).Where("id = ?", id).Update("last_sync", &t).Error
}

// ClusterRepository 集群仓储
type ClusterRepository struct {
	db *gorm.DB
}

// NewClusterRepository 创建集群仓储
func NewClusterRepository() *ClusterRepository {
	return &ClusterRepository{db: DB}
}

// Create 创建集群
func (r *ClusterRepository) Create(cluster *Cluster) error {
	return r.db.Create(cluster).Error
}

// UpdateOrCreate 更新或创建集群
func (r *ClusterRepository) UpdateOrCreate(cluster *Cluster) error {
	var existing Cluster
	err := r.db.Where("cluster_key = ?", cluster.ClusterKey).First(&existing).Error
	if err == gorm.ErrRecordNotFound {
		return r.db.Create(cluster).Error
	}
	if err != nil {
		return err
	}
	cluster.ID = existing.ID
	return r.db.Save(cluster).Error
}

// DeleteByConnectionID 删除连接的所有集群
func (r *ClusterRepository) DeleteByConnectionID(connectionID uint) error {
	return r.db.Where("connection_id = ?", connectionID).Delete(&Cluster{}).Error
}

// ListByConnectionID 获取连接的集群列表
func (r *ClusterRepository) ListByConnectionID(connectionID uint) ([]Cluster, error) {
	var clusters []Cluster
	err := r.db.Where("connection_id = ?", connectionID).Find(&clusters).Error
	return clusters, err
}

// HostRepository 主机仓储
type HostRepository struct {
	db *gorm.DB
}

// NewHostRepository 创建主机仓储
func NewHostRepository() *HostRepository {
	return &HostRepository{db: DB}
}

// Create 创建主机
func (r *HostRepository) Create(host *Host) error {
	return r.db.Create(host).Error
}

// UpdateOrCreate 更新或创建主机
func (r *HostRepository) UpdateOrCreate(host *Host) error {
	var existing Host
	err := r.db.Where("host_key = ?", host.HostKey).First(&existing).Error
	if err == gorm.ErrRecordNotFound {
		return r.db.Create(host).Error
	}
	if err != nil {
		return err
	}
	host.ID = existing.ID
	return r.db.Save(host).Error
}

// DeleteByConnectionID 删除连接的所有主机
func (r *HostRepository) DeleteByConnectionID(connectionID uint) error {
	return r.db.Where("connection_id = ?", connectionID).Delete(&Host{}).Error
}

// ListByConnectionID 获取连接的主机列表
func (r *HostRepository) ListByConnectionID(connectionID uint) ([]Host, error) {
	var hosts []Host
	err := r.db.Where("connection_id = ?", connectionID).Find(&hosts).Error
	return hosts, err
}

// VMRepository 虚拟机仓储
type VMRepository struct {
	db *gorm.DB
}

// NewVMRepository 创建虚拟机仓储
func NewVMRepository() *VMRepository {
	return &VMRepository{db: DB}
}

// Create 创建虚拟机
func (r *VMRepository) Create(vm *VM) error {
	return r.db.Create(vm).Error
}

// UpdateOrCreate 更新或创建虚拟机
func (r *VMRepository) UpdateOrCreate(vm *VM) error {
	var existing VM
	err := r.db.Where("vm_key = ?", vm.VMKey).First(&existing).Error
	if err == gorm.ErrRecordNotFound {
		return r.db.Create(vm).Error
	}
	if err != nil {
		return err
	}
	vm.ID = existing.ID
	return r.db.Save(vm).Error
}

// DeleteByConnectionID 删除连接的所有虚拟机
func (r *VMRepository) DeleteByConnectionID(connectionID uint) error {
	return r.db.Where("connection_id = ?", connectionID).Delete(&VM{}).Error
}

// ListByConnectionID 获取连接的虚拟机列表
func (r *VMRepository) ListByConnectionID(connectionID uint) ([]VM, error) {
	var vms []VM
	err := r.db.Where("connection_id = ?", connectionID).Find(&vms).Error
	return vms, err
}

// GetByKey 根据Key获取虚拟机
func (r *VMRepository) GetByKey(key string) (*VM, error) {
	var vm VM
	err := r.db.Where("vm_key = ?", key).First(&vm).Error
	if err != nil {
		return nil, err
	}
	return &vm, nil
}

// MetricRepository 性能指标仓储
type MetricRepository struct {
	db *gorm.DB
}

// NewMetricRepository 创建指标仓储
func NewMetricRepository() *MetricRepository {
	return &MetricRepository{db: DB}
}

// BatchCreate 批量创建指标
func (r *MetricRepository) BatchCreate(metrics []Metric) error {
	if len(metrics) == 0 {
		return nil
	}
	return r.db.CreateInBatches(metrics, 100).Error
}

// DeleteByVMID 删除虚拟机的所有指标
func (r *MetricRepository) DeleteByVMID(vmID uint) error {
	return r.db.Where("vm_id = ?", vmID).Delete(&Metric{}).Error
}

// DeleteByTimeRange 删除时间范围内的指标
func (r *MetricRepository) DeleteByTimeRange(before time.Time) error {
	return r.db.Where("timestamp < ?", before).Delete(&Metric{}).Error
}

// ListByVMAndType 获取虚拟机的指定类型指标
func (r *MetricRepository) ListByVMAndType(vmID uint, metricType string, startTime, endTime time.Time) ([]Metric, error) {
	var metrics []Metric
	query := r.db.Where("vm_id = ? AND metric_type = ?", vmID, metricType)
	if !startTime.IsZero() {
		query = query.Where("timestamp >= ?", startTime)
	}
	if !endTime.IsZero() {
		query = query.Where("timestamp <= ?", endTime)
	}
	err := query.Order("timestamp ASC").Find(&metrics).Error
	return metrics, err
}

// TaskRepository 任务仓储
type TaskRepository struct {
	db *gorm.DB
}

// NewTaskRepository 创建任务仓储
func NewTaskRepository() *TaskRepository {
	return &TaskRepository{db: DB}
}

// Create 创建任务
func (r *TaskRepository) Create(task *Task) error {
	return r.db.Create(task).Error
}

// Update 更新任务
func (r *TaskRepository) Update(task *Task) error {
	return r.db.Save(task).Error
}

// GetByID 根据ID获取任务
func (r *TaskRepository) GetByID(id uint) (*Task, error) {
	var task Task
	err := r.db.First(&task, id).Error
	if err != nil {
		return nil, err
	}
	return &task, nil
}

// List 获取任务列表
func (r *TaskRepository) List(limit, offset int) ([]Task, error) {
	var tasks []Task
	err := r.db.Order("created_at DESC").Limit(limit).Offset(offset).Find(&tasks).Error
	return tasks, err
}

// ReportRepository 报告仓储
type ReportRepository struct {
	db *gorm.DB
}

// NewReportRepository 创建报告仓储
func NewReportRepository() *ReportRepository {
	return &ReportRepository{db: DB}
}

// Create 创建报告
func (r *ReportRepository) Create(report *Report) error {
	return r.db.Create(report).Error
}

// Update 更新报告
func (r *ReportRepository) Update(report *Report) error {
	return r.db.Save(report).Error
}

// GetByID 根据ID获取报告
func (r *ReportRepository) GetByID(id uint) (*Report, error) {
	var report Report
	err := r.db.First(&report, id).Error
	if err != nil {
		return nil, err
	}
	return &report, nil
}

// List 获取报告列表
func (r *ReportRepository) List(limit, offset int) ([]Report, error) {
	var reports []Report
	err := r.db.Order("created_at DESC").Limit(limit).Offset(offset).Find(&reports).Error
	return reports, err
}

// AnalysisResultRepository 分析结果仓储
type AnalysisResultRepository struct {
	db *gorm.DB
}

// NewAnalysisResultRepository 创建分析结果仓储
func NewAnalysisResultRepository() *AnalysisResultRepository {
	return &AnalysisResultRepository{db: DB}
}

// Create 创建分析结果
func (r *AnalysisResultRepository) Create(result *AnalysisResult) error {
	return r.db.Create(result).Error
}

// BatchCreate 批量创建分析结果
func (r *AnalysisResultRepository) BatchCreate(results []AnalysisResult) error {
	if len(results) == 0 {
		return nil
	}
	return r.db.CreateInBatches(results, 100).Error
}

// ListByReportID 获取报告的分析结果
func (r *AnalysisResultRepository) ListByReportID(reportID uint) ([]AnalysisResult, error) {
	var results []AnalysisResult
	err := r.db.Where("report_id = ?", reportID).Find(&results).Error
	return results, err
}

// AlertRepository 告警仓储
type AlertRepository struct {
	db *gorm.DB
}

// NewAlertRepository 创建告警示储
func NewAlertRepository() *AlertRepository {
	return &AlertRepository{db: DB}
}

// Create 创建告警
func (r *AlertRepository) Create(alert *Alert) error {
	return r.db.Create(alert).Error
}

// BatchCreate 批量创建告警
func (r *AlertRepository) BatchCreate(alerts []Alert) error {
	if len(alerts) == 0 {
		return nil
	}
	return r.db.CreateInBatches(alerts, 100).Error
}

// List 获取告警列表
func (r *AlertRepository) List(acknowledged bool, limit, offset int) ([]Alert, error) {
	var alerts []Alert
	query := r.db.Where("acknowledged = ?", acknowledged)
	err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&alerts).Error
	return alerts, err
}

// Acknowledge 确认告警
func (r *AlertRepository) Acknowledge(id uint) error {
	return r.db.Model(&Alert{}).Where("id = ?", id).Updates(map[string]interface{}{
		"acknowledged":    true,
		"acknowledged_at": time.Now(),
	}).Error
}

// DeleteByTarget 删除指定目标的所有告警
func (r *AlertRepository) DeleteByTarget(targetType, targetKey string) error {
	return r.db.Where("target_type = ? AND target_key = ?", targetType, targetKey).Delete(&Alert{}).Error
}
