// Package version 提供统一的应用版本信息
//
// 版本号命名规范：主版本.次版本.修订版本 (MAJOR.MINOR.PATCH)
// - MAJOR: 重大架构变更，数据库不兼容升级
// - MINOR: 新功能添加，向后兼容
// - PATCH: Bug 修复，不影响功能
//
// 更新版本时，只需修改此文件中的版本常量即可
package version

// Version 当前应用版本
// 修改此版本号会自动影响整个应用的版本显示
const Version = "0.0.2"

// MajorVersions 需要清理历史数据的大版本列表
// 这些版本的数据库结构与当前版本不兼容，需要重建
//
// 注意：
// - 0.0.1 是基础底座版本，不在此列表中（底座版本不触发重建）
// - 只有后续发生数据库不兼容变更的版本才会加入此列表
var MajorVersions = []string{
	// 目前没有需要重建的大版本
	// 未来如果发生数据库结构不兼容变更，在此添加旧版本号
}

// VersionInfo 版本详细信息
type VersionInfo struct {
	Version       string   `json:"version"`       // 版本号
	MajorVersions []string `json:"majorVersions"` // 大版本列表
	IsDevelopment bool     `json:"isDevelopment"` // 是否开发版本
}

// GetVersionInfo 获取版本信息
func GetVersionInfo() VersionInfo {
	return VersionInfo{
		Version:       Version,
		MajorVersions: MajorVersions,
		IsDevelopment: isDevelopmentVersion(),
	}
}

// isDevelopmentVersion 判断是否为开发版本
func isDevelopmentVersion() bool {
	// 开发版本通常包含 "dev", "alpha", "beta", "rc" 等标识
	contains := []string{"dev", "alpha", "beta", "rc", "-"}
	for _, suffix := range contains {
		if containsStr(Version, suffix) {
			return true
		}
	}
	return false
}

// containsStr 检查字符串是否包含子串
func containsStr(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && (
		s[:len(substr)] == substr ||
		s[len(s)-len(substr):] == substr ||
		containsMiddle(s, substr)))
}

// containsMiddle 检查字符串中间是否包含子串
func containsMiddle(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
