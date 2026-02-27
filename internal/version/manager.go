// Package version 版本管理
package version

import (
	"fmt"
	"os"
	"path/filepath"

	"gorm.io/gorm"

	"justfit/internal/appdir"
	applogger "justfit/internal/logger"
	"justfit/internal/storage"
)

// 版本管理器
type Manager struct {
	db  *gorm.DB
	log applogger.Logger
}

// NewManager 创建版本管理器
func NewManager(db *gorm.DB) *Manager {
	return &Manager{
		db:  db,
		log: applogger.With(applogger.Str("component", "version.Manager")),
	}
}

// CheckVersion 检查数据库版本
// 返回: (是否需要重建, 当前版本, 错误信息)
func (m *Manager) CheckVersion() (needsRebuild bool, currentVersion string, err error) {
	// 从 settings 表读取版本
	var setting storage.Settings
	err = m.db.Where("key = ?", "app_version").First(&setting).Error

	if err != nil {
		if err == gorm.ErrRecordNotFound {
			// 首次运行，没有版本记录
			m.log.Debug("首次运行，未找到版本记录")
			return false, "", nil
		}
		m.log.Error("查询版本失败", applogger.Err(err))
		return false, "", fmt.Errorf("查询版本失败: %w", err)
	}

	currentVersion = setting.Value
	m.log.Debug("读取到版本信息", applogger.String("version", currentVersion))

	// 检查是否是需要清理的大版本
	if m.isMajorVersion(currentVersion) {
		m.log.Warn("检测到大版本，需要重建数据库",
			applogger.String("currentVersion", currentVersion),
			applogger.String("latestVersion", Version))
		return true, currentVersion, nil
	}

	m.log.Debug("版本检查通过", applogger.String("version", currentVersion))
	return false, currentVersion, nil
}

// isMajorVersion 判断是否是需要清理的大版本
func (m *Manager) isMajorVersion(ver string) bool {
	for _, major := range MajorVersions {
		if ver == major {
			return true
		}
	}
	return false
}

// SaveVersion 保存当前版本
func (m *Manager) SaveVersion() error {
	setting := storage.Settings{
		Key:   "app_version",
		Value: Version,
		Type:  "string",
	}
	if err := m.db.Save(&setting).Error; err != nil {
		m.log.Error("保存版本失败", applogger.Err(err))
		return err
	}
	m.log.Info("已保存版本信息", applogger.String("version", Version))
	return nil
}

// RebuildDatabase 重建数据库（删除旧数据，重新创建表结构）
func (m *Manager) RebuildDatabase() error {
	// 获取数据库路径
	dataDir, err := appdir.GetAppDataDir()
	if err != nil {
		return fmt.Errorf("获取数据目录失败: %w", err)
	}

	dbPath := filepath.Join(dataDir, "justfit.db")
	m.log.Info("开始删除数据库文件", applogger.String("path", dbPath))

	// 关闭当前连接
	sqlDB, err := m.db.DB()
	if err == nil {
		m.log.Debug("关闭数据库连接")
		sqlDB.Close()
	}

	// 删除数据库文件
	if err := os.Remove(dbPath); err != nil {
		if !os.IsNotExist(err) {
			m.log.Error("删除数据库文件失败", applogger.Err(err), applogger.String("path", dbPath))
			return fmt.Errorf("删除数据库文件失败: %w", err)
		}
		m.log.Debug("数据库文件不存在，跳过删除")
	} else {
		m.log.Info("已删除数据库文件")
	}

	// 删除相关的 -journal 和 -wal 文件
	for _, suffix := range []string{"-journal", "-wal", "-shm"} {
		file := dbPath + suffix
		if err := os.Remove(file); err != nil {
			if !os.IsNotExist(err) {
				m.log.Debug("删除临时文件失败", applogger.Err(err), applogger.String("file", file))
			}
		} else {
			m.log.Debug("已删除临时文件", applogger.String("file", file))
		}
	}

	return nil
}

// GetDatabaseSize 获取数据库文件大小
func (m *Manager) GetDatabaseSize() (int64, error) {
	dataDir, err := appdir.GetAppDataDir()
	if err != nil {
		return 0, err
	}

	dbPath := filepath.Join(dataDir, "justfit.db")
	info, err := os.Stat(dbPath)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		return 0, err
	}

	size := info.Size()
	m.log.Debug("获取数据库大小", applogger.Int64("bytes", size))
	return size, nil
}

// GetVersionInfo 获取版本信息
func (m *Manager) GetVersionInfo() (current string, latest string, needsUpgrade bool) {
	return Version, Version, false
}

// HasData 检查数据库中是否有实际数据
func (m *Manager) HasData() bool {
	var count int64

	// 检查 connections 表是否有数据
	if err := m.db.Table("connections").Count(&count).Error; err == nil && count > 0 {
		m.log.Debug("检测到数据", applogger.String("table", "connections"), applogger.Int64("count", count))
		return true
	}

	// 检查 tasks 表是否有数据
	if err := m.db.Table("tasks").Count(&count).Error; err == nil && count > 0 {
		m.log.Debug("检测到数据", applogger.String("table", "tasks"), applogger.Int64("count", count))
		return true
	}

	// 检查 vms 表是否有数据
	if err := m.db.Table("vms").Count(&count).Error; err == nil && count > 0 {
		m.log.Debug("检测到数据", applogger.String("table", "vms"), applogger.Int64("count", count))
		return true
	}

	m.log.Debug("未检测到任何数据")
	return false
}
