// Package logger 提供测试用的日志输出器
package logger

import (
	"sync"

	"justfit/internal/logger"
)

// MemoryOutput 内存输出（用于测试）
type MemoryOutput struct {
	entries []*logger.Entry
	mu      sync.Mutex
}

// NewMemoryOutput 创建内存输出
func NewMemoryOutput() *MemoryOutput {
	return &MemoryOutput{
		entries: make([]*logger.Entry, 0),
	}
}

// Write 写入日志条目
func (o *MemoryOutput) Write(entry *logger.Entry) error {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.entries = append(o.entries, entry)
	return nil
}

// Sync 同步（空实现）
func (o *MemoryOutput) Sync() error {
	return nil
}

// Close 关闭（空实现）
func (o *MemoryOutput) Close() error {
	return nil
}

// Entries 获取所有日志条目
func (o *MemoryOutput) Entries() []*logger.Entry {
	o.mu.Lock()
	defer o.mu.Unlock()

	// 返回副本，避免外部修改
	result := make([]*logger.Entry, len(o.entries))
	copy(result, o.entries)
	return result
}

// Last 获取最后一条日志
func (o *MemoryOutput) Last() *logger.Entry {
	o.mu.Lock()
	defer o.mu.Unlock()

	if len(o.entries) == 0 {
		return nil
	}
	return o.entries[len(o.entries)-1]
}

// Clear 清空日志
func (o *MemoryOutput) Clear() {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.entries = make([]*logger.Entry, 0)
}

// Count 获取日志条目数量
func (o *MemoryOutput) Count() int {
	o.mu.Lock()
	defer o.mu.Unlock()
	return len(o.entries)
}

// Contains 检查是否包含特定消息的日志
func (o *MemoryOutput) Contains(message string) bool {
	for _, e := range o.Entries() {
		if e.Message == message {
			return true
		}
	}
	return false
}

// ContainsLevel 检查是否包含特定级别的日志
func (o *MemoryOutput) ContainsLevel(level logger.Level) bool {
	for _, e := range o.Entries() {
		if e.Level == level {
			return true
		}
	}
	return false
}

// FindByLevel 按级别查找日志
func (o *MemoryOutput) FindByLevel(level logger.Level) []*logger.Entry {
	o.mu.Lock()
	defer o.mu.Unlock()

	result := make([]*logger.Entry, 0)
	for _, e := range o.entries {
		if e.Level == level {
			result = append(result, e)
		}
	}
	return result
}
