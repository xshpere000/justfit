package main

import (
	"embed"
	"os"
	"path/filepath"
	"runtime"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
)

//go:embed all:frontend/dist
var assets embed.FS

// getFixedCacheDir 返回固定的缓存目录，与二进制文件名无关
func getFixedCacheDir() string {
	homeDir, _ := os.UserHomeDir()

	switch runtime.GOOS {
	case "windows":
		// Windows: 使用 LocalAppData，固定为 justfit_webview
		// 例如: C:\Users\<user>\AppData\Local\justfit_webview
		localAppData := os.Getenv("LOCALAPPDATA")
		if localAppData == "" {
			localAppData = filepath.Join(homeDir, "AppData", "Local")
		}
		return filepath.Join(localAppData, "justfit_webview")

	case "darwin":
		// macOS: 使用 Caches 目录
		// 例如: ~/Library/Caches/justfit_webview
		return filepath.Join(homeDir, "Library", "Caches", "justfit_webview")

	case "linux":
		// Linux: 遵循 XDG 规范，使用缓存目录
		// 例如: ~/.cache/justfit_webview
		if xdgCache := os.Getenv("XDG_CACHE_HOME"); xdgCache != "" {
			return filepath.Join(xdgCache, "justfit_webview")
		}
		return filepath.Join(homeDir, ".cache", "justfit_webview")

	default:
		return filepath.Join(homeDir, ".justfit_webview")
	}
}

func main() {
	app := NewApp()

	// 获取固定的缓存目录（与二进制文件名无关）
	cacheDir := getFixedCacheDir()

	// 确保目录存在
	os.MkdirAll(cacheDir, 0755)

	opts := &options.App{
		Title:            "justfit",
		Width:            1024,
		Height:           640,
		MinWidth:         1024,
		MinHeight:        640,
		WindowStartState: options.Normal, // 默认正常窗口，不是全屏
		Frameless:        true,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},
		OnStartup:        app.startup,
		Bind: []interface{}{
			app,
		},
	}

	// Windows 必须设置 WebviewUserDataPath 来避免根据二进制名创建不同目录
	if runtime.GOOS == "windows" {
		opts.Windows = &windows.Options{
			WebviewUserDataPath: cacheDir,
		}
	}

	err := wails.Run(opts)
	if err != nil {
		println("Error:", err.Error())
	}
}
