// Package logger 提供结构化日志功能
package logger

import (
	"encoding/json"
	"fmt"
	"runtime"
	"strings"
	"time"
)

// Entry 日志条目
type Entry struct {
	// 基础字段
	Timestamp time.Time              `json:"timestamp"`
	Level     Level                  `json:"level"`
	Message   string                 `json:"message"`

	// 上下文字段
	Fields map[string]interface{} `json:"fields,omitempty"`

	// 调用信息
	File     string `json:"file,omitempty"`
	Line     int    `json:"line,omitempty"`
	Function  string `json:"function,omitempty"`

	// 追踪信息
	TraceID string `json:"traceId,omitempty"`
	SpanID  string `json:"spanId,omitempty"`

	// 错误信息
	Error string `json:"error,omitempty"`
	Stack string `json:"stack,omitempty"`
}

// String 返回日志条目的文本格式
func (e *Entry) String() string {
	var sb strings.Builder

	// 时间戳
	sb.WriteString(e.Timestamp.Format("15:04:05.000"))
	sb.WriteString(" ")

	// 级别
	sb.WriteString("[")
	sb.WriteString(e.Level.String())
	sb.WriteString("] ")

	// 消息
	sb.WriteString(e.Message)

	// 字段
	if len(e.Fields) > 0 {
		sb.WriteString(" ")
		for k, v := range e.Fields {
			sb.WriteString(k)
			sb.WriteString("=")
			sb.WriteString(fmt.Sprintf("%v", v))
			sb.WriteString(" ")
		}
	}

	return sb.String()
}

// JSON 返回日志条目的 JSON 格式
func (e *Entry) JSON() string {
	data, err := json.Marshal(e)
	if err != nil {
		return fmt.Sprintf(`{"error": "无法序列化日志: %v"}`, err)
	}
	return string(data)
}

// callerInfo 调用信息
type callerInfo struct {
	file     string
	line     int
	function string
}

// getCaller 获取调用者信息
func getCaller(skip int) callerInfo {
	pc, file, line, ok := runtime.Caller(skip + 1)
	if !ok {
		return callerInfo{}
	}

	fn := runtime.FuncForPC(pc)
	if fn == nil {
		return callerInfo{
			file: file,
			line: line,
		}
	}

	return callerInfo{
		file:     file,
		line:     line,
		function: fn.Name(),
	}
}

// getStackTrace 获取错误堆栈
func getStackTrace(err error) string {
	if err == nil {
		return ""
	}

	var sb strings.Builder
	sb.WriteString(err.Error())
	sb.WriteString("\n")

	// 获取堆栈信息
	buf := make([]byte, 4096)
	n := runtime.Stack(buf, false)
	sb.WriteString(string(buf[:n]))

	return sb.String()
}
