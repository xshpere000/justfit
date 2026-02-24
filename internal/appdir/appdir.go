// Package appdir 提供应用数据目录管理功能
// 统一管理应用数据、日志等目录的创建和获取
package appdir

import (
	"os"
	"path/filepath"
	goruntime "runtime"
	"strings"
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

// IsDevMode 检测是否运行在开发模式
func IsDevMode(ctx interface{}) bool {
	// 方法1: 检查命令行参数
	for _, arg := range os.Args {
		if strings.Contains(arg, "dev") || strings.Contains(arg, "-dev") {
			return true
		}
	}

	// 方法2: 检查环境变量（wails dev 会设置特定环境变量）
	if wailsDev := os.Getenv("WAILS_DEV"); wailsDev != "" {
		return true
	}

	// 方法3: 如果传入了 context，可以使用 wailsruntime 检查
	if ctx != nil {
		// 尝试类型断言获取 Wails 环境信息
		if wailsCtx, ok := ctx.(interface{ Environment() map[string]string }); ok {
			env := wailsCtx.Environment()
			if _, dev := env["dev"]; dev {
				return true
			}
		}
	}

	return false
}

// GetAppDataDir 获取应用数据目录
// 开发模式下可以返回项目根目录的 .justfit 目录，方便调试
func GetAppDataDir(ctx interface{}) (string, error) {
	// 首先检查环境变量是否有显式指定
	if customDir := os.Getenv("JUSTFIT_DATA_DIR"); customDir != "" {
		return customDir, nil
	}

	// 检查是否强制使用生产模式目录（即使在开发模式）
	if forceProd := os.Getenv("JUSTFIT_FORCE_PROD_MODE"); forceProd == "1" || forceProd == "true" {
		return getPlatformStandardDir()
	}

	// 检测是否是开发模式
	isDev := IsDevMode(ctx)

	if isDev {
		// 开发模式：使用项目根目录的 .justfit 目录
		// 获取可执行文件所在目录
		exePath, err := os.Executable()
		if err != nil {
			// 如果获取失败，使用当前工作目录
			exePath = "."
		}

		// 对于 wails dev，可执行文件在临时目录，应该使用项目目录
		// 检查当前工作目录
		cwd, err := os.Getwd()
		if err == nil && cwd != "" {
			// 检查是否存在 frontend 目录（项目根目录标识）
			if _, err := os.Stat(filepath.Join(cwd, "frontend")); err == nil {
				return filepath.Join(cwd, ".justfit"), nil
			}
		}

		// 尝试获取项目根目录
		if exePath != "." {
			dir := filepath.Dir(exePath)
			// 向上查找项目根目录
			for i := 0; i < 4; i++ {
				if _, err := os.Stat(filepath.Join(dir, "frontend")); err == nil {
					return filepath.Join(dir, ".justfit"), nil
				}
				parent := filepath.Dir(dir)
				if parent == dir {
					break
				}
				dir = parent
			}
		}

		// 兜底：使用当前工作目录
		cwd = "."
		if c, err := os.Getwd(); err == nil {
			cwd = c
		}
		return filepath.Join(cwd, ".justfit"), nil
	}

	// 生产模式：使用符合各平台标准的应用数据目录
	return getPlatformStandardDir()
}

// GetLogDir 获取日志目录
func GetLogDir(ctx interface{}) (string, error) {
	appDataDir, err := GetAppDataDir(ctx)
	if err != nil {
		return "", err
	}
	return filepath.Join(appDataDir, "logs"), nil
}

// GetDBPath 获取数据库文件路径
func GetDBPath(ctx interface{}) (string, error) {
	appDataDir, err := GetAppDataDir(ctx)
	if err != nil {
		return "", err
	}
	return filepath.Join(appDataDir, "justfit.db"), nil
}

// EnsureAppDirs 确保应用所需的所有目录都存在
func EnsureAppDirs(ctx interface{}) error {
	appDataDir, err := GetAppDataDir(ctx)
	if err != nil {
		return err
	}

	// 创建应用数据目录
	if err := os.MkdirAll(appDataDir, 0755); err != nil {
		return err
	}

	// 创建日志目录
	logDir, err := GetLogDir(ctx)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return err
	}

	return nil
}

// MustGetAppDataDir 获取应用数据目录，如果失败则 panic
func MustGetAppDataDir(ctx interface{}) string {
	dir, err := GetAppDataDir(ctx)
	if err != nil {
		panic("failed to get app data dir: " + err.Error())
	}
	return dir
}

// MustGetLogDir 获取日志目录，如果失败则 panic
func MustGetLogDir(ctx interface{}) string {
	dir, err := GetLogDir(ctx)
	if err != nil {
		panic("failed to get log dir: " + err.Error())
	}
	return dir
}

// MustGetDBPath 获取数据库文件路径，如果失败则 panic
func MustGetDBPath(ctx interface{}) string {
	path, err := GetDBPath(ctx)
	if err != nil {
		panic("failed to get db path: " + err.Error())
	}
	return path
}

// InitWithContext 初始化并确保目录存在，返回应用数据目录路径
// 这个函数应该在应用启动时调用
func InitWithContext(ctx interface{}) (string, error) {
	if err := EnsureAppDirs(ctx); err != nil {
		return "", err
	}
	return GetAppDataDir(ctx)
}

// GetWailsRuntime 获取 wails runtime（如果可用）
// 避免直接依赖 wails runtime 导致开发模式编译问题
var GetWailsRuntime func(ctx interface{}) interface{} = func(ctx interface{}) interface{} {
	// 这是一个兼容性函数，用于获取 wails runtime
	// 实际使用时直接传入 context 即可
	return nil
}
