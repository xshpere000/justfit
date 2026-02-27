// Package logger_test 日志系统测试
package logger_test

import (
	"strings"
	"testing"
	"time"

	"justfit/internal/logger"
	memlogger "justfit/test/fixtures/logger"
)

// TestLevel_String 测试级别字符串
func TestLevel_String(t *testing.T) {
	tests := []struct {
		name     string
		level    logger.Level
		expected string
	}{
		{"DEBUG", logger.DEBUG, "DEBUG"},
		{"INFO", logger.INFO, "INFO"},
		{"WARN", logger.WARN, "WARN"},
		{"ERROR", logger.ERROR, "ERROR"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.level.String(); got != tt.expected {
				t.Errorf("Level.String() = %v, want %v", got, tt.expected)
			}
		})
	}
}

// TestParseLevel 测试级别解析
func TestParseLevel(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected logger.Level
	}{
		{"DEBUG小写", "debug", logger.DEBUG},
		{"DEBUG大写", "DEBUG", logger.DEBUG},
		{"INFO小写", "info", logger.INFO},
		{"WARN小写", "warn", logger.WARN},
		{"WARNING", "warning", logger.WARN},
		{"ERROR小写", "error", logger.ERROR},
		{"无效", "invalid", logger.INFO}, // 默认返回 INFO
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := logger.ParseLevel(tt.input); got != tt.expected {
				t.Errorf("ParseLevel(%v) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

// TestLogger_LevelFiltering 测试级别过滤
func TestLogger_LevelFiltering(t *testing.T) {
	mem := memlogger.NewMemoryOutput()
	log := logger.New(&logger.Config{
		Level:   logger.WARN,
		Outputs: []logger.Output{mem},
	})

	// DEBUG 日志不应被记录
	log.Debug("debug message")

	// INFO 日志不应被记录
	log.Info("info message")

	// WARN 日志应被记录
	log.Warn("warn message")

	// ERROR 日志应被记录
	log.Error("error message")

	entries := mem.Entries()
	if len(entries) != 2 {
		t.Fatalf("期望 2 条日志，得到 %d", len(entries))
	}

	// 验证日志级别
	if entries[0].Level != logger.WARN {
		t.Errorf("第1条日志级别错误，期望 WARN，得到 %v", entries[0].Level)
	}
	if entries[1].Level != logger.ERROR {
		t.Errorf("第2条日志级别错误，期望 ERROR，得到 %v", entries[1].Level)
	}
}

// TestLogger_WithFields 测试字段记录
func TestLogger_WithFields(t *testing.T) {
	mem := memlogger.NewMemoryOutput()
	log := logger.New(&logger.Config{
		Outputs: []logger.Output{mem},
	})

	log.Info("test message",
		logger.String("service", "collector"),
		logger.Int("count", 100),
		logger.Bool("success", true))

	entries := mem.Entries()
	if len(entries) != 1 {
		t.Fatalf("期望 1 条日志，得到 %d", len(entries))
	}

	entry := entries[0]

	// 验证字段
	if entry.Fields["service"] != "collector" {
		t.Errorf("service 字段错误，得到 %v", entry.Fields["service"])
	}
	if entry.Fields["count"] != 100 {
		t.Errorf("count 字段错误，得到 %v", entry.Fields["count"])
	}
	if entry.Fields["success"] != true {
		t.Errorf("success 字段错误，得到 %v", entry.Fields["success"])
	}
}

// TestLogger_Sublogger 测试子日志器
func TestLogger_Sublogger(t *testing.T) {
	mem := memlogger.NewMemoryOutput()
	log := logger.New(&logger.Config{
		Outputs: []logger.Output{mem},
	})

	// 创建带预设字段的子日志器
	subLog := log.With(
		logger.String("service", "collector"),
		logger.String("version", "1.0"),
	)

	subLog.Info("test message")

	entries := mem.Entries()
	if len(entries) != 1 {
		t.Fatalf("期望 1 条日志，得到 %d", len(entries))
	}

	entry := entries[0]

	// 验证预设字段存在
	if entry.Fields["service"] != "collector" {
		t.Errorf("service 字段错误，得到 %v", entry.Fields["service"])
	}
	if entry.Fields["version"] != "1.0" {
		t.Errorf("version 字段错误，得到 %v", entry.Fields["version"])
	}
}

// TestLogger_ErrorField 测试错误字段
func TestLogger_ErrorField(t *testing.T) {
	mem := memlogger.NewMemoryOutput()
	log := logger.New(&logger.Config{
		Outputs: []logger.Output{mem},
	})

	testErr := &testError{msg: "test error"}
	log.Error("operation failed", logger.Err(testErr))

	entries := mem.Entries()
	if len(entries) != 1 {
		t.Fatalf("期望 1 条日志，得到 %d", len(entries))
	}

	entry := entries[0]

	// 验证错误被记录
	if entry.Error == "" {
		t.Error("错误字段为空")
	}
	if !strings.Contains(entry.Error, "test error") {
		t.Errorf("错误消息不正确，得到 %v", entry.Error)
	}
}

// TestLogger_SetLevel 测试设置级别
func TestLogger_SetLevel(t *testing.T) {
	mem := memlogger.NewMemoryOutput()
	log := logger.New(&logger.Config{
		Level:   logger.INFO,
		Outputs: []logger.Output{mem},
	})

	// 初始级别为 INFO，DEBUG 不应记录
	log.Debug("debug message")
	if mem.Count() != 0 {
		t.Error("DEBUG 日志不应被记录")
	}

	// 修改级别为 DEBUG
	log.SetLevel(logger.DEBUG)

	log.Debug("debug message")
	if mem.Count() != 1 {
		t.Error("DEBUG 日志应被记录")
	}
}

// TestGlobalLogger 测试全局日志器
func TestGlobalLogger(t *testing.T) {
	// 重置全局日志器
	logger.Init(&logger.Config{
		Level:   logger.INFO,
		Outputs: []logger.Output{memlogger.NewMemoryOutput()},
	})

	logger.Info("global info")
	logger.Warn("global warn")
	// 无法直接验证，但不应该 panic
}

// TestFieldHelpers 测试字段辅助函数
func TestFieldHelpers(t *testing.T) {
	tests := []struct {
		name  string
		field logger.Field
		key   string
		value interface{}
	}{
		{"String", logger.String("key", "value"), "key", "value"},
		{"Int", logger.Int("count", 42), "count", 42},
		{"Int64", logger.Int64("big", 1234567890), "big", int64(1234567890)},
		{"Float64", logger.Float64("ratio", 0.5), "ratio", 0.5},
		{"Bool", logger.Bool("flag", true), "flag", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.field.Key != tt.key {
				t.Errorf("Key = %v, want %v", tt.field.Key, tt.key)
			}
			if tt.field.Value != tt.value {
				t.Errorf("Value = %v, want %v", tt.field.Value, tt.value)
			}
		})
	}
}

// TestDurationField 测试时长字段
func TestDurationField(t *testing.T) {
	d := time.Second + 500*time.Millisecond
	field := logger.Duration("duration", d)

	if field.Key != "duration" {
		t.Errorf("Key = %v, want 'duration'", field.Key)
	}
	// 值应该是格式化的字符串
	if !strings.Contains(field.Value.(string), "s") {
		t.Errorf("Duration value should contain 's', got %v", field.Value)
	}
}

// BenchmarkLogger 性能测试
func BenchmarkLogger(b *testing.B) {
	log := logger.New(&logger.Config{
		Outputs: []logger.Output{memlogger.NewMemoryOutput()},
	})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		log.Info("test message",
			logger.String("key", "value"),
			logger.Int("count", i))
	}
}

// BenchmarkLogger_WithSublogger 性能测试
func BenchmarkLogger_WithSublogger(b *testing.B) {
	log := logger.New(&logger.Config{
		Outputs: []logger.Output{memlogger.NewMemoryOutput()},
	})
	subLog := log.With(logger.String("service", "test"))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		subLog.Info("test message", logger.Int("count", i))
	}
}

// 测试用错误类型
type testError struct {
	msg string
}

func (e *testError) Error() string {
	return e.msg
}
