package report

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/xuri/excelize/v2"
)

// ExcelGenerator Excel 报告生成器
type ExcelGenerator struct {
	data      *ReportData
	outputDir string
	file      *excelize.File
	styles    *excelStyles
}

// excelStyles Excel 样式缓存
type excelStyles struct {
	header   int
	title    int
	subtitle int
	normal   int
	warning  int
	danger   int
	success  int
	border   int
	number   int
	percent  int
}

// NewExcelGenerator 创建 Excel 生成器
func NewExcelGenerator(data *ReportData, outputDir string) *ExcelGenerator {
	if outputDir == "" {
		outputDir = os.TempDir()
	}
	return &ExcelGenerator{
		data:      data,
		outputDir: outputDir,
		file:      excelize.NewFile(),
	}
}

// Generate 生成 Excel 报告
func (g *ExcelGenerator) Generate() (string, error) {
	// 设置生成时间
	g.data.GeneratedAt = time.Now()

	// 初始化样式
	if err := g.initStyles(); err != nil {
		return "", fmt.Errorf("初始化样式失败: %w", err)
	}

	// 删除默认 Sheet
	g.file.DeleteSheet("Sheet1")

	// 创建各个 Sheet
	if err := g.createSummarySheet(); err != nil {
		return "", fmt.Errorf("创建概览 Sheet 失败: %w", err)
	}

	if err := g.createZombieVMSheet(); err != nil {
		return "", fmt.Errorf("创建僵尸 VM Sheet 失败: %w", err)
	}

	if err := g.createRightSizeSheet(); err != nil {
		return "", fmt.Errorf("创建 Right Size Sheet 失败: %w", err)
	}

	if err := g.createTidalSheet(); err != nil {
		return "", fmt.Errorf("创建潮汐检测 Sheet 失败: %w", err)
	}

	if err := g.createHealthSheet(); err != nil {
		return "", fmt.Errorf("创建健康评分 Sheet 失败: %w", err)
	}

	if err := g.createVMSheet(); err != nil {
		return "", fmt.Errorf("创建虚拟机列表 Sheet 失败: %w", err)
	}

	// 生成文件名
	filename := fmt.Sprintf("%s_%s.xlsx", sanitizeFilename(g.data.Title), time.Now().Format("20060102_150405"))
	filepath := filepath.Join(g.outputDir, filename)

	// 保存文件
	if err := g.file.SaveAs(filepath); err != nil {
		return "", fmt.Errorf("保存文件失败: %w", err)
	}

	g.file.Close()
	return filepath, nil
}

// initStyles 初始化样式
func (g *ExcelGenerator) initStyles() error {
	g.styles = &excelStyles{}

	// 标题样式
	titleStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{
			Bold:  true,
			Size:  18,
			Color: "409EFF",
		},
		Alignment: &excelize.Alignment{
			Horizontal: "center",
			Vertical:   "center",
		},
	})
	if err != nil {
		return err
	}
	g.styles.title = titleStyle

	// 副标题样式
	subtitleStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{
			Bold:  true,
			Size:  14,
			Color: "606266",
		},
		Alignment: &excelize.Alignment{
			Horizontal: "left",
			Vertical:   "center",
		},
	})
	if err != nil {
		return err
	}
	g.styles.subtitle = subtitleStyle

	// 表头样式
	headerStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{
			Bold: true,
			Size: 12,
		},
		Fill: excelize.Fill{
			Type:    "pattern",
			Color:   []string{"E8F4FF"},
			Pattern: 1,
		},
		Border: []excelize.Border{
			{Type: "left", Color: "CCCCCC", Style: 1},
			{Type: "top", Color: "CCCCCC", Style: 1},
			{Type: "bottom", Color: "CCCCCC", Style: 1},
			{Type: "right", Color: "CCCCCC", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Horizontal: "center",
			Vertical:   "center",
			WrapText:   true,
		},
	})
	if err != nil {
		return err
	}
	g.styles.header = headerStyle

	// 普通单元格样式（带边框）
	normalStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{Size: 11},
		Border: []excelize.Border{
			{Type: "left", Color: "EEEEEE", Style: 1},
			{Type: "top", Color: "EEEEEE", Style: 1},
			{Type: "bottom", Color: "EEEEEE", Style: 1},
			{Type: "right", Color: "EEEEEE", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Vertical: "center",
		},
	})
	if err != nil {
		return err
	}
	g.styles.normal = normalStyle
	g.styles.border = normalStyle

	// 数字样式
	numberStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{Size: 11},
		Border: []excelize.Border{
			{Type: "left", Color: "EEEEEE", Style: 1},
			{Type: "top", Color: "EEEEEE", Style: 1},
			{Type: "bottom", Color: "EEEEEE", Style: 1},
			{Type: "right", Color: "EEEEEE", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Horizontal: "right",
			Vertical:   "center",
		},
		NumFmt: 1,
	})
	if err != nil {
		return err
	}
	g.styles.number = numberStyle

	// 百分比样式
	percentStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{Size: 11},
		Border: []excelize.Border{
			{Type: "left", Color: "EEEEEE", Style: 1},
			{Type: "top", Color: "EEEEEE", Style: 1},
			{Type: "bottom", Color: "EEEEEE", Style: 1},
			{Type: "right", Color: "EEEEEE", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Horizontal: "right",
			Vertical:   "center",
		},
		NumFmt: 9,
	})
	if err != nil {
		return err
	}
	g.styles.percent = percentStyle

	// 警告样式
	warningStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{Size: 11, Color: "E6A23C"},
		Fill: excelize.Fill{
			Type:    "pattern",
			Color:   []string{"FDF6EC"},
			Pattern: 1,
		},
		Border: []excelize.Border{
			{Type: "left", Color: "EEEEEE", Style: 1},
			{Type: "top", Color: "EEEEEE", Style: 1},
			{Type: "bottom", Color: "EEEEEE", Style: 1},
			{Type: "right", Color: "EEEEEE", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Vertical: "center",
		},
	})
	if err != nil {
		return err
	}
	g.styles.warning = warningStyle

	// 危险样式
	dangerStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{Size: 11, Color: "F56C6C"},
		Fill: excelize.Fill{
			Type:    "pattern",
			Color:   []string{"FEF0F0"},
			Pattern: 1,
		},
		Border: []excelize.Border{
			{Type: "left", Color: "EEEEEE", Style: 1},
			{Type: "top", Color: "EEEEEE", Style: 1},
			{Type: "bottom", Color: "EEEEEE", Style: 1},
			{Type: "right", Color: "EEEEEE", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Vertical: "center",
		},
	})
	if err != nil {
		return err
	}
	g.styles.danger = dangerStyle

	// 成功样式
	successStyle, err := g.file.NewStyle(&excelize.Style{
		Font: &excelize.Font{Size: 11, Color: "67C23A"},
		Fill: excelize.Fill{
			Type:    "pattern",
			Color:   []string{"F0F9FF"},
			Pattern: 1,
		},
		Border: []excelize.Border{
			{Type: "left", Color: "EEEEEE", Style: 1},
			{Type: "top", Color: "EEEEEE", Style: 1},
			{Type: "bottom", Color: "EEEEEE", Style: 1},
			{Type: "right", Color: "EEEEEE", Style: 1},
		},
		Alignment: &excelize.Alignment{
			Vertical: "center",
		},
	})
	if err != nil {
		return err
	}
	g.styles.success = successStyle

	return nil
}

// createSummarySheet 创建概览 Sheet
func (g *ExcelGenerator) createSummarySheet() error {
	sheet := "概览"
	index, err := g.file.NewSheet(sheet)
	if err != nil {
		return err
	}
	g.file.SetActiveSheet(index)

	// 设置列宽
	g.file.SetColWidth(sheet, "A", "B", 20)
	g.file.SetColWidth(sheet, "C", "C", 35)

	// 标题
	g.file.SetCellValue(sheet, "A1", g.data.Title)
	g.file.SetCellStyle(sheet, "A1", "C1", g.styles.title)
	g.file.MergeCell(sheet, "A1", "C1")

	// 生成时间
	g.file.SetCellValue(sheet, "A2", "生成时间: "+g.data.GeneratedAt.Format("2006-01-02 15:04:05"))
	g.file.SetCellStyle(sheet, "A2", "C2", g.styles.subtitle)
	g.file.MergeCell(sheet, "A2", "C2")

	// 空行
	row := 4

	// 汇总数据
	for _, section := range g.data.Sections {
		if section.Type == "summary" {
			g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), section.Title)
			g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.subtitle)
			g.file.MergeCell(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row))
			row++

			if m, ok := section.Data.(map[string]interface{}); ok {
				for key, value := range m {
					label := getMetricLabel(key)
					g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), label)
					g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("A%d", row), g.styles.normal)

					g.file.SetCellValue(sheet, fmt.Sprintf("B%d", row), value)
					style := g.getNumberStyle(key)
					g.file.SetCellStyle(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("B%d", row), style)

					// 备注
					remark := getMetricRemark(key)
					if remark != "" {
						g.file.SetCellValue(sheet, fmt.Sprintf("C%d", row), remark)
						g.file.SetCellStyle(sheet, fmt.Sprintf("C%d", row), fmt.Sprintf("C%d", row), g.styles.normal)
					}

					row++
				}
			}
			row += 2
		}
	}

	// 风险和建议
	for _, section := range g.data.Sections {
		if section.Type == "list" {
			g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), section.Title)
			g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.subtitle)
			g.file.MergeCell(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row))
			row++

			if items, ok := section.Data.([]string); ok {
				for _, item := range items {
					g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), "•")
					g.file.SetCellValue(sheet, fmt.Sprintf("B%d", row), item)
					g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.normal)
					g.file.MergeCell(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("C%d", row))
					row++
				}
			}
			break
		}
	}

	return nil
}

// createZombieVMSheet 创建僵尸 VM 检测 Sheet
func (g *ExcelGenerator) createZombieVMSheet() error {
	sheet := "僵尸VM"
	_, err := g.file.NewSheet(sheet)
	if err != nil {
		return err
	}

	// 设置列宽
	g.file.SetColWidth(sheet, "A", "A", 25)
	g.file.SetColWidth(sheet, "B", "G", 15)
	g.file.SetColWidth(sheet, "H", "H", 40)

	// 表头
	headers := []string{"虚拟机名称", "集群", "主机", "CPU(核)", "内存(GB)", "CPU使用率", "内存使用率", "置信度", "建议"}
	for i, h := range headers {
		cell := fmt.Sprintf("%s1", string(rune('A'+i)))
		g.file.SetCellValue(sheet, cell, h)
		g.file.SetCellStyle(sheet, cell, cell, g.styles.header)
	}

	// 数据行
	row := 2
	for _, section := range g.data.Sections {
		if section.Type == "zombie_table" {
			if rows, ok := section.Data.([]map[string]interface{}); ok {
				for _, r := range rows {
					g.setRowValue(sheet, row, r)
					// 置信度高的标红
					if confidence, ok := r["confidence"].(float64); ok && confidence >= 90 {
						g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("I%d", row), g.styles.danger)
					} else if confidence, ok := r["confidence"].(float64); ok && confidence >= 70 {
						g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("I%d", row), g.styles.warning)
					}
					row++
				}
			}
			break
		}
	}

	return nil
}

// createRightSizeSheet 创建 Right Size Sheet
func (g *ExcelGenerator) createRightSizeSheet() error {
	sheet := "RightSize"
	_, err := g.file.NewSheet(sheet)
	if err != nil {
		return err
	}

	// 设置列宽
	g.file.SetColWidth(sheet, "A", "A", 25)
	g.file.SetColWidth(sheet, "B", "C", 15)
	g.file.SetColWidth(sheet, "D", "E", 12)
	g.file.SetColWidth(sheet, "F", "F", 12)
	g.file.SetColWidth(sheet, "G", "G", 10)
	g.file.SetColWidth(sheet, "H", "H", 15)
	g.file.SetColWidth(sheet, "I", "I", 40)

	// 表头
	headers := []string{"虚拟机名称", "集群", "当前CPU", "推荐CPU", "当前内存(GB)", "推荐内存(GB)", "调整类型", "风险等级", "节省估算", "置信度"}
	for i, h := range headers {
		cell := fmt.Sprintf("%s1", string(rune('A'+i)))
		g.file.SetCellValue(sheet, cell, h)
		g.file.SetCellStyle(sheet, cell, cell, g.styles.header)
	}

	// 数据行
	row := 2
	for _, section := range g.data.Sections {
		if section.Type == "rightsize_table" {
			if rows, ok := section.Data.([]map[string]interface{}); ok {
				for _, r := range rows {
					g.setRowValue(sheet, row, r)
					// 根据风险等级设置样式
					if risk, ok := r["riskLevel"].(string); ok {
						style := g.styles.normal
						if risk == "高" {
							style = g.styles.danger
						} else if risk == "中" {
							style = g.styles.warning
						} else if risk == "低" {
							style = g.styles.success
						}
						g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("J%d", row), style)
					}
					row++
				}
			}
			break
		}
	}

	return nil
}

// createTidalSheet 创建潮汐检测 Sheet
func (g *ExcelGenerator) createTidalSheet() error {
	sheet := "潮汐检测"
	_, err := g.file.NewSheet(sheet)
	if err != nil {
		return err
	}

	// 设置列宽
	g.file.SetColWidth(sheet, "A", "A", 25)
	g.file.SetColWidth(sheet, "B", "F", 15)
	g.file.SetColWidth(sheet, "G", "G", 40)

	// 表头
	headers := []string{"虚拟机名称", "集群", "模式类型", "稳定性评分", "高峰时段", "高峰日期", "节省估算", "建议"}
	for i, h := range headers {
		cell := fmt.Sprintf("%s1", string(rune('A'+i)))
		g.file.SetCellValue(sheet, cell, h)
		g.file.SetCellStyle(sheet, cell, cell, g.styles.header)
	}

	// 数据行
	row := 2
	for _, section := range g.data.Sections {
		if section.Type == "tidal_table" {
			if rows, ok := section.Data.([]map[string]interface{}); ok {
				for _, r := range rows {
					g.setRowValue(sheet, row, r)
					row++
				}
			}
			break
		}
	}

	return nil
}

// createHealthSheet 创建健康评分 Sheet
func (g *ExcelGenerator) createHealthSheet() error {
	sheet := "健康评分"
	_, err := g.file.NewSheet(sheet)
	if err != nil {
		return err
	}

	// 设置列宽
	g.file.SetColWidth(sheet, "A", "B", 20)
	g.file.SetColWidth(sheet, "C", "C", 30)

	// 标题
	row := 1
	g.file.SetCellValue(sheet, "A1", "平台健康评分报告")
	g.file.SetCellStyle(sheet, "A1", "C1", g.styles.title)
	g.file.MergeCell(sheet, "A1", "C1")
	row += 2

	// 总体评分
	for _, section := range g.data.Sections {
		if section.Type == "health_summary" {
			if m, ok := section.Data.(map[string]interface{}); ok {
				// 评分大字显示
				if score, ok := m["overallScore"].(float64); ok {
					g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), "总体评分")
					g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("A%d", row), g.styles.subtitle)

					scoreStyle, _ := g.file.NewStyle(&excelize.Style{
						Font:      &excelize.Font{Bold: true, Size: 36, Color: getHealthColor(score)},
						Alignment: &excelize.Alignment{Horizontal: "center", Vertical: "center"},
					})
					g.file.SetCellValue(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("%.0f", score))
					g.file.SetCellStyle(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("C%d", row), scoreStyle)
					g.file.MergeCell(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("C%d", row))
					row += 2
				}

				// 详细指标
				for key, value := range m {
					if key == "overallScore" {
						continue
					}
					label := getMetricLabel(key)
					g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), label)
					g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("A%d", row), g.styles.normal)

					g.file.SetCellValue(sheet, fmt.Sprintf("B%d", row), value)
					g.file.SetCellStyle(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("B%d", row), g.styles.number)
					row++
				}
			}
			break
		}
	}

	// 风险项
	row += 2
	for _, section := range g.data.Sections {
		if section.Type == "risk_list" {
			g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), "风险项")
			g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.subtitle)
			g.file.MergeCell(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row))
			row++

			if items, ok := section.Data.([]string); ok {
				for _, item := range items {
					g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), "⚠")
					g.file.SetCellValue(sheet, fmt.Sprintf("B%d", row), item)
					g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.warning)
					g.file.MergeCell(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("C%d", row))
					row++
				}
			}
		}
	}

	// 建议
	row += 1
	for _, section := range g.data.Sections {
		if section.Type == "recommendation_list" {
			g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), "改进建议")
			g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.subtitle)
			g.file.MergeCell(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row))
			row++

			if items, ok := section.Data.([]string); ok {
				for _, item := range items {
					g.file.SetCellValue(sheet, fmt.Sprintf("A%d", row), "💡")
					g.file.SetCellValue(sheet, fmt.Sprintf("B%d", row), item)
					g.file.SetCellStyle(sheet, fmt.Sprintf("A%d", row), fmt.Sprintf("C%d", row), g.styles.success)
					g.file.MergeCell(sheet, fmt.Sprintf("B%d", row), fmt.Sprintf("C%d", row))
					row++
				}
			}
			break
		}
	}

	return nil
}

// createVMSheet 创建虚拟机列表 Sheet
func (g *ExcelGenerator) createVMSheet() error {
	sheet := "虚拟机列表"
	_, err := g.file.NewSheet(sheet)
	if err != nil {
		return err
	}

	// 设置列宽
	g.file.SetColWidth(sheet, "A", "A", 25)
	g.file.SetColWidth(sheet, "B", "D", 15)
	g.file.SetColWidth(sheet, "E", "F", 12)
	g.file.SetColWidth(sheet, "G", "G", 10)

	// 表头
	headers := []string{"虚拟机名称", "集群", "主机", "操作系统", "CPU", "内存(GB)", "磁盘(GB)", "电源状态"}
	for i, h := range headers {
		cell := fmt.Sprintf("%s1", string(rune('A'+i)))
		g.file.SetCellValue(sheet, cell, h)
		g.file.SetCellStyle(sheet, cell, cell, g.styles.header)
	}

	// 数据行
	row := 2
	for _, section := range g.data.Sections {
		if section.Type == "vm_table" {
			if rows, ok := section.Data.([]map[string]interface{}); ok {
				for _, r := range rows {
					g.setRowValue(sheet, row, r)
					row++
				}
			}
			break
		}
	}

	return nil
}

// setRowValue 设置一行数据
func (g *ExcelGenerator) setRowValue(sheet string, row int, data map[string]interface{}) {
	col := 'A'
	for _, value := range data {
		cell := fmt.Sprintf("%s%d", string(col), row)
		g.file.SetCellValue(sheet, cell, value)
		g.file.SetCellStyle(sheet, cell, cell, g.styles.normal)
		col++
	}
}

// getNumberStyle 获取数字样式
func (g *ExcelGenerator) getNumberStyle(key string) int {
	if contains(key, []string{"percent", "ratio", "score", "usage"}) {
		return g.styles.percent
	}
	return g.styles.number
}

// getHealthColor 获取健康分数颜色
func getHealthColor(score float64) string {
	if score >= 80 {
		return "67C23A"
	} else if score >= 60 {
		return "E6A23C"
	}
	return "F56C6C"
}

// getMetricLabel 获取指标标签
func getMetricLabel(key string) string {
	labels := map[string]string{
		"vmCount":         "虚拟机总数",
		"hostCount":       "主机总数",
		"clusterCount":    "集群总数",
		"zombieVMs":       "僵尸 VM 数量",
		"overallocated":   "超配 VM 数量",
		"underutilized":   "低利用率 VM 数量",
		"healthScore":     "健康评分",
		"resourceBalance": "资源均衡度",
		"overcommitRisk":  "超配风险",
		"hotspotLevel":    "热点集中度",
		"overallScore":    "总体评分",
	}
	if label, ok := labels[key]; ok {
		return label
	}
	return key
}

// getMetricRemark 获取指标备注
func getMetricRemark(key string) string {
	remarks := map[string]string{
		"zombieVMs":     "建议关机或删除",
		"overallocated": "建议降配",
		"underutilized": "建议合并或优化",
		"healthScore":   "满分100分",
	}
	if remark, ok := remarks[key]; ok {
		return remark
	}
	return ""
}

// contains 检查字符串是否包含在数组中
func contains(s string, list []string) bool {
	for _, item := range list {
		if s == item {
			return true
		}
	}
	return false
}
