package task

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// LogLevel 日志级别
type LogLevel string

const (
	LogLevelDebug LogLevel = "debug"
	LogLevelInfo  LogLevel = "info"
	LogLevelWarn  LogLevel = "warn"
	LogLevelError LogLevel = "error"
)

// LogEntry 日志条目
type LogEntry struct {
	Timestamp time.Time `json:"timestamp"`
	Level     LogLevel  `json:"level"`
	Message   string    `json:"message"`
	TaskID    uint      `json:"taskId,omitempty"`
	TaskType  TaskType  `json:"taskType,omitempty"`
}

// Logger 任务日志记录器
type Logger struct {
	mu      sync.Mutex
	logDir  string
	file    *os.File
	entries []LogEntry
	maxSize int
	enabled bool
}

// NewLogger 创建日志记录器
func NewLogger(logDir string, maxSize int) (*Logger, error) {
	if maxSize <= 0 {
		maxSize = 1000
	}

	if err := os.MkdirAll(logDir, 0755); err != nil {
		return nil, fmt.Errorf("创建日志目录失败: %w", err)
	}

	logger := &Logger{
		logDir:  logDir,
		entries: make([]LogEntry, 0, maxSize),
		maxSize: maxSize,
		enabled: true,
	}

	return logger, nil
}

// Enable 启用日志
func (l *Logger) Enable() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.enabled = true
}

// Disable 禁用日志
func (l *Logger) Disable() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.enabled = false
}

// log 内部日志方法
func (l *Logger) log(level LogLevel, taskID uint, taskType TaskType, message string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if !l.enabled {
		return
	}

	entry := LogEntry{
		Timestamp: time.Now(),
		Level:     level,
		Message:   message,
		TaskID:    taskID,
		TaskType:  taskType,
	}

	// 添加到内存
	l.entries = append(l.entries, entry)

	// 限制内存中的日志数量
	if len(l.entries) > l.maxSize {
		l.entries = l.entries[1:]
	}

	// 写入文件
	if err := l.writeToFile(entry); err != nil {
		// 文件写入失败不影响程序运行
		fmt.Fprintf(os.Stderr, "写入日志文件失败: %v\n", err)
	}
}

// writeToFile 写入日志文件
func (l *Logger) writeToFile(entry LogEntry) error {
	// 按日期创建日志文件
	date := entry.Timestamp.Format("2006-01-02")
	filename := fmt.Sprintf("task_%s.log", date)
	filepath := filepath.Join(l.logDir, filename)

	file, err := os.OpenFile(filepath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return err
	}
	defer file.Close()

	// 写入日志行
	logLine := fmt.Sprintf("[%s] [%s] [Task:%d] %s\n",
		entry.Timestamp.Format("15:04:05"),
		entry.Level,
		entry.TaskID,
		entry.Message)

	_, err = file.WriteString(logLine)
	return err
}

// Debug 记录调试日志
func (l *Logger) Debug(taskID uint, message string) {
	l.log(LogLevelDebug, taskID, "", message)
}

// Info 记录信息日志
func (l *Logger) Info(taskID uint, message string) {
	l.log(LogLevelInfo, taskID, "", message)
}

// Warn 记录警告日志
func (l *Logger) Warn(taskID uint, message string) {
	l.log(LogLevelWarn, taskID, "", message)
}

// Error 记录错误日志
func (l *Logger) Error(taskID uint, message string) {
	l.log(LogLevelError, taskID, "", message)
}

// LogWithTask 记录任务相关日志
func (l *Logger) LogWithTask(level LogLevel, task *Task, message string) {
	l.log(level, task.ID, task.Type, message)
}

// GetEntries 获取日志条目
func (l *Logger) GetEntries(taskID uint, limit int) []LogEntry {
	l.mu.Lock()
	defer l.mu.Unlock()

	if taskID == 0 {
		// 返回所有日志
		if limit > 0 && len(l.entries) > limit {
			return l.entries[len(l.entries)-limit:]
		}
		return l.entries
	}

	// 过滤指定任务的日志
	var result []LogEntry
	for i := len(l.entries) - 1; i >= 0; i-- {
		if l.entries[i].TaskID == taskID {
			result = append(result, l.entries[i])
			if limit > 0 && len(result) >= limit {
				break
			}
		}
	}

	// 反转结果（从旧到新）
	for i, j := 0, len(result)-1; i < j; i, j = i+1, j-1 {
		result[i], result[j] = result[j], result[i]
	}

	return result
}

// Clear 清空日志
func (l *Logger) Clear(taskID uint) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if taskID == 0 {
		l.entries = make([]LogEntry, 0, l.maxSize)
		return
	}

	// 过滤删除指定任务的日志
	var newEntries []LogEntry
	for _, entry := range l.entries {
		if entry.TaskID != taskID {
			newEntries = append(newEntries, entry)
		}
	}
	l.entries = newEntries
}

// Close 关闭日志记录器
func (l *Logger) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.file != nil {
		return l.file.Close()
	}
	return nil
}

// CleanOldLogs 清理旧日志文件
func (l *Logger) CleanOldLogs(days int) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	cutoff := time.Now().AddDate(0, 0, -days)

	entries, err := os.ReadDir(l.logDir)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		info, err := entry.Info()
		if err != nil {
			continue
		}

		if info.ModTime().Before(cutoff) {
			filepath := filepath.Join(l.logDir, entry.Name())
			os.Remove(filepath)
		}
	}

	return nil
}

// GetLogFile 获取任务日志文件路径
func (l *Logger) GetLogFile(taskID uint) (string, error) {
	date := time.Now().Format("2006-01-02")
	filename := fmt.Sprintf("task_%s.log", date)
	filepath := filepath.Join(l.logDir, filename)

	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		return "", fmt.Errorf("日志文件不存在")
	}

	return filepath, nil
}
