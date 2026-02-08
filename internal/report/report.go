package report

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// ReportType 报告类型
type ReportType string

const (
	ReportTypeJSON  ReportType = "json"
	ReportTypeHTML  ReportType = "html"
	ReportTypePDF   ReportType = "pdf"
	ReportTypeExcel ReportType = "xlsx"
)

// ReportConfig 报告配置
type ReportConfig struct {
	Type      ReportType `json:"type"`
	OutputDir string     `json:"output_dir"`
}

// ReportData 报告数据
type ReportData struct {
	Title       string                 `json:"title"`
	GeneratedAt time.Time              `json:"generated_at"`
	ConnectionID uint                  `json:"connection_id"`
	Metadata    map[string]interface{} `json:"metadata"`
	Sections    []ReportSection        `json:"sections"`
}

// ReportSection 报告章节
type ReportSection struct {
	Title   string      `json:"title"`
	Content string      `json:"content"`
	Data    interface{} `json:"data"`
	Type    string      `json:"type"` // text, table, chart, summary, list
}

// Generator 报告生成器
type Generator struct {
	config *ReportConfig
}

// NewGenerator 创建报告生成器
func NewGenerator(config *ReportConfig) *Generator {
	if config == nil {
		config = &ReportConfig{
			Type:      ReportTypeJSON,
			OutputDir: os.TempDir(),
		}
	}
	return &Generator{config: config}
}

// Generate 生成报告
func (g *Generator) Generate(data *ReportData) (string, error) {
	// 设置生成时间
	data.GeneratedAt = time.Now()

	switch g.config.Type {
	case ReportTypeJSON:
		return g.generateJSON(data)
	case ReportTypeHTML:
		return g.generateHTML(data)
	case ReportTypeExcel:
		excelGen := NewExcelGenerator(data, g.config.OutputDir)
		return excelGen.Generate()
	case ReportTypePDF:
		return "", fmt.Errorf("PDF 报告暂不支持")
	default:
		return "", fmt.Errorf("不支持的报告类型: %s", g.config.Type)
	}
}

// generateJSON 生成 JSON 报告
func (g *Generator) generateJSON(data *ReportData) (string, error) {
	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return "", fmt.Errorf("序列化 JSON 失败: %w", err)
	}

	// 生成文件名
	filename := fmt.Sprintf("%s_%s.json", sanitizeFilename(data.Title), time.Now().Format("20060102_150405"))
	filepath := filepath.Join(g.config.OutputDir, filename)

	// 写入文件
	if err := os.WriteFile(filepath, jsonData, 0644); err != nil {
		return "", fmt.Errorf("写入文件失败: %w", err)
	}

	return filepath, nil
}

// generateHTML 生成 HTML 报告
func (g *Generator) generateHTML(data *ReportData) (string, error) {
	html := `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>` + data.Title + `</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #409EFF;
        }
        .header h1 {
            color: #409EFF;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .meta-info {
            color: #909399;
            font-size: 14px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #303133;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #409EFF;
        }
        .section-content {
            color: #606266;
            line-height: 1.8;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #EBEEF5;
        }
        th {
            background: #F5F7FA;
            font-weight: 600;
            color: #303133;
        }
        tr:hover {
            background: #F5F7FA;
        }
        .summary-card {
            display: inline-block;
            padding: 15px 25px;
            margin: 10px;
            background: #F5F7FA;
            border-radius: 4px;
            text-align: center;
            min-width: 120px;
        }
        .summary-value {
            font-size: 28px;
            font-weight: 600;
            color: #409EFF;
        }
        .summary-label {
            font-size: 14px;
            color: #909399;
            margin-top: 5px;
        }
        .summary-card.success .summary-value { color: #67C23A; }
        .summary-card.warning .summary-value { color: #E6A23C; }
        .summary-card.danger .summary-value { color: #F56C6C; }
        .list-item {
            padding: 10px 15px;
            margin: 5px 0;
            background: #F5F7FA;
            border-radius: 4px;
            border-left: 3px solid #409EFF;
        }
        .list-item.warning { border-left-color: #E6A23C; }
        .list-item.danger { border-left-color: #F56C6C; }
        .list-item.success { border-left-color: #67C23A; }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #EBEEF5;
            color: #909399;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>` + data.Title + `</h1>
            <div class="meta-info">
                生成时间: ` + data.GeneratedAt.Format("2006-01-02 15:04:05") + `
            </div>
        </div>
`

	// 渲染各个章节
	for _, section := range data.Sections {
		html += g.renderSection(section)
	}

	html += `
        <div class="footer">
            <p>本报告由 JustFit 云平台资源评估工具自动生成</p>
        </div>
    </div>
</body>
</html>`

	// 生成文件名
	filename := fmt.Sprintf("%s_%s.html", sanitizeFilename(data.Title), time.Now().Format("20060102_150405"))
	filepath := filepath.Join(g.config.OutputDir, filename)

	// 写入文件
	if err := os.WriteFile(filepath, []byte(html), 0644); err != nil {
		return "", fmt.Errorf("写入文件失败: %w", err)
	}

	return filepath, nil
}

// renderSection 渲染章节
func (g *Generator) renderSection(section ReportSection) string {
	html := `<div class="section">
        <div class="section-title">` + section.Title + `</div>
        <div class="section-content">`

	switch section.Type {
	case "text":
		html += `<p>` + escapeHTML(section.Content) + `</p>`
	case "summary":
		html += g.renderSummary(section.Data)
	case "table":
		html += g.renderTable(section.Data)
	case "list":
		html += g.renderList(section.Data)
	default:
		html += `<p>` + escapeHTML(section.Content) + `</p>`
	}

	html += `</div></div>`
	return html
}

// renderSummary 渲染汇总数据
func (g *Generator) renderSummary(data interface{}) string {
	html := `<div style="display: flex; flex-wrap: wrap; justify-content: center;">`

	m, ok := data.(map[string]interface{})
	if !ok {
		return `<p>无效的汇总数据</p>`
	}

	// 定义标签和颜色
	labels := map[string]string{
		"total_vms":     "虚拟机总数",
		"total_hosts":   "主机总数",
		"total_clusters": "集群总数",
		"zombie_vms":    "僵尸 VM",
		"overallocated": "超配 VM",
		"underutilized": "低利用率 VM",
		"health_score":  "健康评分",
	}

	colors := map[string]string{
		"zombie_vms":     "danger",
		"overallocated":  "warning",
		"underutilized":  "warning",
		"health_score":   "success",
	}

	for key, value := range m {
		label, ok := labels[key]
		if !ok {
			label = key
		}

		var valueStr string
		switch v := value.(type) {
		case float64:
			valueStr = fmt.Sprintf("%.0f", v)
		case int:
			valueStr = fmt.Sprintf("%d", v)
		case int64:
			valueStr = fmt.Sprintf("%d", v)
		case uint:
			valueStr = fmt.Sprintf("%d", v)
		default:
			valueStr = fmt.Sprintf("%v", v)
		}

		colorClass := ""
		if c, ok := colors[key]; ok {
			colorClass = " " + c
		}

		html += fmt.Sprintf(`
            <div class="summary-card%s">
                <div class="summary-value">%s</div>
                <div class="summary-label">%s</div>
            </div>`, colorClass, valueStr, label)
	}

	html += `</div>`
	return html
}

// renderTable 渲染表格
func (g *Generator) renderTable(data interface{}) string {
	// 支持多种数据格式
	switch v := data.(type) {
	case []map[string]interface{}:
		return g.renderMapTable(v)
	case map[string]interface{}:
		// 单行数据
		return g.renderSingleRowTable(v)
	default:
		return `<p>无法渲染的表格数据</p>`
	}
}

// renderMapTable 渲染 map 切片表格
func (g *Generator) renderMapTable(rows []map[string]interface{}) string {
	if len(rows) == 0 {
		return `<p>无数据</p>`
	}

	// 获取所有列名
	columns := make([]string, 0)
	seen := make(map[string]bool)
	for _, row := range rows {
		for key := range row {
			if !seen[key] {
				seen[key] = true
				columns = append(columns, key)
			}
		}
	}

	html := `<table><thead><tr>`
	for _, col := range columns {
		html += `<th>` + escapeHTML(col) + `</th>`
	}
	html += `</tr></thead><tbody>`

	for _, row := range rows {
		html += `<tr>`
		for _, col := range columns {
			val := fmt.Sprintf("%v", row[col])
			html += `<td>` + escapeHTML(val) + `</td>`
		}
		html += `</tr>`
	}

	html += `</tbody></table>`
	return html
}

// renderSingleRowTable 渲染单行表格（键值对）
func (g *Generator) renderSingleRowTable(data map[string]interface{}) string {
	html := `<table><tbody>`

	for key, value := range data {
		val := fmt.Sprintf("%v", value)
		html += `<tr>
            <td><strong>` + escapeHTML(key) + `</strong></td>
            <td>` + escapeHTML(val) + `</td>
        </tr>`
	}

	html += `</tbody></table>`
	return html
}

// renderList 渲染列表
func (g *Generator) renderList(data interface{}) string {
	items, ok := data.([]string)
	if !ok {
		// 尝试从 interface 切片转换
		if ifaceItems, ok := data.([]interface{}); ok {
			items = make([]string, len(ifaceItems))
			for i, v := range ifaceItems {
				items[i] = fmt.Sprintf("%v", v)
			}
		} else {
			return `<p>无效的列表数据</p>`
		}
	}

	if len(items) == 0 {
		return `<p>列表为空</p>`
	}

	html := `<div>`
	for _, item := range items {
		// 根据内容确定样式
		itemClass := ""
		if strings.Contains(item, "风险") || strings.Contains(item, "警告") {
			itemClass = " warning"
		} else if strings.Contains(item, "错误") || strings.Contains(item, "失败") {
			itemClass = " danger"
		} else if strings.Contains(item, "成功") || strings.Contains(item, "正常") {
			itemClass = " success"
		}

		html += fmt.Sprintf(`<div class="list-item%s">%s</div>`, itemClass, escapeHTML(item))
	}
	html += `</div>`

	return html
}

// sanitizeFilename 清理文件名
func sanitizeFilename(name string) string {
	// 移除或替换不安全的字符
	replacer := strings.NewReplacer(
		" ", "_",
		"/", "-",
		"\\", "-",
		":", "-",
		"*", "",
		"?", "",
		"\"", "",
		"<", "",
		">", "",
		"|", "",
	)
	return replacer.Replace(name)
}

// escapeHTML 转义 HTML 特殊字符
func escapeHTML(s string) string {
	replacer := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		"\"", "&quot;",
		"'", "&#39;",
	)
	return replacer.Replace(s)
}
