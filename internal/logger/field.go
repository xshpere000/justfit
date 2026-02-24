// Package logger 提供结构化日志功能
package logger

import "time"

// Field 日志字段
type Field struct {
	Key   string
	Value interface{}
}

// F 创建字段快捷方法
func F(key string, value interface{}) Field {
	return Field{Key: key, Value: value}
}

// String 创建字符串字段
func String(key, value string) Field {
	return Field{Key: key, Value: value}
}

// Str String 的别名
func Str(key, value string) Field {
	return String(key, value)
}

// Int 创建整数字段
func Int(key string, value int) Field {
	return Field{Key: key, Value: value}
}

// Int8 创建 int8 字段
func Int8(key string, value int8) Field {
	return Field{Key: key, Value: value}
}

// Int16 创建 int16 字段
func Int16(key string, value int16) Field {
	return Field{Key: key, Value: value}
}

// Int32 创建 int32 字段
func Int32(key string, value int32) Field {
	return Field{Key: key, Value: value}
}

// Int64 创建 int64 字段
func Int64(key string, value int64) Field {
	return Field{Key: key, Value: value}
}

// Uint 创建 uint 字段
func Uint(key string, value uint) Field {
	return Field{Key: key, Value: value}
}

// Uint32 创建 uint32 字段
func Uint32(key string, value uint32) Field {
	return Field{Key: key, Value: value}
}

// Uint64 创建 uint64 字段
func Uint64(key string, value uint64) Field {
	return Field{Key: key, Value: value}
}

// Float64 创建 float64 字段
func Float64(key string, value float64) Field {
	return Field{Key: key, Value: value}
}

// Bool 创建布尔字段
func Bool(key string, value bool) Field {
	return Field{Key: key, Value: value}
}

// Err 创建错误字段
func Err(err error) Field {
	if err == nil {
		return Field{Key: "error", Value: nil}
	}
	return Field{Key: "error", Value: err.Error()}
}

// Duration 创建时长字段
func Duration(key string, value time.Duration) Field {
	return Field{Key: key, Value: value.String()}
}

// Any 创建任意类型字段
func Any(key string, value interface{}) Field {
	return Field{Key: key, Value: value}
}
