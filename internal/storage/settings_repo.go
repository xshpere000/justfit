// Package storage 数据仓储实现
package storage

import (
	"gorm.io/gorm"
)

// SettingsRepository 系统配置仓储
type SettingsRepository struct {
	db *gorm.DB
}

// NewSettingsRepository 创建系统配置仓储
func NewSettingsRepository() *SettingsRepository {
	return &SettingsRepository{db: DB}
}

// Get 根据键获取配置
func (r *SettingsRepository) Get(key string) (*Settings, error) {
	var setting Settings
	err := r.db.Where("key = ?", key).First(&setting).Error
	if err != nil {
		return nil, err
	}
	return &setting, nil
}

// Set 设置配置
func (r *SettingsRepository) Set(key, value, settingType string) error {
	var setting Settings
	err := r.db.Where("key = ?", key).First(&setting).Error

	if err == gorm.ErrRecordNotFound {
		setting = Settings{
			Key:   key,
			Value: value,
			Type:  settingType,
		}
		return r.db.Create(&setting).Error
	}

	if err != nil {
		return err
	}

	setting.Value = value
	setting.Type = settingType
	return r.db.Save(&setting).Error
}

// GetAll 获取所有配置
func (r *SettingsRepository) GetAll() ([]Settings, error) {
	var settings []Settings
	err := r.db.Find(&settings).Error
	return settings, err
}

// Delete 删除配置
func (r *SettingsRepository) Delete(key string) error {
	return r.db.Where("key = ?", key).Delete(&Settings{}).Error
}
