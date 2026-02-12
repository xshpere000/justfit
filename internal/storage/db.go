// Package storage 提供数据库操作
package storage

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// DB 数据库实例
var DB *gorm.DB

// Config 数据库配置
type Config struct {
	DataDir string // 数据目录
}

// Init 初始化数据库
func Init(cfg *Config) error {
	if cfg.DataDir == "" {
		// 默认使用用户数据目录
		homeDir, err := os.UserHomeDir()
		if err != nil {
			return fmt.Errorf("获取用户目录失败: %w", err)
		}
		cfg.DataDir = filepath.Join(homeDir, ".justfit")
	}

	// 确保数据目录存在
	if err := os.MkdirAll(cfg.DataDir, 0755); err != nil {
		return fmt.Errorf("创建数据目录失败: %w", err)
	}

	dbPath := filepath.Join(cfg.DataDir, "justfit.db")

	// 打开数据库
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
		&Connection{},
		&Cluster{},
		&Host{},
		&VM{},
		&Metric{},
		&Task{},
		&TaskLog{},
		&Report{},
		&AnalysisResult{},
		&Alert{},
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

// Repositories 数据仓储
type Repositories struct {
	Connection     *ConnectionRepository
	Cluster        *ClusterRepository
	Host           *HostRepository
	VM             *VMRepository
	Metric         *MetricRepository
	Task           *TaskRepository
	Report         *ReportRepository
	AnalysisResult *AnalysisResultRepository
	Alert          *AlertRepository
	Settings       *SettingsRepository
}

// NewRepositories 创建数据仓储
func NewRepositories() *Repositories {
	return &Repositories{
		Connection:     NewConnectionRepository(),
		Cluster:        NewClusterRepository(),
		Host:           NewHostRepository(),
		VM:             NewVMRepository(),
		Metric:         NewMetricRepository(),
		Task:           NewTaskRepository(),
		Report:         NewReportRepository(),
		AnalysisResult: NewAnalysisResultRepository(),
		Alert:          NewAlertRepository(),
		Settings:       NewSettingsRepository(),
	}
}
