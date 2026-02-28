// Package analyzer 提供分析功能的单元测试
package analyzer

import (
	"testing"

	"justfit/internal/storage"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// setupTestDB 创建测试数据库
func setupTestDB(t *testing.T) *gorm.DB {
	db, err := gorm.Open(sqlite.Open("file::memory:?cache=shared_mode"), &gorm.Config{})
	require.NoError(t, err)

	// 自动迁移表结构
	err = db.AutoMigrate(&storage.Cluster{}, &storage.Host{}, &storage.VM{}, &storage.VMMetric{})
	require.NoError(t, err)

	return db
}

func TestAverageMetrics(t *testing.T) {
	metrics := []storage.VMMetric{
		{Value: 10.0},
		{Value: 20.0},
		{Value: 30.0},
	}

	result := averageMetrics(metrics)
	assert.Equal(t, 20.0, result)
}

func TestAverageMetrics_Empty(t *testing.T) {
	result := averageMetrics([]storage.VMMetric{})
	assert.Equal(t, 0.0, result)
}

func TestPercentile(t *testing.T) {
	tests := []struct {
		name     string
		values   []float64
		p        float64
		expected float64
	}{
		{
			name:     "P50 of 1,2,3",
			values:   []float64{1, 2, 3},
			p:        50,
			expected: 2,
		},
		{
			name:     "P95 of sorted values",
			values:   []float64{1, 2, 3, 4, 5, 6, 7, 8, 9, 10},
			p:        95,
			expected: 9.55,
		},
		{
			name:     "P100",
			values:   []float64{1, 2, 3},
			p:        100,
			expected: 3,
		},
		{
			name:     "P0",
			values:   []float64{1, 2, 3},
			p:        0,
			expected: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := percentile(tt.values, tt.p)
			assert.InDelta(t, tt.expected, result, 0.01)
		})
	}
}

func TestPercentile_Empty(t *testing.T) {
	result := percentile([]float64{}, 50)
	assert.Equal(t, 0.0, result)
}

func TestStdDev(t *testing.T) {
	tests := []struct {
		name     string
		values   []float64
		expected float64
	}{
		{
			name:     "相同值",
			values:   []float64{5, 5, 5, 5},
			expected: 0,
		},
		{
			name:     "不同值",
			values:   []float64{2, 4, 4, 4, 5, 5, 7, 9},
			expected: 2.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := stdDev(tt.values)
			assert.InDelta(t, tt.expected, result, 0.01)
		})
	}
}

func TestStdDevEmpty(t *testing.T) {
	result := stdDev([]float64{})
	assert.Equal(t, 0.0, result)
}

func TestMax(t *testing.T) {
	assert.Equal(t, 0.0, max([]float64{}))
	assert.Equal(t, 10.0, max([]float64{1, 5, 10, 2}))
}

func TestNormalizeCPU(t *testing.T) {
	tests := []struct {
		input    int32
		expected int32
	}{
		{0, 1},
		{1, 1},
		{2, 2},
		{3, 4},
		{5, 8},
		{9, 12},  // 修正：实际标准值是 12
		{17, 24}, // 修正：实际标准值是 24
		{129, 128},
		{130, 128},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := normalizeCPU(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestNormalizeMemory(t *testing.T) {
	tests := []struct {
		input    int32
		expected int32
	}{
		{0, 512},
		{100, 512},
		{512, 512},
		{513, 1024},
		{1024, 1024},
		{1025, 1536},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := normalizeMemory(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestCalculateZombieConfidence(t *testing.T) {
	tests := []struct {
		name        string
		cpu         float64
		memory      float64
		diskIO      float64
		network     float64
		lowDays     int
		totalDays   int
		minExpected float64
	}{
		{
			name:        "完全僵尸机",
			cpu:         0,
			memory:      0,
			diskIO:      0,
			network:     0,
			lowDays:     14,
			totalDays:   14,
			minExpected: 90,
		},
		{
			name:        "中等僵尸机",
			cpu:         3,
			memory:      5,
			diskIO:      5,
			network:     2,
			lowDays:     10,
			totalDays:   14,
			minExpected: 60,
		},
		{
			name:        "非僵尸机",
			cpu:         50,
			memory:      60,
			diskIO:      80,
			network:     90,
			lowDays:     0,
			totalDays:   14,
			minExpected: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := calculateZombieConfidence(tt.cpu, tt.memory, tt.diskIO, tt.network, tt.lowDays, tt.totalDays)
			assert.True(t, result >= tt.minExpected, "置信度应该大于最小期望值")
		})
	}
}
