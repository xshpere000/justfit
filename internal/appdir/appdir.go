// Package appdir 提供应用数据目录管理功能
// 统一管理应用数据、日志等目录的创建和获取
package appdir

import (
	"os"
	"path/filepath"
	goruntime "runtime"
)

// AppDataDir 应用数据目录名称
const AppDataDir = ".justfit"

// GetUserHomeDir 获取用户主目录（跨平台）
func GetUserHomeDir() (string, error) {
	// 优先使用 os.UserHomeDir()，这是跨平台的标准方法
	homeDir, err := os.UserHomeDir()
	if err == nil && homeDir != "" {
		return homeDir, nil
	}

	// Windows 备用方案
	if goruntime.GOOS == "windows" {
		// 尝试 USERPROFILE
		if homeDir := os.Getenv("USERPROFILE"); homeDir != "" {
			return homeDir, nil
		}
		// 尝试 HOMEDRIVE + HOMEPATH
		if homeDrive := os.Getenv("HOMEDRIVE"); homeDrive != "" {
			if homePath := os.Getenv("HOMEPATH"); homePath != "" {
				return filepath.Join(homeDrive, homePath), nil
			}
		}
	}

	// Unix 备用方案
	if homeDir := os.Getenv("HOME"); homeDir != "" {
		return homeDir, nil
	}

	// 最终备用方案
	return "", os.ErrInvalid
}

// getPlatformStandardDir 获取符合各平台标准的应用数据目录
func getPlatformStandardDir() (string, error) {
	homeDir, err := GetUserHomeDir()
	if err != nil {
		return "", err
	}

	switch goruntime.GOOS {
	case "windows":
		// Windows: %APPDATA% (即 %USERPROFILE%\AppData\Roaming)
		if appData := os.Getenv("APPDATA"); appData != "" {
			return filepath.Join(appData, "justfit"), nil
		}
		// 备用方案
		return filepath.Join(homeDir, "AppData", "Roaming", "justfit"), nil

	case "darwin":
		// macOS: ~/Library/Application Support
		return filepath.Join(homeDir, "Library", "Application Support", "justfit"), nil

	default:
		// Linux: 遵循 XDG 标准
		// 如果 XDG_DATA_HOME 设置则使用，否则 ~/.local/share
		if xdgData := os.Getenv("XDG_DATA_HOME"); xdgData != "" {
			return filepath.Join(xdgData, "justfit"), nil
		}
		return filepath.Join(homeDir, ".local", "share", "justfit"), nil
	}
}

// GetAppDataDir 获取应用数据目录
// 优先使用环境变量 JUSTFIT_DATA_DIR 指定的目录
// 否则使用平台标���的应用数据目录
func GetAppDataDir() (string, error) {
	// 首先检查环境变量是否有显式指定
	if customDir := os.Getenv("JUSTFIT_DATA_DIR"); customDir != "" {
		return customDir, nil
	}

	// 使用平台标准的应用数据目录
	return getPlatformStandardDir()
}

// GetLogDir 获取日志目录
func GetLogDir() (string, error) {
	appDataDir, err := GetAppDataDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(appDataDir, "logs"), nil
}

// GetDBPath 获取数据库文件路径
func GetDBPath() (string, error) {
	appDataDir, err := GetAppDataDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(appDataDir, "justfit.db"), nil
}

// EnsureAppDirs 确保应用所需的所有目录都存在
func EnsureAppDirs() error {
	appDataDir, err := GetAppDataDir()
	if err != nil {
		return err
	}

	// 创建应用数据目录
	if err := os.MkdirAll(appDataDir, 0755); err != nil {
		return err
	}

	// 创建日志目录
	logDir, err := GetLogDir()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return err
	}

	return nil
}

// MustGetAppDataDir 获取应用数据目录，如果失败则 panic
func MustGetAppDataDir() string {
	dir, err := GetAppDataDir()
	if err != nil {
		panic("failed to get app data dir: " + err.Error())
	}
	return dir
}

// MustGetLogDir 获取日志目录，如果失败则 panic
func MustGetLogDir() string {
	dir, err := GetLogDir()
	if err != nil {
		panic("failed to get log dir: " + err.Error())
	}
	return dir
}

// MustGetDBPath 获取数据库文件路径，如果失败则 panic
func MustGetDBPath() string {
	path, err := GetDBPath()
	if err != nil {
		panic("failed to get db path: " + err.Error())
	}
	return path
}

// Init 初始化并确保目录存在，返回应用数据目录路径
// 这个函数应该在应用启动时调用
func Init() (string, error) {
	if err := EnsureAppDirs(); err != nil {
		return "", err
	}
	return GetAppDataDir()
}
