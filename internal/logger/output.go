// Package logger 提供结构化日志功能
package logger

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
)

// Output 输出适配器接口
type Output interface {
	Write(entry *Entry) error
	Sync() error
	Close() error
}

// Format 日志格式
type Format int

const (
	FormatJSON Format = iota
	FormatText
)

// ConsoleOutput 控制台输出
type ConsoleOutput struct {
	mu       sync.Mutex
	writer   io.Writer
	format   Format
	useColor bool
}

// NewConsoleOutput 创建控制台输出
func NewConsoleOutput(format Format) *ConsoleOutput {
	return &ConsoleOutput{
		writer:   os.Stdout,
		format:   format,
		useColor: format == FormatText,
	}
}

// SetWriter 设置输出写入器
func (o *ConsoleOutput) SetWriter(w io.Writer) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.writer = w
}

// Write 写入日志
func (o *ConsoleOutput) Write(entry *Entry) error {
	o.mu.Lock()
	defer o.mu.Unlock()

	var data []byte
	switch o.format {
	case FormatJSON:
		data = o.formatJSON(entry)
	case FormatText:
		data = o.formatText(entry)
	}

	_, err := o.writer.Write(append(data, '\n'))
	return err
}

// Sync 同步
func (o *ConsoleOutput) Sync() error {
	if f, ok := o.writer.(interface{ Sync() error }); ok {
		return f.Sync()
	}
	return nil
}

// Close 关闭
func (o *ConsoleOutput) Close() error {
	return nil
}

func (o *ConsoleOutput) formatJSON(entry *Entry) []byte {
	data, err := json.Marshal(entry)
	if err != nil {
		return []byte(fmt.Sprintf(`{"error": "无法序列化日志: %v"}`, err))
	}
	return data
}

func (o *ConsoleOutput) formatText(entry *Entry) []byte {
	var colorReset string
	if o.useColor {
		colorReset = ResetColor()
	}

	// 时间戳
	timestamp := entry.Timestamp.Format("15:04:05.000")

	// 级别（带颜色）
	levelStr := entry.Level.String()
	if o.useColor {
		levelStr = entry.Level.Color() + levelStr + colorReset
	}

	// 文件位置
	file := ""
	if entry.File != "" {
		file = fmt.Sprintf(" [%s:%d]", filepath.Base(entry.File), entry.Line)
	}

	// 构建基础消息
	msg := fmt.Sprintf("%s [%s]%s %s", timestamp, levelStr, file, entry.Message)

	// 添加字段
	if len(entry.Fields) > 0 {
		msg += " "
		for k, v := range entry.Fields {
			msg += fmt.Sprintf("%s=%v ", k, v)
		}
	}

	// 添加错误
	if entry.Error != "" {
		msg += " error=" + entry.Error
	}

	return []byte(msg)
}

// FileOutput 文件输出
type FileOutput struct {
	mu   sync.Mutex
	file *os.File
}

// NewFileOutput 创建文件输出
func NewFileOutput(filename string) (*FileOutput, error) {
	// 确保目录存在
	dir := filepath.Dir(filename)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("创建日志目录失败: %w", err)
	}

	file, err := os.OpenFile(filename, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, fmt.Errorf("打开日志文件失败: %w", err)
	}

	return &FileOutput{file: file}, nil
}

// Write 写入日志
func (o *FileOutput) Write(entry *Entry) error {
	o.mu.Lock()
	defer o.mu.Unlock()

	data, err := json.Marshal(entry)
	if err != nil {
		return err
	}

	_, err = o.file.Write(append(data, '\n'))
	return err
}

// Sync 同步
func (o *FileOutput) Sync() error {
	o.mu.Lock()
	defer o.mu.Unlock()

	if o.file != nil {
		return o.file.Sync()
	}
	return nil
}

// Close 关闭
func (o *FileOutput) Close() error {
	o.mu.Lock()
	defer o.mu.Unlock()

	if o.file != nil {
		return o.file.Close()
	}
	return nil
}

// MultiOutput 多路输出
type MultiOutput struct {
	outputs []Output
	closed  atomic.Bool
}

// NewMultiOutput 创建多路输出
func NewMultiOutput(outputs ...Output) *MultiOutput {
	return &MultiOutput{outputs: outputs}
}

// Write 写入日志
func (o *MultiOutput) Write(entry *Entry) error {
	if o.closed.Load() {
		return nil
	}

	var firstErr error
	for _, output := range o.outputs {
		if err := output.Write(entry); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// Sync 同步
func (o *MultiOutput) Sync() error {
	var firstErr error
	for _, output := range o.outputs {
		if err := output.Sync(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// Close 关闭
func (o *MultiOutput) Close() error {
	if !o.closed.CompareAndSwap(false, true) {
		return nil
	}

	var firstErr error
	for _, output := range o.outputs {
		if err := output.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// AddOutput 添加输出器
func (o *MultiOutput) AddOutput(output Output) {
	o.outputs = append(o.outputs, output)
}

// NullOutput 空输出（用于禁用日志）
type NullOutput struct{}

// NewNullOutput 创建空输出
func NewNullOutput() *NullOutput {
	return &NullOutput{}
}

func (o *NullOutput) Write(entry *Entry) error { return nil }
func (o *NullOutput) Sync() error              { return nil }
func (o *NullOutput) Close() error             { return nil }
