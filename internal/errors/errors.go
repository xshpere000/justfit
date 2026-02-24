// Package errors 提供统一的错误处理
package errors

import (
	"fmt"
	"strings"
)

// Error 应用错误
type Error struct {
	Code    string // 错误码
	Message string // 错误消息
	Cause   error  // 原始错误
}

// Error 实现 error 接口
func (e *Error) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.Cause)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

// Unwrap 实现 errors.Unwrap 接口
func (e *Error) Unwrap() error {
	return e.Cause
}

// joinErrors 连接多个错误
func joinErrors(errs ...error) error {
	var result []string
	for _, err := range errs {
		if err != nil {
			result = append(result, err.Error())
		}
	}
	if len(result) == 0 {
		return nil
	}
	return New(CodeInternalError, strings.Join(result, "; "))
}

// New 创建新错误
func New(code, message string) *Error {
	return &Error{
		Code:    code,
		Message: message,
	}
}

// Wrap 包装错误
func Wrap(code, message string, cause error) *Error {
	return &Error{
		Code:    code,
		Message: message,
		Cause:   cause,
	}
}

// Is 判断错误是否匹配
func (e *Error) Is(target error) bool {
	if t, ok := target.(*Error); ok {
		return e.Code == t.Code
	}
	return false
}

// ==================== 预定义错误码 ====================

const (
	// 通用错误 (1xxx)
	CodeInternalError   = "INTERNAL_ERROR"
	CodeInvalidInput    = "INVALID_INPUT"
	CodeInvalidConfig   = "INVALID_CONFIG"
	CodeNotFound        = "NOT_FOUND"
	CodeAlreadyExists   = "ALREADY_EXISTS"
	CodeTimeout         = "TIMEOUT"
	CodeCancelled       = "CANCELLED"

	// 连接错误 (2xxx)
	CodeConnectionNotFound   = "CONN_NOT_FOUND"
	CodeConnectionFailed     = "CONN_FAILED"
	CodeConnectionTimeout    = "CONN_TIMEOUT"
	CodeInvalidCredentials   = "INVALID_CREDENTIALS"
	CodeConnectionRefused    = "CONN_REFUSED"

	// 任务错误 (3xxx)
	CodeTaskNotFound       = "TASK_NOT_FOUND"
	CodeTaskFailed         = "TASK_FAILED"
	CodeTaskCancelled      = "TASK_CANCELLED"
	CodeTaskTimeout        = "TASK_TIMEOUT"
	CodeInvalidTaskConfig  = "INVALID_TASK_CONFIG"

	// 数据错误 (4xxx)
	CodeDataNotFound       = "DATA_NOT_FOUND"
	CodeDataInvalid        = "DATA_INVALID"
	CodeDataCorrupted      = "DATA_CORRUPTED"
	CodeDatabaseError      = "DATABASE_ERROR"

	// 分析错误 (5xxx)
	CodeAnalysisFailed     = "ANALYSIS_FAILED"
	CodeInvalidAnalysisConfig = "INVALID_ANALYSIS_CONFIG"
	CodeInsufficientData   = "INSUFFICIENT_DATA"

	// 采集错误 (6xxx)
	CodeCollectionFailed   = "COLLECTION_FAILED"
	CodePlatformNotSupported = "PLATFORM_NOT_SUPPORTED"
)

// ==================== 预定义错误实例 ====================

var (
	// 通用错误
	ErrInternal      = New(CodeInternalError, "内部错误")
	ErrInternalError = New(CodeInternalError, "内部错误")
	ErrInvalidInput  = New(CodeInvalidInput, "输入参数无效")
	ErrInvalidConfig = New(CodeInvalidConfig, "配置无效")
	ErrNotFound      = New(CodeNotFound, "资源不存在")
	ErrAlreadyExists = New(CodeAlreadyExists, "资源已存在")
	ErrTimeout       = New(CodeTimeout, "操作超时")
	ErrCancelled     = New(CodeCancelled, "操作已取消")

	// 连接错误
	ErrConnectionNotFound = New(CodeConnectionNotFound, "连接不存在")
	ErrConnectionFailed   = New(CodeConnectionFailed, "连接失败")
	ErrConnectionTimeout  = New(CodeConnectionTimeout, "连接超时")
	ErrInvalidCredentials = New(CodeInvalidCredentials, "凭据无效")
	ErrConnectionTestFailed = New(CodeConnectionFailed, "连接测试失败")

	// 任务错误
	ErrTaskNotFound      = New(CodeTaskNotFound, "任务不存在")
	ErrTaskFailed        = New(CodeTaskFailed, "任务执行失败")
	ErrTaskCancelled     = New(CodeTaskCancelled, "任务已取消")
	ErrTaskTimeout       = New(CodeTaskTimeout, "任务执行超时")

	// 数据错误
	ErrDataNotFound  = New(CodeDataNotFound, "数据不存在")
	ErrDataInvalid   = New(CodeDataInvalid, "数据无效")
	ErrDatabaseError = New(CodeDatabaseError, "数据库错误")

	// 分析错误
	ErrAnalysisFailed   = New(CodeAnalysisFailed, "分析失败")
	ErrInsufficientData = New(CodeInsufficientData, "数据不足")

	// 资源错误
	ErrVMNotFound     = New(CodeDataNotFound, "虚拟机不存在")
	ErrHostNotFound   = New(CodeDataNotFound, "主机不存在")
	ErrClusterNotFound = New(CodeDataNotFound, "集群不存在")
)

// ==================== 辅助函数 ====================

// WithCause 添加原始错误
func (e *Error) WithCause(cause error) *Error {
	return &Error{
		Code:    e.Code,
		Message: e.Message,
		Cause:   cause,
	}
}

// Wrap 包装错误并返回新的错误实例
func (e *Error) Wrap(cause error, message string) *Error {
	return &Error{
		Code:    e.Code,
		Message: message,
		Cause:   cause,
	}
}

// WithMessage 修改错误消息
func (e *Error) WithMessage(message string) *Error {
	return &Error{
		Code:    e.Code,
		Message: message,
		Cause:   e.Cause,
	}
}

// IsNotFound 判断是否为"不存在"错误
func IsNotFound(err error) bool {
	return matchesCode(err, CodeNotFound) ||
		matchesCode(err, CodeConnectionNotFound) ||
		matchesCode(err, CodeTaskNotFound) ||
		matchesCode(err, CodeDataNotFound)
}

// IsTimeout 判断是否为超时错误
func IsTimeout(err error) bool {
	return matchesCode(err, CodeTimeout) ||
		matchesCode(err, CodeConnectionTimeout) ||
		matchesCode(err, CodeTaskTimeout)
}

// IsCancelled 判断是否为取消错误
func IsCancelled(err error) bool {
	return matchesCode(err, CodeCancelled) ||
		matchesCode(err, CodeTaskCancelled)
}

// GetCode 获取错误码
func GetCode(err error) string {
	if e, ok := err.(*Error); ok {
		return e.Code
	}
	return CodeInternalError
}

// matchesCode 匹配错误码
func matchesCode(err error, code string) bool {
	if e, ok := err.(*Error); ok {
		return e.Code == code
	}
	return false
}

// Wrapf 包装错误（格式化消息）
func Wrapf(code string, cause error, format string, args ...interface{}) *Error {
	return &Error{
		Code:    code,
		Message: fmt.Sprintf(format, args...),
		Cause:   cause,
	}
}

// FormatError 格式化错误为字符串
func FormatError(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}

// FormatErrorChain 格式化错误链
func FormatErrorChain(err error) string {
	if err == nil {
		return ""
	}

	result := err.Error()
	for {
		// 使用自定义的 unwrap 函数
		unwrapped := unwrapError(err)
		if unwrapped == nil {
			break
		}
		result += "\n  caused by: " + unwrapped.Error()
		err = unwrapped
	}
	return result
}

// unwrapError 解包错误
func unwrapError(err error) error {
	if wrapper, ok := err.(interface{ Unwrap() error }); ok {
		return wrapper.Unwrap()
	}
	return nil
}
