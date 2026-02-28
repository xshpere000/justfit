// Package storage 数据仓储实现
package storage

import (
	"encoding/json"
	"time"

	"gorm.io/gorm"
)

// ==============================================================================
// ConnectionRepository 连接仓储
// ==============================================================================

type ConnectionRepository struct {
	db *gorm.DB
}

func NewConnectionRepository() *ConnectionRepository {
	return &ConnectionRepository{db: DB}
}

func (r *ConnectionRepository) Create(conn *Connection) error {
	return r.db.Create(conn).Error
}

func (r *ConnectionRepository) Update(conn *Connection) error {
	return r.db.Save(conn).Error
}

func (r *ConnectionRepository) Delete(id uint) error {
	return r.db.Delete(&Connection{}, id).Error
}

func (r *ConnectionRepository) GetByID(id uint) (*Connection, error) {
	var conn Connection
	err := r.db.First(&conn, id).Error
	if err != nil {
		return nil, err
	}
	return &conn, nil
}

func (r *ConnectionRepository) List() ([]Connection, error) {
	var conns []Connection
	err := r.db.Find(&conns).Error
	return conns, err
}

func (r *ConnectionRepository) UpdateStatus(id uint, status string) error {
	return r.db.Model(&Connection{}).Where("id = ?", id).Update("status", status).Error
}

func (r *ConnectionRepository) UpdateLastSync(id uint, t time.Time) error {
	return r.db.Model(&Connection{}).Where("id = ?", id).Update("last_sync", &t).Error
}

// ==============================================================================
// ClusterRepository 集群仓储
// ==============================================================================

type ClusterRepository struct {
	db *gorm.DB
}

func NewClusterRepository() *ClusterRepository {
	return &ClusterRepository{db: DB}
}

func (r *ClusterRepository) Create(cluster *Cluster) error {
	return r.db.Create(cluster).Error
}

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

func (r *ClusterRepository) DeleteByConnectionID(connectionID uint) error {
	return r.db.Where("connection_id = ?", connectionID).Delete(&Cluster{}).Error
}

func (r *ClusterRepository) ListByConnectionID(connectionID uint) ([]Cluster, error) {
	var clusters []Cluster
	err := r.db.Where("connection_id = ?", connectionID).Find(&clusters).Error
	return clusters, err
}

func (r *ClusterRepository) GetByID(id uint) (*Cluster, error) {
	var cluster Cluster
	err := r.db.First(&cluster, id).Error
	if err != nil {
		return nil, err
	}
	return &cluster, nil
}

// ==============================================================================
// HostRepository 主机仓储
// ==============================================================================

type HostRepository struct {
	db *gorm.DB
}

func NewHostRepository() *HostRepository {
	return &HostRepository{db: DB}
}

func (r *HostRepository) Create(host *Host) error {
	return r.db.Create(host).Error
}

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

func (r *HostRepository) DeleteByConnectionID(connectionID uint) error {
	return r.db.Where("connection_id = ?", connectionID).Delete(&Host{}).Error
}

func (r *HostRepository) ListByConnectionID(connectionID uint) ([]Host, error) {
	var hosts []Host
	err := r.db.Where("connection_id = ?", connectionID).Find(&hosts).Error
	return hosts, err
}

func (r *HostRepository) GetByID(id uint) (*Host, error) {
	var host Host
	err := r.db.First(&host, id).Error
	if err != nil {
		return nil, err
	}
	return &host, nil
}

// ==============================================================================
// VMRepository 虚拟机仓储
// ==============================================================================

type VMRepository struct {
	db *gorm.DB
}

func NewVMRepository() *VMRepository {
	return &VMRepository{db: DB}
}

func (r *VMRepository) Create(vm *VM) error {
	return r.db.Create(vm).Error
}

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

func (r *VMRepository) DeleteByConnectionID(connectionID uint) error {
	return r.db.Where("connection_id = ?", connectionID).Delete(&VM{}).Error
}

func (r *VMRepository) ListByConnectionID(connectionID uint) ([]VM, error) {
	var vms []VM
	err := r.db.Where("connection_id = ?", connectionID).Find(&vms).Error
	return vms, err
}

func (r *VMRepository) GetByKey(key string) (*VM, error) {
	var vm VM
	err := r.db.Where("vm_key = ?", key).First(&vm).Error
	if err != nil {
		return nil, err
	}
	return &vm, nil
}

func (r *VMRepository) GetByID(id uint) (*VM, error) {
	var vm VM
	err := r.db.First(&vm, id).Error
	if err != nil {
		return nil, err
	}
	return &vm, nil
}

func (r *VMRepository) CountByConnectionID(connectionID uint) (int, error) {
	var count int64
	err := r.db.Model(&VM{}).Where("connection_id = ?", connectionID).Count(&count).Error
	return int(count), err
}

func (r *VMRepository) ListByConnectionIDPaged(connectionID uint, limit, offset int, keyword string) ([]VM, int64, error) {
	var vms []VM
	var total int64

	query := r.db.Model(&VM{}).Where("connection_id = ?", connectionID)

	if keyword != "" {
		query = query.Where("name LIKE ? OR uuid LIKE ?", "%"+keyword+"%", "%"+keyword+"%")
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	err := query.Find(&vms).Error
	return vms, total, err
}

// ListByHostName 根据主机名称获取关联的虚拟机列表
func (r *VMRepository) ListByHostName(hostName string) ([]VM, error) {
	var vms []VM
	err := r.db.Where("host_name = ?", hostName).Find(&vms).Error
	return vms, err
}

// ListByHostNames 根据主机名称列表获取关联的虚拟机列表
func (r *VMRepository) ListByHostNames(hostNames []string) ([]VM, error) {
	var vms []VM
	err := r.db.Where("host_name IN ?", hostNames).Find(&vms).Error
	return vms, err
}

// ==============================================================================
// MetricRepository 性能指标仓储
// ==============================================================================

type MetricRepository struct {
	db *gorm.DB
}

func NewMetricRepository() *MetricRepository {
	return &MetricRepository{db: DB}
}

func (r *MetricRepository) BatchCreate(metrics []VMMetric) error {
	if len(metrics) == 0 {
		return nil
	}
	return r.db.CreateInBatches(metrics, 100).Error
}

// DeleteByTaskID 删除指定任务的所有指标数据
func (r *MetricRepository) DeleteByTaskID(taskID uint) error {
	return r.db.Where("task_id = ?", taskID).Delete(&VMMetric{}).Error
}

// DeleteByVMID 删除指定虚拟机的所有指标数据
func (r *MetricRepository) DeleteByVMID(vmID uint) error {
	return r.db.Where("vm_id = ?", vmID).Delete(&VMMetric{}).Error
}

func (r *MetricRepository) DeleteByTimeRange(before time.Time) error {
	return r.db.Where("timestamp < ?", before).Delete(&VMMetric{}).Error
}

// ListByTaskAndVMAndType 查询指定任务、虚拟机和类型的指标
// taskID 为 0 时查询所有任务的数据
func (r *MetricRepository) ListByTaskAndVMAndType(taskID, vmID uint, metricType string, startTime, endTime time.Time) ([]VMMetric, error) {
	var metrics []VMMetric
	query := r.db.Where("vm_id = ? AND metric_type = ?", vmID, metricType)
	// taskID 为 0 时不过滤任务（查询所有数据）
	if taskID != 0 {
		query = query.Where("task_id = ?", taskID)
	}
	if !startTime.IsZero() {
		query = query.Where("timestamp >= ?", startTime)
	}
	if !endTime.IsZero() {
		query = query.Where("timestamp <= ?", endTime)
	}
	err := query.Order("timestamp ASC").Find(&metrics).Error
	return metrics, err
}

// ListByVMAndType 查询指定虚拟机和类型的指标（所有任务）
func (r *MetricRepository) ListByVMAndType(vmID uint, metricType string, startTime, endTime time.Time) ([]VMMetric, error) {
	var metrics []VMMetric
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

// ==============================================================================
// AssessmentTaskRepository 评估任务仓储 (原 TaskRepository)
// ==============================================================================

type TaskRepository struct {
	db *gorm.DB
}

func NewTaskRepository() *TaskRepository {
	return &TaskRepository{db: DB}
}

func (r *TaskRepository) Create(task *AssessmentTask) error {
	return r.db.Create(task).Error
}

func (r *TaskRepository) Update(task *AssessmentTask) error {
	return r.db.Save(task).Error
}

func (r *TaskRepository) GetByID(id uint) (*AssessmentTask, error) {
	var task AssessmentTask
	err := r.db.First(&task, id).Error
	if err != nil {
		return nil, err
	}
	return &task, nil
}

func (r *TaskRepository) List(limit, offset int) ([]AssessmentTask, error) {
	var tasks []AssessmentTask
	err := r.db.Order("created_at DESC").Limit(limit).Offset(offset).Find(&tasks).Error
	return tasks, err
}

func (r *TaskRepository) ListByStatus(status string, limit, offset int) ([]AssessmentTask, error) {
	var tasks []AssessmentTask
	query := r.db.Order("created_at DESC")
	if status != "" {
		query = query.Where("status = ?", status)
	}
	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}
	err := query.Find(&tasks).Error
	return tasks, err
}

func (r *TaskRepository) GetMaxID() (uint, error) {
	var maxID uint
	// 使用 Unscoped() 包含软删除的记录，确保 taskCounter 正确同步
	// 场景：如果有软删除的任务，其 ID 仍占用，需要跳过这些 ID
	err := r.db.Model(&AssessmentTask{}).Unscoped().Select("COALESCE(MAX(id), 0)").Scan(&maxID).Error
	return maxID, err
}

func (r *TaskRepository) Delete(id uint) error {
	return r.db.Delete(&AssessmentTask{}, id).Error
}

// UpdateProgress 更新任务进度和状态（确保状态为 running）
// 同时更新 status 和 progress，防止前端认为任务不是运行中
func (r *TaskRepository) UpdateProgress(id uint, progress int) error {
	// 先获取当前任务状态
	var currentStatus string
	r.db.Model(&AssessmentTask{}).Where("id = ?", id).Select("status").Scan(&currentStatus)

	// 如果任务还未完成，确保状态是 running
	targetStatus := currentStatus
	if currentStatus != "completed" && currentStatus != "failed" && currentStatus != "cancelled" {
		targetStatus = "running"
	}

	// 同时更新 status 和 progress
	return r.db.Model(&AssessmentTask{}).Where("id = ?", id).
		Select("status", "progress").
		Updates(map[string]interface{}{
			"status":   targetStatus,
			"progress": progress,
		}).Error
}

// TaskStats 任务统计信息
type TaskStats struct {
	Total     int64
	Pending   int64
	Running   int64
	Completed int64
	Failed    int64
}

// GetStats 获取任务统计信息
func (r *TaskRepository) GetStats() (*TaskStats, error) {
	var stats TaskStats

	// 统计各状态的任务数量
	r.db.Model(&AssessmentTask{}).Count(&stats.Total)
	r.db.Model(&AssessmentTask{}).Where("status = ?", "pending").Count(&stats.Pending)
	r.db.Model(&AssessmentTask{}).Where("status = ?", "running").Count(&stats.Running)
	r.db.Model(&AssessmentTask{}).Where("status = ?", "completed").Count(&stats.Completed)
	r.db.Model(&AssessmentTask{}).Where("status = ?", "failed").Count(&stats.Failed)

	return &stats, nil
}

// ==============================================================================
// TaskVMSnapshotRepository 任务虚拟机快照仓储
// ==============================================================================

type TaskVMSnapshotRepository struct {
	db *gorm.DB
}

func NewTaskVMSnapshotRepository() *TaskVMSnapshotRepository {
	return &TaskVMSnapshotRepository{db: DB}
}

func (r *TaskVMSnapshotRepository) ReplaceByTaskID(taskID uint, snapshots []TaskVMSnapshot) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("task_id = ?", taskID).Delete(&TaskVMSnapshot{}).Error; err != nil {
			return err
		}

		if len(snapshots) == 0 {
			return nil
		}

		return tx.CreateInBatches(snapshots, 100).Error
	})
}

func (r *TaskVMSnapshotRepository) ListByTaskID(taskID uint, limit, offset int, keyword string) ([]TaskVMSnapshot, int64, error) {
	query := r.db.Model(&TaskVMSnapshot{}).Where("task_id = ?", taskID)
	if keyword != "" {
		kw := "%" + keyword + "%"
		query = query.Where("name LIKE ? OR host_name LIKE ? OR datacenter LIKE ?", kw, kw, kw)
	}

	var total int64
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	var snapshots []TaskVMSnapshot
	err := query.Order("name ASC").Find(&snapshots).Error
	return snapshots, total, err
}

func (r *TaskVMSnapshotRepository) CountByTaskID(taskID uint) (int64, error) {
	var total int64
	err := r.db.Model(&TaskVMSnapshot{}).Where("task_id = ?", taskID).Count(&total).Error
	return total, err
}

func (r *TaskVMSnapshotRepository) DeleteByTaskID(taskID uint) error {
	return r.db.Where("task_id = ?", taskID).Delete(&TaskVMSnapshot{}).Error
}

// ==============================================================================
// TaskAnalysisJobRepository 任务分析子任务仓储 (新)
// ==============================================================================

type TaskAnalysisJobRepository struct {
	db *gorm.DB
}

func NewTaskAnalysisJobRepository() *TaskAnalysisJobRepository {
	return &TaskAnalysisJobRepository{db: DB}
}

func (r *TaskAnalysisJobRepository) Create(job *TaskAnalysisJob) error {
	return r.db.Create(job).Error
}

func (r *TaskAnalysisJobRepository) Update(job *TaskAnalysisJob) error {
	return r.db.Save(job).Error
}

func (r *TaskAnalysisJobRepository) GetByID(id uint) (*TaskAnalysisJob, error) {
	var job TaskAnalysisJob
	err := r.db.First(&job, id).Error
	if err != nil {
		return nil, err
	}
	return &job, nil
}

func (r *TaskAnalysisJobRepository) GetByTaskAndType(taskID uint, jobType string) (*TaskAnalysisJob, error) {
	var job TaskAnalysisJob
	// 获取最新的执行记录（按 created_at DESC）
	err := r.db.Where("task_id = ? AND job_type = ?", taskID, jobType).
		Order("created_at DESC").
		First(&job).Error
	if err != nil {
		return nil, err
	}
	return &job, nil
}

func (r *TaskAnalysisJobRepository) ListByTaskID(taskID uint) ([]TaskAnalysisJob, error) {
	var jobs []TaskAnalysisJob
	// 只返回每个 job_type 的最新执行记录
	// 使用子查询获取每个 job_type 的最大 id
	err := r.db.Raw(`
		SELECT * FROM task_analysis_jobs
		WHERE id IN (
			SELECT MAX(id) FROM task_analysis_jobs
			WHERE task_id = ?
			GROUP BY job_type
		)
		ORDER BY job_type ASC
	`, taskID).Find(&jobs).Error
	return jobs, err
}

func (r *TaskAnalysisJobRepository) UpdateStatus(id uint, status string, progress int) error {
	return r.db.Model(&TaskAnalysisJob{}).Where("id = ?", id).Updates(map[string]interface{}{
		"status":   status,
		"progress": progress,
	}).Error
}

func (r *TaskAnalysisJobRepository) UpdateResult(id uint, status string, result string, resultCount int) error {
	return r.db.Model(&TaskAnalysisJob{}).Where("id = ?", id).Updates(map[string]interface{}{
		"status":       status,
		"result":       result,
		"result_count": resultCount,
	}).Error
}

// ==============================================================================
// AnalysisFindingRepository 分析发现仓储 (新)
// ==============================================================================

type AnalysisFindingRepository struct {
	db *gorm.DB
}

func NewAnalysisFindingRepository() *AnalysisFindingRepository {
	return &AnalysisFindingRepository{db: DB}
}

func (r *AnalysisFindingRepository) Create(finding *AnalysisFinding) error {
	return r.db.Create(finding).Error
}

func (r *AnalysisFindingRepository) BatchCreate(findings []AnalysisFinding) error {
	if len(findings) == 0 {
		return nil
	}
	return r.db.CreateInBatches(findings, 100).Error
}

func (r *AnalysisFindingRepository) ListByTaskAndJobType(taskID uint, jobType string) ([]AnalysisFinding, error) {
	// 子查询：获取该任务下每个 job_type 的最新执行记录
	latestJobsQuery := r.db.Table("task_analysis_jobs").
		Select("job_type, MAX(id) as latest_job_id").
		Where("task_id = ?", taskID).
		Group("job_type")

	if jobType != "" {
		latestJobsQuery = latestJobsQuery.Where("job_type = ?", jobType)
	}

	// 主查询：只关联最新执行的分析发现
	var findings []AnalysisFinding
	err := r.db.
		Table("analysis_findings").
		Joins("JOIN (?) AS latest_jobs ON analysis_findings.job_id = latest_jobs.latest_job_id AND analysis_findings.job_type = latest_jobs.job_type", latestJobsQuery).
		Where("analysis_findings.task_id = ?", taskID).
		Where("analysis_findings.deleted_at IS NULL").
		Order("analysis_findings.severity DESC, analysis_findings.created_at DESC").
		Find(&findings).Error

	return findings, err
}

func (r *AnalysisFindingRepository) ListByTaskID(taskID uint) ([]AnalysisFinding, error) {
	// 只返回最后一次执行的分析结果
	// 子查询：获取该任务下每个 job_type 的最新执行记录
	latestJobsQuery := r.db.Table("task_analysis_jobs").
		Select("job_type, MAX(id) as latest_job_id").
		Where("task_id = ?", taskID).
		Group("job_type")

	// 主查询：只关联最新执行的分析发现
	var findings []AnalysisFinding
	err := r.db.
		Table("analysis_findings").
		Joins("JOIN (?) AS latest_jobs ON analysis_findings.job_id = latest_jobs.latest_job_id AND analysis_findings.job_type = latest_jobs.job_type", latestJobsQuery).
		Where("analysis_findings.task_id = ?", taskID).
		Where("analysis_findings.deleted_at IS NULL").
		Order("analysis_findings.job_type ASC, analysis_findings.severity DESC, analysis_findings.created_at DESC").
		Find(&findings).Error

	return findings, err
}

func (r *AnalysisFindingRepository) DeleteByTaskID(taskID uint) error {
	return r.db.Where("task_id = ?", taskID).Delete(&AnalysisFinding{}).Error
}

func (r *AnalysisFindingRepository) CountByTaskAndSeverity(taskID uint, severity string) (int64, error) {
	var count int64
	query := r.db.Model(&AnalysisFinding{}).Where("task_id = ?", taskID)
	if severity != "" {
		query = query.Where("severity = ?", severity)
	}
	err := query.Count(&count).Error
	return count, err
}

// ==============================================================================
// TaskReportRepository 任务报告仓储 (新)
// ==============================================================================

type TaskReportRepository struct {
	db *gorm.DB
}

func NewTaskReportRepository() *TaskReportRepository {
	return &TaskReportRepository{db: DB}
}

func (r *TaskReportRepository) Create(report *TaskReport) error {
	return r.db.Create(report).Error
}

func (r *TaskReportRepository) Update(report *TaskReport) error {
	return r.db.Save(report).Error
}

func (r *TaskReportRepository) GetByID(id uint) (*TaskReport, error) {
	var report TaskReport
	err := r.db.First(&report, id).Error
	if err != nil {
		return nil, err
	}
	return &report, nil
}

func (r *TaskReportRepository) ListByTaskID(taskID uint) ([]TaskReport, error) {
	var reports []TaskReport
	err := r.db.Where("task_id = ?", taskID).Order("created_at DESC").Find(&reports).Error
	return reports, err
}

func (r *TaskReportRepository) List(limit, offset int) ([]TaskReport, error) {
	var reports []TaskReport
	err := r.db.Order("created_at DESC").Limit(limit).Offset(offset).Find(&reports).Error
	return reports, err
}

func (r *TaskReportRepository) Delete(id uint) error {
	return r.db.Delete(&TaskReport{}, id).Error
}

// ==============================================================================
// SettingsRepository 系统配置仓储
// ==============================================================================

type SettingsRepository struct {
	db *gorm.DB
}

func NewSettingsRepository() *SettingsRepository {
	return &SettingsRepository{db: DB}
}

func (r *SettingsRepository) Get(key string) (*Settings, error) {
	var setting Settings
	err := r.db.Where("key = ?", key).First(&setting).Error
	if err != nil {
		return nil, err
	}
	return &setting, nil
}

func (r *SettingsRepository) Set(key, value, typ string) error {
	var setting Settings
	err := r.db.Where("key = ?", key).First(&setting).Error
	if err == gorm.ErrRecordNotFound {
		setting = Settings{
			Key:   key,
			Value: value,
			Type:  typ,
		}
		return r.db.Create(&setting).Error
	}
	if err != nil {
		return err
	}
	setting.Value = value
	setting.Type = typ
	return r.db.Save(&setting).Error
}

func (r *SettingsRepository) Delete(key string) error {
	return r.db.Where("key = ?", key).Delete(&Settings{}).Error
}

func (r *SettingsRepository) List() ([]Settings, error) {
	var settings []Settings
	err := r.db.Find(&settings).Error
	return settings, err
}

// ==============================================================================
// TaskLogRepository 任务日志仓储
// ==============================================================================

type TaskLogRepository struct {
	db *gorm.DB
}

func NewTaskLogRepository() *TaskLogRepository {
	return &TaskLogRepository{db: DB}
}

func (r *TaskLogRepository) Create(log *TaskLog) error {
	return r.db.Create(log).Error
}

func (r *TaskLogRepository) ListByTaskID(taskID uint, limit, offset int) ([]TaskLog, int64, error) {
	var logs []TaskLog
	var total int64

	query := r.db.Model(&TaskLog{}).Where("task_id = ?", taskID)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	err := query.Order("created_at DESC").Find(&logs).Error
	return logs, total, err
}

func (r *TaskLogRepository) ListByJobID(jobID uint, limit, offset int) ([]TaskLog, int64, error) {
	var logs []TaskLog
	var total int64

	query := r.db.Model(&TaskLog{}).Where("job_id = ?", jobID)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	err := query.Order("created_at DESC").Find(&logs).Error
	return logs, total, err
}

func (r *TaskLogRepository) ListByOperation(taskID uint, operation string, limit, offset int) ([]TaskLog, error) {
	var logs []TaskLog
	query := r.db.Where("task_id = ? AND operation = ?", taskID, operation)

	if limit > 0 {
		query = query.Limit(limit)
	}
	if offset > 0 {
		query = query.Offset(offset)
	}

	err := query.Order("created_at DESC").Find(&logs).Error
	return logs, err
}

// CreateLog 创建日志的便捷方法
func (r *TaskLogRepository) CreateLog(taskID uint, jobID *uint, operation, category, title, message string, config, result interface{}, duration int64) error {
	log := &TaskLog{
		TaskID:    taskID,
		JobID:     jobID,
		Operation: operation,
		Category:  category,
		Title:     title,
		Message:   message,
		Duration:  duration,
	}

	if config != nil {
		if b, err := json.Marshal(config); err == nil {
			log.Config = string(b)
		}
	}

	if result != nil {
		if b, err := json.Marshal(result); err == nil {
			log.Result = string(b)
		}
	}

	return r.Create(log)
}
