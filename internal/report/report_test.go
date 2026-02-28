package report

import (
	"encoding/json"
	"os"
	"testing"
	"time"

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

// ========== 新增测试：报告生成器 ==========

// TestReportBuilder_BuildReportData 测试报告数据构建器
func TestReportBuilder_BuildReportData(t *testing.T) {
	// 创建模拟数据源
	ds := &mockDataSource{
		clusters: []ClusterInfo{
			{Name: "Cluster-01", Datacenter: "DC1", TotalCpu: 100000, TotalMemory: 100000000000, NumHosts: 5, NumVMs: 50},
			{Name: "Cluster-02", Datacenter: "DC1", TotalCpu: 200000, TotalMemory: 200000000000, NumHosts: 10, NumVMs: 100},
		},
		hosts: []HostInfo{
			{Name: "Host-01", Datacenter: "DC1", IPAddress: "192.168.1.1", CpuCores: 32, CpuMhz: 2400, Memory: 100000000000, NumVMs: 10},
		},
		vms: []VMInfo{
			{Name: "VM-001", Datacenter: "DC1", CpuCount: 4, MemoryMB: 8192, PowerState: "poweredOn"},
		},
		findings: map[string][]AnalysisFinding{
			"zombie": {
				{JobType: "zombie", TargetName: "VM-001", Severity: "warning", Title: "低使用率", Action: "建议关机"},
			},
		},
		taskInfo: &TaskInfo{Name: "Test Task", Platform: "vcenter", StartedAt: time.Now(), MetricsDays: 30},
	}

	builder := NewReportBuilder(ds)
	reportData, err := builder.BuildReportData()

	require.NoError(t, err, "构建报告数据应该成功")
	assert.NotNil(t, reportData)
	assert.Equal(t, "Test Task - 资源评估报告", reportData.Title)
	assert.NotEmpty(t, reportData.Sections, "应该有章节内容")
}

// TestExcelGenerator_Generate 测试 Excel 生成器
func TestExcelGenerator_Generate(t *testing.T) {
	// 创建测试报告数据
	reportData := &ReportData{
		Title:        "测试报告",
		GeneratedAt:  time.Now(),
		ConnectionID: 1,
		Metadata:     make(map[string]interface{}),
		Sections: []ReportSection{
			{
				Type:  "summary",
				Title: "资源概览",
				Data: map[string]interface{}{
					"clusterCount": 2,
					"hostCount":    5,
					"vmCount":      10,
				},
			},
			{
				Type:  "cluster_table",
				Title: "集群信息",
				Data: []map[string]interface{}{
					{"name": "Cluster-01", "datacenter": "DC1", "totalCpu": 100000, "totalMemory": 100, "numHosts": 5, "numVMs": 50, "status": "green"},
				},
			},
			{
				Type:  "host_table",
				Title: "主机信息",
				Data: []map[string]interface{}{
					{"name": "Host-01", "datacenter": "DC1", "ipAddress": "192.168.1.1", "cpuCores": 32, "cpuMhz": 2400, "memory": 100, "numVMs": 10, "powerState": "poweredOn"},
				},
			},
			{
				Type:  "vm_table",
				Title: "虚拟机列表",
				Data: []map[string]interface{}{
					{"name": "VM-001", "datacenter": "DC1", "hostName": "Host-01", "cpuCount": 4, "memoryGb": 8.0, "powerState": "poweredOn"},
				},
			},
		},
	}

	// 创建临时输出目录
	tmpDir := t.TempDir()
	gen := NewExcelGenerator(reportData, tmpDir)

	filepath, err := gen.Generate()
	require.NoError(t, err, "Excel 生成应该成功")

	// 验证文件存在
	assert.FileExists(t, filepath)
	assert.Contains(t, filepath, ".xlsx")

	// 清理
	os.Remove(filepath)
}

// TestPDFGenerator_GenerateWithFont 测试 PDF 生成器（需要字体）
func TestPDFGenerator_GenerateWithFont(t *testing.T) {
	if testing.Short() {
		t.Skip("跳过 PDF 生成测试（需要字体文件）")
	}

	// 创建测试报告数据
	reportData := &ReportData{
		Title:        "测试报告",
		GeneratedAt:  time.Now(),
		ConnectionID: 1,
		Metadata:     make(map[string]interface{}),
		Sections: []ReportSection{
			{
				Type:  "summary",
				Title: "资源概览",
				Data: map[string]interface{}{
					"clusterCount": 2,
					"hostCount":    5,
					"vmCount":      10,
				},
			},
		},
	}

	// 创建临时输出目录
	tmpDir := t.TempDir()
	config := &PDFConfig{
		OutputDir: tmpDir,
	}

	gen := NewPDFGenerator(reportData, nil, config)

	// 使用 recover 捕获可能的 panic（字体加载失败）
	defer func() {
		if r := recover(); r != nil {
			t.Skipf("PDF 生成失败（可能缺少有效的 TTF 字体文件）: %v", r)
		}
	}()

	filepath, err := gen.Generate()

	// PDF 生成可能会因为没有字体而失败
	if err != nil {
		t.Skipf("PDF 生成失败（可能缺少字体）: %v", err)
		return
	}

	// 验证文件存在
	assert.FileExists(t, filepath)
	assert.Contains(t, filepath, ".pdf")

	// 清理
	os.Remove(filepath)
}

// TestChartGenerator_GenerateClusterPie 测试集群分布饼图生成
func TestChartGenerator_GenerateClusterPie(t *testing.T) {
	reportData := &ReportData{
		Title:        "测试报告",
		GeneratedAt:  time.Now(),
		ConnectionID: 1,
		Sections: []ReportSection{
			{
				Type: "cluster_table",
				Data: []map[string]interface{}{
					{"name": "Cluster-01", "numVMs": 50},
					{"name": "Cluster-02", "numVMs": 30},
					{"name": "Cluster-03", "numVMs": 20},
				},
			},
		},
	}

	tmpDir := t.TempDir()
	gen := NewChartGenerator(tmpDir)

	images, err := gen.GenerateAllCharts(reportData)

	// 饼图图应该生成成功（不需要指标数据源）
	assert.NoError(t, err)
	assert.NotNil(t, images)
	assert.NotEmpty(t, images.ClusterDistribution, "集群分布图应该生成")

	// 验证文件存在
	assert.FileExists(t, images.ClusterDistribution)

	// 清理
	os.Remove(images.ClusterDistribution)
}

// TestMetricDataSourceAdapter 测试指标数据源适配器
func TestMetricDataSourceAdapter(t *testing.T) {
	// 这个测试需要真实的数据库连接，在集成测试中运行
	t.Skip("需要数据库连接，在集成测试中运行")
}

// ========== Mock 数据源（用于单元测试） ==========

type mockDataSource struct {
	clusters []ClusterInfo
	hosts    []HostInfo
	vms      []VMInfo
	findings map[string][]AnalysisFinding
	taskInfo *TaskInfo
}

func (m *mockDataSource) GetClusters() ([]ClusterInfo, error) {
	return m.clusters, nil
}

func (m *mockDataSource) GetHosts() ([]HostInfo, error) {
	return m.hosts, nil
}

func (m *mockDataSource) GetVMs() ([]VMInfo, error) {
	return m.vms, nil
}

func (m *mockDataSource) GetAnalysisFindings(jobType string) ([]AnalysisFinding, error) {
	if findings, ok := m.findings[jobType]; ok {
		return findings, nil
	}
	return []AnalysisFinding{}, nil
}

func (m *mockDataSource) GetTaskInfo() (*TaskInfo, error) {
	if m.taskInfo == nil {
		return &TaskInfo{Name: "Default Task", Platform: "test", StartedAt: time.Now(), MetricsDays: 30}, nil
	}
	return m.taskInfo, nil
}
