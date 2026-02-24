// Package errors_test 错误处理测试
package errors_test

import (
	stderrors "errors"
	"testing"

	apperrors "justfit/internal/errors"
)

// TestError_Error 测试错误字符串
func TestError_Error(t *testing.T) {
	err := apperrors.New("TEST_CODE", "test message")
	if got := err.Error(); got != "TEST_CODE: test message" {
		t.Errorf("Error() = %v, want 'TEST_CODE: test message'", got)
	}
}

// TestError_Wrap 测试错误包装
func TestError_Wrap(t *testing.T) {
	original := apperrors.New("ORIGINAL", "original error")
	wrapped := apperrors.Wrap("WRAPPED", "wrapped message", original)

	expected := "WRAPPED: wrapped message: ORIGINAL: original error"
	if got := wrapped.Error(); got != expected {
		t.Errorf("Wrapped Error() = %v, want %v", got, expected)
	}
}

// TestError_Unwrap 测试错误解包
func TestError_Unwrap(t *testing.T) {
	original := apperrors.New("ORIGINAL", "original error")
	wrapped := apperrors.Wrap("WRAPPED", "wrapped message", original)

	if wrapped.Unwrap() != original {
		t.Error("Unwrap() 应返回原始错误")
	}
}

// TestError_Is 测试错误匹配
func TestError_Is(t *testing.T) {
	err1 := apperrors.New("TEST_CODE", "test")
	err2 := apperrors.New("TEST_CODE", "another")
	err3 := apperrors.New("OTHER_CODE", "test")

	if !err1.Is(err2) {
		t.Error("相同错误码应该匹配")
	}

	if err1.Is(err3) {
		t.Error("不同错误码不应该匹配")
	}
}

// TestPredefinedErrors 测试预定义错误
func TestPredefinedErrors(t *testing.T) {
	tests := []struct {
		name   string
		err    *apperrors.Error
		code   string
		msg    string
	}{
		{"ErrInternal", apperrors.ErrInternal, "INTERNAL_ERROR", "内部错误"},
		{"ErrInvalidInput", apperrors.ErrInvalidInput, "INVALID_INPUT", "输入参数无效"},
		{"ErrNotFound", apperrors.ErrNotFound, "NOT_FOUND", "资源不存在"},
		{"ErrConnectionNotFound", apperrors.ErrConnectionNotFound, "CONN_NOT_FOUND", "连接不存在"},
		{"ErrTaskNotFound", apperrors.ErrTaskNotFound, "TASK_NOT_FOUND", "任务不存在"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.err.Code != tt.code {
				t.Errorf("Code = %v, want %v", tt.err.Code, tt.code)
			}
			if tt.err.Message != tt.msg {
				t.Errorf("Message = %v, want %v", tt.err.Message, tt.msg)
			}
		})
	}
}

// TestWithCause 测试添加原因
func TestWithCause(t *testing.T) {
	original := apperrors.New("ORIGINAL", "original")
	err := apperrors.ErrInvalidInput.WithCause(original)

	if err.Unwrap() != original {
		t.Error("WithCause 应该设置原始错误")
	}
	if err.Code != apperrors.ErrInvalidInput.Code {
		t.Error("WithCause 应该保留错误码")
	}
}

// TestWithMessage 测试修改消息
func TestWithMessage(t *testing.T) {
	err := apperrors.ErrInvalidInput.WithMessage("custom message")

	if err.Message != "custom message" {
		t.Errorf("Message = %v, want 'custom message'", err.Message)
	}
	if err.Code != apperrors.ErrInvalidInput.Code {
		t.Error("WithMessage 应该保留错误码")
	}
}

// TestIsNotFound 测试 NotFound 判断
func TestIsNotFound(t *testing.T) {
	tests := []struct {
		name     string
		err      error
		expected bool
	}{
		{"ErrNotFound", apperrors.ErrNotFound, true},
		{"ErrConnectionNotFound", apperrors.ErrConnectionNotFound, true},
		{"ErrTaskNotFound", apperrors.ErrTaskNotFound, true},
		{"ErrDataNotFound", apperrors.ErrDataNotFound, true},
		{"ErrInternal", apperrors.ErrInternal, false},
		{"标准错误", stderrors.New("std error"), false},
		{"nil", nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := apperrors.IsNotFound(tt.err); got != tt.expected {
				t.Errorf("IsNotFound(%v) = %v, want %v", tt.err, got, tt.expected)
			}
		})
	}
}

// TestIsTimeout 测试 Timeout 判断
func TestIsTimeout(t *testing.T) {
	tests := []struct {
		name     string
		err      error
		expected bool
	}{
		{"ErrTimeout", apperrors.ErrTimeout, true},
		{"ErrConnectionTimeout", apperrors.ErrConnectionTimeout, true},
		{"ErrTaskTimeout", apperrors.ErrTaskTimeout, true},
		{"ErrInternal", apperrors.ErrInternal, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := apperrors.IsTimeout(tt.err); got != tt.expected {
				t.Errorf("IsTimeout(%v) = %v, want %v", tt.err, got, tt.expected)
			}
		})
	}
}

// TestGetCode 测试获取错误码
func TestGetCode(t *testing.T) {
	tests := []struct {
		name     string
		err      error
		expected string
	}{
		{"应用错误", apperrors.ErrInvalidInput, "INVALID_INPUT"},
		{"标准错误", stderrors.New("std"), "INTERNAL_ERROR"},
		{"nil", nil, "INTERNAL_ERROR"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := apperrors.GetCode(tt.err); got != tt.expected {
				t.Errorf("GetCode() = %v, want %v", got, tt.expected)
			}
		})
	}
}

// TestWrapf 测试格式化包装
func TestWrapf(t *testing.T) {
	original := apperrors.New("ORIGINAL", "original")
	wrapped := apperrors.Wrapf("WRAPPED", original, "failed to process %d items", 42)

	expectedMsg := "failed to process 42 items"
	if wrapped.Message != expectedMsg {
		t.Errorf("Message = %v, want %v", wrapped.Message, expectedMsg)
	}
}

// TestFormatError 测试格式化错误
func TestFormatError(t *testing.T) {
	err := apperrors.ErrInvalidInput
	formatted := apperrors.FormatError(err)

	expected := "INVALID_INPUT: 输入参数无效"
	if formatted != expected {
		t.Errorf("FormatError() = %v, want %v", formatted, expected)
	}

	// nil 错误
	if apperrors.FormatError(nil) != "" {
		t.Error("nil 错误应返回空字符串")
	}
}

// TestFormatErrorChain 测试格式化错误链
func TestFormatErrorChain(t *testing.T) {
	original := apperrors.New("ORIGINAL", "original error")
	middle := apperrors.Wrap("MIDDLE", "middle error", original)
	top := apperrors.Wrap("TOP", "top error", middle)

	chain := apperrors.FormatErrorChain(top)

	lines := splitLines(chain)
	if len(lines) < 3 {
		t.Errorf("错误链应该至少有3行，得到 %d", len(lines))
	}

	if !contains(lines[0], "TOP") {
		t.Errorf("第一行应包含 TOP，得到 %v", lines[0])
	}
}

// TestErrors_Is 与标准库兼容
func TestErrors_Is(t *testing.T) {
	err := apperrors.ErrNotFound

	if !stderrors.Is(err, apperrors.ErrNotFound) {
		t.Error("标准 errors.Is 应该匹配")
	}

	if stderrors.Is(err, apperrors.ErrInternal) {
		t.Error("不应该匹配不同错误")
	}
}

func splitLines(s string) []string {
	lines := make([]string, 0)
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			lines = append(lines, s[start:i])
			start = i + 1
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && containsIn(s, substr))
}

func containsIn(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
