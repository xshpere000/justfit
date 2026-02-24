// Package logger 提供结构化日志功能
package logger

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Logger 日志器接口
type Logger interface {
	// 基础日志方法
	Debug(msg string, fields ...Field)
	Info(msg string, fields ...Field)
	Warn(msg string, fields ...Field)
	Error(msg string, fields ...Field)

	// 子日志器（带预设字段）
	With(fields ...Field) Logger

	// 设置级别
	SetLevel(level Level)
	GetLevel() Level

	// 同步缓冲区
	Sync() error

	// 关闭
	Close() error
}

// Config 日志配置
type Config struct {
	Level      Level    // 日志级别
	Outputs    []Output // 输出器列表
	Format     Format   // 输出格式
	CallerSkip int      // 调用栈跳过层数
}

// DefaultConfig 默认配置
func DefaultConfig() *Config {
	return &Config{
		Level:      INFO,
		Format:     FormatJSON,
		CallerSkip: 1,
	}
}

// loggerImpl 日志器实现
type loggerImpl struct {
	mu      sync.RWMutex
	config  *Config
	outputs []Output
	fields  []Field // 预设字段
}

// New 创建新日志器
func New(config *Config) Logger {
	if config == nil {
		config = DefaultConfig()
	}

	// 如果没有输出器，添加默认的控制台输出
	if len(config.Outputs) == 0 {
		config.Outputs = []Output{
			NewConsoleOutput(config.Format),
		}
	}

	return &loggerImpl{
		config:  config,
		outputs: config.Outputs,
		fields:  make([]Field, 0),
	}
}

// Debug 记录调试日志
func (l *loggerImpl) Debug(msg string, fields ...Field) {
	l.log(DEBUG, msg, fields)
}

// Info 记录信息日志
func (l *loggerImpl) Info(msg string, fields ...Field) {
	l.log(INFO, msg, fields)
}

// Warn 记录警告日志
func (l *loggerImpl) Warn(msg string, fields ...Field) {
	l.log(WARN, msg, fields)
}

// Error 记录错误日志
func (l *loggerImpl) Error(msg string, fields ...Field) {
	l.log(ERROR, msg, fields)
}

// log 内部日志方法
func (l *loggerImpl) log(level Level, msg string, fields []Field) {
	// 级别过滤
	if level < l.GetLevel() {
		return
	}

	// 获取调用信息
	caller := getCaller(l.config.CallerSkip + 2)

	// 创建日志条目
	entry := &Entry{
		Timestamp: time.Now(),
		Level:     level,
		Message:   msg,
		File:      caller.file,
		Line:      caller.line,
		Function:  caller.function,
		Fields:    make(map[string]interface{}),
	}

	// 合并字段（预设字段 + 本次字段）
	l.mu.RLock()
	for _, f := range l.fields {
		entry.Fields[f.Key] = f.Value
	}
	l.mu.RUnlock()

	for _, f := range fields {
		if f.Key == "error" {
			if err, ok := f.Value.(string); ok {
				entry.Error = err
			}
		}
		entry.Fields[f.Key] = f.Value
	}

	// 写入所有输出器
	for _, output := range l.outputs {
		_ = output.Write(entry)
	}
}

// With 创建带预设字段的子日志器
func (l *loggerImpl) With(fields ...Field) Logger {
	l.mu.Lock()
	defer l.mu.Unlock()

	newFields := make([]Field, len(l.fields)+len(fields))
	copy(newFields, l.fields)
	copy(newFields[len(l.fields):], fields)

	return &loggerImpl{
		config:  l.config,
		outputs: l.outputs,
		fields:  newFields,
	}
}

// SetLevel 设置日志级别
func (l *loggerImpl) SetLevel(level Level) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.config.Level = level
}

// GetLevel 获取日志级别
func (l *loggerImpl) GetLevel() Level {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.config.Level
}

// Sync 同步缓冲区
func (l *loggerImpl) Sync() error {
	var firstErr error
	for _, output := range l.outputs {
		if err := output.Sync(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// Close 关闭日志器
func (l *loggerImpl) Close() error {
	var firstErr error
	for _, output := range l.outputs {
		if closer, ok := output.(interface{ Close() error }); ok {
			if err := closer.Close(); err != nil && firstErr == nil {
				firstErr = err
			}
		}
	}
	return firstErr
}

// ==================== 全局日志器 ====================

var (
	global Logger
	once   sync.Once
)

// Init 初始化全局日志器
func Init(config *Config) {
	once.Do(func() {
		global = New(config)
	})
}

// InitWithFile 初始化日志器（输出到文件）
func InitWithFile(logDir string, levelStr string) error {
	// 创建日志目录
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return fmt.Errorf("创建日志目录失败: %w", err)
	}

	config := &Config{
		Level:      ParseLevel(levelStr),
		Format:     FormatJSON,
		CallerSkip: 1,
	}

	// 添加多路输出
	config.Outputs = []Output{
		NewConsoleOutput(FormatText), // 控制台使用文本格式
	}

	// 添加文件输出
	logFile := filepath.Join(logDir, "justfit.log")
	fileOutput, err := NewFileOutput(logFile)
	if err == nil {
		config.Outputs = append(config.Outputs, fileOutput)
	}

	Init(config)
	return nil
}

// Get 获取全局日志器
func Get() Logger {
	if global == nil {
		global = New(DefaultConfig())
	}
	return global
}

// ==================== 全局便捷方法 ====================

// Debug 记录调试日志
func Debug(msg string, fields ...Field) {
	Get().Debug(msg, fields...)
}

// Info 记录信息日志
func Info(msg string, fields ...Field) {
	Get().Info(msg, fields...)
}

// Warn 记录警告日志
func Warn(msg string, fields ...Field) {
	Get().Warn(msg, fields...)
}

// Error 记录错误日志
func Error(msg string, fields ...Field) {
	Get().Error(msg, fields...)
}

// With 创建带预设字段的子日志器
func With(fields ...Field) Logger {
	return Get().With(fields...)
}

// SetLevel 设置全局日志级别
func SetLevel(level Level) {
	Get().SetLevel(level)
}

// Sync 同步全局日志器
func Sync() error {
	if global != nil {
		return global.Sync()
	}
	return nil
}

// Close 关闭全局日志器
func Close() error {
	if global != nil {
		return global.Close()
	}
	return nil
}
