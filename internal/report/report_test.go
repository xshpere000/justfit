package report

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewGenerator(t *testing.T) {
	g := NewGenerator(nil)
	assert.NotNil(t, g)
	assert.Equal(t, ReportTypeJSON, g.config.Type)
	assert.Equal(t, os.TempDir(), g.config.OutputDir)

	g = NewGenerator(&ReportConfig{
		Type:      ReportTypeHTML,
		OutputDir: "/tmp",
	})
	assert.NotNil(t, g)
	assert.Equal(t, ReportTypeHTML, g.config.Type)
	assert.Equal(t, "/tmp", g.config.OutputDir)
}

func TestGenerateJSON(t *testing.T) {
	tmpDir := t.TempDir()
	g := NewGenerator(&ReportConfig{
		Type:      ReportTypeJSON,
		OutputDir: tmpDir,
	})

	data := &ReportData{
		Title:        "测试报告",
		ConnectionID: 1,
		Metadata: map[string]interface{}{
			"author": "test",
		},
		Sections: []ReportSection{
			{
				Title:   "概述",
				Content: "这是一个测试报告",
				Type:    "text",
			},
		},
	}

	filepath, err := g.Generate(data)
	require.NoError(t, err)
	assert.FileExists(t, filepath)
	assert.Contains(t, filepath, tmpDir)

	// 验证文件内容
	content, err := os.ReadFile(filepath)
	require.NoError(t, err)

	var result ReportData
	err = json.Unmarshal(content, &result)
	require.NoError(t, err)

	assert.Equal(t, "测试报告", result.Title)
	assert.Equal(t, uint(1), result.ConnectionID)
	assert.NotZero(t, result.GeneratedAt)
	assert.Len(t, result.Sections, 1)
}

func TestGenerateHTML(t *testing.T) {
	tmpDir := t.TempDir()
	g := NewGenerator(&ReportConfig{
		Type:      ReportTypeHTML,
		OutputDir: tmpDir,
	})

	data := &ReportData{
		Title:        "测试 HTML 报告",
		ConnectionID: 1,
		Sections: []ReportSection{
			{
				Title:   "概述",
				Content: "这是一个测试报告",
				Type:    "text",
			},
			{
				Title: "数据汇总",
				Type:  "summary",
				Data: map[string]interface{}{
					"vmCount":     100,
					"hostCount":   10,
					"zombieVMs":   5,
					"healthScore": 85.5,
				},
			},
			{
				Title: "虚拟机列表",
				Type:  "table",
				Data: []map[string]interface{}{
					{"name": "vm-001", "cpu": 4, "memory": 8192},
					{"name": "vm-002", "cpu": 2, "memory": 4096},
				},
			},
			{
				Title: "建议列表",
				Type:  "list",
				Data: []string{
					"建议关闭僵尸虚拟机 vm-001",
					"存在超配风险的虚拟机需要优化",
					"正常运行中",
				},
			},
		},
	}

	filepath, err := g.Generate(data)
	require.NoError(t, err)
	assert.FileExists(t, filepath)

	// 验证文件内容
	content, err := os.ReadFile(filepath)
	require.NoError(t, err)

	html := string(content)
	assert.Contains(t, html, "<!DOCTYPE html>")
	assert.Contains(t, html, "测试 HTML 报告")
	assert.Contains(t, html, "虚拟机总数")
	assert.Contains(t, html, "100")
	assert.Contains(t, html, "vm-001")
	assert.Contains(t, html, "建议关闭僵尸虚拟机")
}

func TestGeneratePDF(t *testing.T) {
	g := NewGenerator(&ReportConfig{
		Type: ReportTypePDF,
	})

	data := &ReportData{
		Title: "测试 PDF 报告",
	}

	_, err := g.Generate(data)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "PDF 报告暂不支持")
}

func TestGenerateUnsupportedType(t *testing.T) {
	g := NewGenerator(&ReportConfig{
		Type: ReportType("unsupported"),
	})

	data := &ReportData{
		Title: "测试",
	}

	_, err := g.Generate(data)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "不支持的报告类型")
}

func TestSanitizeFilename(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"normal_file", "normal_file"},
		{"file with spaces", "file_with_spaces"},
		{"file/slash\\backslash", "file-slash-backslash"},
		{"file:colon*star?question\"quote<less>more|pipe", "file-colonstarquestionquotelessmorepipe"},
		{"文件名", "文件名"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			result := sanitizeFilename(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestEscapeHTML(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"normal text", "normal text"},
		{"<script>alert('xss')</script>", "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"},
		{"&lt;&gt;", "&amp;lt;&amp;gt;"},
		{"\"quotes\"", "&quot;quotes&quot;"},
		{"'apostrophe'", "&#39;apostrophe&#39;"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			result := escapeHTML(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestRenderSummary(t *testing.T) {
	g := NewGenerator(nil)

	tests := []struct {
		name     string
		data     interface{}
		contains []string
	}{
		{
			name: "基本统计数据",
			data: map[string]interface{}{
				"vmCount":   100,
				"hostCount": 10,
			},
			contains: []string{"100", "10", "虚拟机总数", "主机总数"},
		},
		{
			name: "带颜色的数据",
			data: map[string]interface{}{
				"zombieVMs":   5,
				"healthScore": 85.5,
			},
			contains: []string{"5", "86", "僵尸 VM", "danger", "success"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := g.renderSummary(tt.data)
			for _, contain := range tt.contains {
				assert.Contains(t, result, contain)
			}
		})
	}
}

func TestRenderTable(t *testing.T) {
	g := NewGenerator(nil)

	t.Run("空表格", func(t *testing.T) {
		result := g.renderTable([]map[string]interface{}{})
		assert.Contains(t, result, "无数据")
	})

	t.Run("map 切片表格", func(t *testing.T) {
		data := []map[string]interface{}{
			{"name": "vm-001", "cpu": 4, "memory": 8192},
			{"name": "vm-002", "cpu": 2, "memory": 4096},
		}
		result := g.renderTable(data)
		assert.Contains(t, result, "<table>")
		assert.Contains(t, result, "vm-001")
		assert.Contains(t, result, "vm-002")
		assert.Contains(t, result, "4")
		assert.Contains(t, result, "8192")
	})

	t.Run("单行表格", func(t *testing.T) {
		data := map[string]interface{}{
			"name": "vm-001",
			"cpu":  4,
		}
		result := g.renderTable(data)
		assert.Contains(t, result, "<table>")
		assert.Contains(t, result, "vm-001")
		assert.Contains(t, result, "4")
	})

	t.Run("无效数据", func(t *testing.T) {
		result := g.renderTable("invalid")
		assert.Contains(t, result, "无法渲染")
	})
}

func TestRenderList(t *testing.T) {
	g := NewGenerator(nil)

	t.Run("字符串列表", func(t *testing.T) {
		data := []string{"item1", "item2", "item3"}
		result := g.renderList(data)
		assert.Contains(t, result, "item1")
		assert.Contains(t, result, "item2")
		assert.Contains(t, result, "item3")
	})

	t.Run("interface 列表", func(t *testing.T) {
		data := []interface{}{"item1", 123, true}
		result := g.renderList(data)
		assert.Contains(t, result, "item1")
		assert.Contains(t, result, "123")
		assert.Contains(t, result, "true")
	})

	t.Run("带样式的列表", func(t *testing.T) {
		data := []string{
			"存在风险警告",
			"操作失败",
			"运行正常",
		}
		result := g.renderList(data)
		assert.Contains(t, result, "warning")
		assert.Contains(t, result, "danger")
		assert.Contains(t, result, "success")
	})

	t.Run("空列表", func(t *testing.T) {
		result := g.renderList([]string{})
		assert.Contains(t, result, "列表为空")
	})

	t.Run("无效数据", func(t *testing.T) {
		result := g.renderList("invalid")
		assert.Contains(t, result, "无效的列表数据")
	})
}

func TestGenerateWithRealData(t *testing.T) {
	tmpDir := t.TempDir()

	g := NewGenerator(&ReportConfig{
		Type:      ReportTypeHTML,
		OutputDir: tmpDir,
	})

	// 模拟真实的分析报告数据
	data := &ReportData{
		Title:        "JustFit 资源评估报告",
		ConnectionID: 1,
		Metadata: map[string]interface{}{
			"platform":      "vCenter",
			"analysis_days": 14,
		},
		Sections: []ReportSection{
			{
				Title:   "报告概述",
				Content: "本报告基于过去 14 天的性能数据进行分析",
				Type:    "text",
			},
			{
				Title: "资源概况",
				Type:  "summary",
				Data: map[string]interface{}{
					"vmCount":       150,
					"hostCount":     8,
					"clusterCount":  2,
					"zombieVMs":     12,
					"overallocated": 25,
					"healthScore":   78.5,
				},
			},
			{
				Title: "僵尸虚拟机列表",
				Type:  "table",
				Data: []map[string]interface{}{
					{
						"vm_name":        "test-vm-001",
						"cpu_usage":      "0.5%",
						"memory_usage":   "2.3%",
						"confidence":     "95%",
						"recommendation": "建议关闭",
					},
					{
						"vm_name":        "test-vm-002",
						"cpu_usage":      "1.2%",
						"memory_usage":   "3.1%",
						"confidence":     "88%",
						"recommendation": "建议关闭",
					},
				},
			},
			{
				Title: "优化建议",
				Type:  "list",
				Data: []string{
					"发现 12 台僵尸虚拟机，建议关闭以节省资源",
					"25 台虚拟机存在超配风险，建议进行 Right Size 优化",
					"集群 Cluster-01 的资源分配不均衡，存在热点风险",
					"建议定期运行资源评估分析",
				},
			},
		},
	}

	filepath, err := g.Generate(data)
	require.NoError(t, err)
	assert.FileExists(t, filepath)

	// 验证生成的文件
	content, err := os.ReadFile(filepath)
	require.NoError(t, err)

	html := string(content)
	assert.Contains(t, html, "JustFit 资源评估报告")
	assert.Contains(t, html, "150")
	assert.Contains(t, html, "test-vm-001")
	assert.Contains(t, html, "建议关闭")
}
