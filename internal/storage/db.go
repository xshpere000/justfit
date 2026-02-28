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
	DataDir string
}

// Init 初始化数据库
func Init(cfg *Config) error {
	if cfg.DataDir == "" {
		dataDir, err := appdir.GetAppDataDir()
		if err != nil {
			return fmt.Errorf("获取应用数据目录失败: %w", err)
		}
		cfg.DataDir = dataDir
	}

	if err := os.MkdirAll(cfg.DataDir, 0755); err != nil {
		return fmt.Errorf("创建数据目录失败: %w", err)
	}

	dbPath := filepath.Join(cfg.DataDir, "justfit.db")

	db, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		return fmt.Errorf("打开数据库失败: %w", err)
	}

	DB = db

	if err := autoMigrate(); err != nil {
		return fmt.Errorf("数据库迁移失败: %w", err)
	}

	return nil
}

// autoMigrate 初始化数据库表结构（GORM 标准）
// - 空数据库：自动创建所有表、索引、外键
// - 现有数据库：自动添加新列（不修改现有数据）
// 注：每次启动都会执行，支持开发环境快速重置
func autoMigrate() error {
	return DB.AutoMigrate(
		// 基础资源层
		&Connection{},
		&Cluster{},
		&Host{},
		&VM{},
		&VMMetric{},

		// 任务层
		&AssessmentTask{},
		&TaskVMSnapshot{},
		&TaskAnalysisJob{},
		&TaskLog{},

		// 输出层
		&AnalysisFinding{},
		&TaskReport{},

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
	Connection      *ConnectionRepository
	Cluster         *ClusterRepository
	Host            *HostRepository
	VM              *VMRepository
	VMMetric        *MetricRepository
	AssessmentTask  *TaskRepository
	TaskVMSnapshot  *TaskVMSnapshotRepository
	TaskAnalysisJob *TaskAnalysisJobRepository
	TaskLog         *TaskLogRepository
	AnalysisFinding *AnalysisFindingRepository
	TaskReport      *TaskReportRepository
	Settings        *SettingsRepository
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
		Connection:      NewConnectionRepository(),
		Cluster:         NewClusterRepository(),
		Host:            NewHostRepository(),
		VM:              NewVMRepository(),
		VMMetric:        metricRepo,
		AssessmentTask:  taskRepo,
		TaskVMSnapshot:  NewTaskVMSnapshotRepository(),
		TaskAnalysisJob: NewTaskAnalysisJobRepository(),
		TaskLog:         NewTaskLogRepository(),
		AnalysisFinding: findingRepo,
		TaskReport:      NewTaskReportRepository(),
		Settings:        NewSettingsRepository(),
	}
}
