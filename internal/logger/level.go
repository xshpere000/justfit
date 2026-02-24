// Package logger 提供结构化日志功能
package logger

// Level 日志级别
type Level int

const (
	// DEBUG 调试信息，用于开发排查问题
	DEBUG Level = iota
	// INFO 常规信息，记录正常业务流程
	INFO
	// WARN 警告信息，潜在问题但不影响运行
	WARN
	// ERROR 错误信息，功能异常但程序可继续
	ERROR
)

// String 返回级别字符串
func (l Level) String() string {
	switch l {
	case DEBUG:
		return "DEBUG"
	case INFO:
		return "INFO"
	case WARN:
		return "WARN"
	case ERROR:
		return "ERROR"
	default:
		return "UNKNOWN"
	}
}

// ParseLevel 解析日志级别字符串
func ParseLevel(s string) Level {
	switch s {
	case "DEBUG", "debug":
		return DEBUG
	case "INFO", "info":
		return INFO
	case "WARN", "WARNING", "warn", "warning":
		return WARN
	case "ERROR", "error":
		return ERROR
	default:
		return INFO
	}
}

// Color 返回级别的颜色代码
func (l Level) Color() string {
	switch l {
	case DEBUG:
		return "\033[36m" // 青色
	case INFO:
		return "\033[32m" // 绿色
	case WARN:
		return "\033[33m" // 黄色
	case ERROR:
		return "\033[31m" // 红色
	default:
		return "\033[0m" // 默认
	}
}

// ResetColor 重置颜色
func ResetColor() string {
	return "\033[0m"
}
