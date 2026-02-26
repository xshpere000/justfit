// Package storage 提供数据库操作
package storage

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"justfit/internal/appdir"
)

// DB 数据库实例
var DB *gorm.DB

// Config 数据库配置
type Config struct {
	DataDir string // 数据目录，为空时使用默认路径
}

// Init 初始化数据库
// 使用 appdir 模块统一获取应用数据目录
func Init(cfg *Config) error {
	if cfg.DataDir == "" {
		// 使用 appdir 模块获取应用数据目录
		dataDir, err := appdir.GetAppDataDir()
		if err != nil {
			return fmt.Errorf("获取应用数据目录失败: %w", err)
		}
		cfg.DataDir = dataDir
	}

	// 确保数据目录存在
	if err := os.MkdirAll(cfg.DataDir, 0755); err != nil {
		return fmt.Errorf("创建数据目录失败: %w", err)
	}

	dbPath := filepath.Join(cfg.DataDir, "justfit.db")

	// 打开数据库
	// 使用默认命名策略（蛇形），保证数据正常流转
	db, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		return fmt.Errorf("打开数据库失败: %w", err)
	}

	DB = db

	// 自动迁移表结构
	if err := autoMigrate(); err != nil {
		return fmt.Errorf("数据库迁移失败: %w", err)
	}

	return nil
}

// autoMigrate 自动迁移表结构
func autoMigrate() error {
	return DB.AutoMigrate(
		// 基础资源层
		&Connection{},
		&Cluster{},
		&Host{},
		&VM{},
		&VMMetric{}, // 新表名

		// 任务层
		&AssessmentTask{},  // 新表名 (原 Task)
		&TaskVMSnapshot{},
		&TaskAnalysisJob{},  // 新表名 (原 TaskAnalysisResult)
		&TaskLog{},          // 任务操作日志

		// 输出层
		&AnalysisFinding{}, // 新增
		&TaskReport{},      // 新表名 (原 Report)

		// 系统配置层
		&Settings{},
	)
}

// Close 关闭数据库连接
func Close() error {
	if DB != nil {
		sqlDB, err := DB.DB()
		if err != nil {
			return err
		}
		return sqlDB.Close()
	}
	return nil
}

// GetDB 获取数据库实例
func GetDB() *gorm.DB {
	return DB
}

// Repositories 数据仓储
type Repositories struct {
	Connection        *ConnectionRepository
	Cluster           *ClusterRepository
	Host              *HostRepository
	VM                *VMRepository
	Metric            *MetricRepository // 向后兼容 (实际使用 VMMetric)
	VMMetric          *MetricRepository // 新名称
	Task              *TaskRepository   // 向后兼容 (实际使用 AssessmentTask)
	AssessmentTask    *TaskRepository   // 新名称
	TaskVMSnapshot    *TaskVMSnapshotRepository
	TaskAnalysis      *TaskAnalysisResultRepository // 向后兼容
	TaskAnalysisJob   *TaskAnalysisJobRepository     // 新名称
	TaskAnalysisResult *TaskAnalysisJobRepository    // 向后兼容别名
	TaskLog           *TaskLogRepository   // 任务日志
	AnalysisFinding   *AnalysisFindingRepository
	AnalysisResult    *AnalysisFindingRepository // 向后兼容别名
	Report            *TaskReportRepository // 向后兼容 (实际使用 TaskReport)
	TaskReport        *TaskReportRepository // 新名称
	Alert             *AnalysisFindingRepository // 向后兼容别名
	Settings          *SettingsRepository
}

// DB 返回底层数据库连接
func (r *Repositories) DB() *gorm.DB {
	return DB
}

// NewRepositories 创建数据仓储
func NewRepositories() *Repositories {
	taskRepo := NewTaskRepository()
	metricRepo := NewMetricRepository()
	findingRepo := NewAnalysisFindingRepository()

	return &Repositories{
		Connection:        NewConnectionRepository(),
		Cluster:           NewClusterRepository(),
		Host:              NewHostRepository(),
		VM:                NewVMRepository(),
		Metric:            metricRepo, // 向后兼容
		VMMetric:          metricRepo,
		Task:              taskRepo,   // 向后兼容
		AssessmentTask:    taskRepo,
		TaskVMSnapshot:    NewTaskVMSnapshotRepository(),
		TaskAnalysis:      NewTaskAnalysisJobRepository(), // 向后兼容
		TaskAnalysisJob:   NewTaskAnalysisJobRepository(),
		TaskAnalysisResult: NewTaskAnalysisJobRepository(), // 向后兼容别名
		TaskLog:           NewTaskLogRepository(),
		AnalysisFinding:   findingRepo,
		AnalysisResult:    findingRepo, // 向后兼容别名
		Report:            NewTaskReportRepository(), // 向后兼容
		TaskReport:        NewTaskReportRepository(),
		Alert:             findingRepo, // 向后兼容别名
		Settings:          NewSettingsRepository(),
	}
}
