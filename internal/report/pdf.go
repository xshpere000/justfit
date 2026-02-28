package report

import (
	"embed"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"text/template"
	"time"

	"github.com/signintech/gopdf"
	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/extension"
)

//go:embed template.md fonts
var assets embed.FS

// 字体文件路径（相对于 embed.FS）
const (
	fontFilePath = "fonts/simhei.ttf"
	fontFamily   = "simhei"
)

// PDFGenerator PDF 报告生成器
type PDFGenerator struct {
	data        *ReportData
	chartImages *ChartImages
	outputDir   string
	template    string
	fontFamily  string // 使用的字体系列
}

// PDFConfig PDF 配置
type PDFConfig struct {
	OutputDir string `json:"outputDir"`
}

// NewPDFGenerator 创建 PDF 生成器
func NewPDFGenerator(data *ReportData, chartImages *ChartImages, config *PDFConfig) *PDFGenerator {
	if config == nil {
		config = &PDFConfig{
			OutputDir: os.TempDir(),
		}
	}
	if config.OutputDir == "" {
		config.OutputDir = os.TempDir()
	}
	os.MkdirAll(config.OutputDir, 0755)

	return &PDFGenerator{
		data:        data,
		chartImages: chartImages,
		outputDir:   config.OutputDir,
		fontFamily:  "Helvetica", // 默认使用内置字体
	}
}

// loadTemplate 加载 Markdown 模板
func (g *PDFGenerator) loadTemplate() error {
	if g.template != "" {
		return nil
	}

	content, err := assets.ReadFile("template.md")
	if err != nil {
		return fmt.Errorf("读取模板文件失败: %w", err)
	}

	g.template = string(content)
	return nil
}

// renderMarkdown 渲染 Markdown 文本
func (g *PDFGenerator) renderMarkdown() (string, error) {
	if err := g.loadTemplate(); err != nil {
		return "", err
	}

	// 创建 FuncMap 支持模板函数
	funcMap := template.FuncMap{
		"formatMemory": formatMemory,
	}

	// 使用 text/template 渲染模板
	tmpl, err := template.New("pdf").Funcs(funcMap).Parse(g.template)
	if err != nil {
		return "", fmt.Errorf("解析模板失败: %w", err)
	}

	// 准备模板数据
	templateData := struct {
		Title            string
		GeneratedAt      time.Time
		Platform         string
		ConnectionName   string
		ClusterCount     int
		HostCount        int
		VMCount          int
		MetricsDays      int
		Clusters         []map[string]interface{}
		Hosts            []map[string]interface{}
		VMs              []map[string]interface{}
		ZombieVMs        []map[string]interface{}
		RightSizeResults []map[string]interface{}
		TidalResults     []map[string]interface{}
		HealthScore      map[string]interface{}
		Charts           []ChartRef
	}{
		Title:            g.data.Title,
		GeneratedAt:      g.data.GeneratedAt,
		Platform:         getPlatformName(g.data.ConnectionID),
		ConnectionName:   getConnectionName(g.data.Metadata),
		ClusterCount:     getCount(g.data.Metadata, "clusterCount"),
		HostCount:        getCount(g.data.Metadata, "hostCount"),
		VMCount:          getCount(g.data.Metadata, "vmCount"),
		MetricsDays:      getMetricsDays(g.data.Metadata),
		Clusters:         getClusters(g.data),
		Hosts:            getHosts(g.data),
		VMs:              getVMs(g.data),
		ZombieVMs:        getZombieVMs(g.data),
		RightSizeResults: getRightSizeResults(g.data),
		TidalResults:     getTidalResults(g.data),
		HealthScore:      getHealthScore(g.data),
		Charts:           getChartRefs(g.chartImages),
	}

	var buf strings.Builder
	if err := tmpl.Execute(&buf, templateData); err != nil {
		return "", fmt.Errorf("渲染模板失败: %w", err)
	}

	return buf.String(), nil
}

// Generate 生成 PDF 报告
func (g *PDFGenerator) Generate() (string, error) {
	// 1. 渲染 Markdown
	markdown, err := g.renderMarkdown()
	if err != nil {
		return "", fmt.Errorf("渲染 Markdown 失败: %w", err)
	}

	// 2. 转换为 HTML
	html := g.markdownToHTML(markdown)

	// 3. 生成 PDF
	return g.generatePDF(html)
}

// markdownToHTML 将 Markdown 转换为 HTML
func (g *PDFGenerator) markdownToHTML(markdown string) string {
	md := goldmark.New(
		goldmark.WithExtensions(
			extension.GFM,
			extension.Table,
		),
	)

	var buf strings.Builder
	if err := md.Convert([]byte(markdown), &buf); err != nil {
		fmt.Printf("Markdown 转换失败: %v\n", err)
		return ""
	}

	return buf.String()
}

// generatePDF 使用 gopdf 生成 PDF
func (g *PDFGenerator) generatePDF(htmlContent string) (string, error) {
	pdf := gopdf.GoPdf{}
	pdf.Start(gopdf.Config{PageSize: *gopdf.PageSizeA4})
	pdf.AddPage()

	// 尝试加载中文字体
	fontLoaded := false
	fontPath, err := g.extractFontFile()
	if err != nil {
		fmt.Printf("[PDFGenerator] 警告: 无法提取字体文件: %v\n", err)
	} else {
		defer os.Remove(fontPath)

		// 尝试加载 TTF 字体
		if err := pdf.AddTTFFont(fontFamily, fontPath); err != nil {
			fmt.Printf("[PDFGenerator] 警告: 加载 TTF 字体失败: %v\n", err)
		} else {
			fontLoaded = true
			g.fontFamily = fontFamily
			fmt.Printf("[PDFGenerator] 成功加载中文字体: %s\n", fontFamily)
		}
	}

	// 如果没有加载成功，使用内置字体
	if !fontLoaded {
		fmt.Printf("[PDFGenerator] 使用内置字体（不支持中文）\n")
		g.fontFamily = "Helvetica"
	}

	// 测试字体是否可用
	pdf.SetFont(g.fontFamily, "", 12)
	pdf.SetY(50)

	// A4 页面尺寸 (单位: point, 1pt ≈ 1.33px)
	const (
		pageWidth    = 595.28
		pageHeight   = 841.89
		marginTop    = 50.0
		marginLeft   = 50.0
		marginRight  = 50.0
		marginBottom = 50.0
		contentWidth = pageWidth - marginLeft - marginRight
	)

	// 初始 Y 坐标
	y := marginTop
	lineHeight := 14.0

	// 简化的 HTML 解析和绘制
	lines := strings.Split(htmlContent, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			y += lineHeight / 2
			continue
		}

		// 检查是否需要新页
		if y > pageHeight-marginBottom {
			pdf.AddPage()
			y = marginTop
		}

		// 处理 HTML 标签（简化版本）
		if strings.HasPrefix(line, "<h1>") {
			text := extractText(line, "<h1>", "</h1>")
			pdf.SetFont(g.fontFamily, "", 24)
			pdf.SetTextColor(40, 158, 255)
			pdf.SetX(marginLeft)
			pdf.SetY(y)
			pdf.Cell(nil, text)
			y += 30
			pdf.Br(25)
		} else if strings.HasPrefix(line, "<h2>") {
			text := extractText(line, "<h2>", "</h2>")
			pdf.SetFont(g.fontFamily, "", 20)
			pdf.SetTextColor(51, 51, 51)
			pdf.SetX(marginLeft)
			pdf.SetY(y)
			pdf.Cell(nil, text)
			y += 25
			pdf.Br(20)
		} else if strings.HasPrefix(line, "<h3>") {
			text := extractText(line, "<h3>", "</h3>")
			pdf.SetFont(g.fontFamily, "", 18)
			pdf.SetTextColor(51, 51, 51)
			pdf.SetX(marginLeft)
			pdf.SetY(y)
			pdf.Cell(nil, text)
			y += 20
			pdf.Br(15)
		} else if strings.HasPrefix(line, "<p>") {
			text := htmlToString(line)
			pdf.SetFont(g.fontFamily, "", 12)
			pdf.SetTextColor(51, 51, 51)
			pdf.SetX(marginLeft)
			// 简单文本换行处理
			wrappedLines := wrapText(text, contentWidth, pdf)
			for _, ln := range wrappedLines {
				if y > pageHeight-marginBottom {
					pdf.AddPage()
					y = marginTop
				}
				pdf.SetX(marginLeft)
				pdf.SetY(y)
				pdf.Cell(nil, ln)
				y += lineHeight
			}
		} else if strings.HasPrefix(line, "<li>") {
			text := htmlToString(line)
			pdf.SetFont(g.fontFamily, "", 12)
			pdf.SetTextColor(51, 51, 51)
			pdf.SetX(marginLeft + 20)
			pdf.SetY(y)
			pdf.Cell(nil, "• "+text)
			y += lineHeight
		} else if !strings.HasPrefix(line, "<") {
			// 普通文本（不属于 HTML 标签）
			if y > pageHeight-marginBottom {
				pdf.AddPage()
				y = marginTop
			}
			pdf.SetFont(g.fontFamily, "", 12)
			pdf.SetTextColor(51, 51, 51)
			pdf.SetX(marginLeft)
			pdf.SetY(y)
			pdf.Cell(nil, line)
			y += lineHeight
		}
	}

	// 保存文件
	filename := fmt.Sprintf("%s_%s.pdf", sanitizeFilename(g.data.Title), time.Now().Format("20060102_150405"))
	filepath := filepath.Join(g.outputDir, filename)

	if err := pdf.WritePdf(filepath); err != nil {
		return "", fmt.Errorf("保存 PDF 失败: %w", err)
	}

	fmt.Printf("[PDFGenerator] PDF 生成成功: %s\n", filepath)
	return filepath, nil
}

// extractFontFile 从 embed.FS 提取字体文件到临时目录
func (g *PDFGenerator) extractFontFile() (string, error) {
	data, err := assets.ReadFile(fontFilePath)
	if err != nil {
		return "", fmt.Errorf("读取嵌入字体失败: %w", err)
	}

	tmpFile, err := os.CreateTemp("", "justfit-font-*.ttf")
	if err != nil {
		return "", fmt.Errorf("创建临时文件失败: %w", err)
	}

	// 确保文件被正确写入和关闭
	if _, err := tmpFile.Write(data); err != nil {
		tmpFile.Close()
		return "", fmt.Errorf("写入字体数据失败: %w", err)
	}
	if err := tmpFile.Close(); err != nil {
		return "", fmt.Errorf("关闭临时文件失败: %w", err)
	}

	return tmpFile.Name(), nil
}

// htmlToString 简单的 HTML 标签去除
func htmlToString(s string) string {
	// 去除常见 HTML 标签
	s = strings.ReplaceAll(s, "<p>", "")
	s = strings.ReplaceAll(s, "</p>", "")
	s = strings.ReplaceAll(s, "<strong>", "")
	s = strings.ReplaceAll(s, "</strong>", "")
	s = strings.ReplaceAll(s, "<em>", "")
	s = strings.ReplaceAll(s, "</em>", "")
	s = strings.ReplaceAll(s, "<br>", "")
	s = strings.ReplaceAll(s, "<br/>", "")
	s = strings.ReplaceAll(s, "<li>", "")
	s = strings.ReplaceAll(s, "</li>", "")
	return strings.TrimSpace(s)
}

// wrapText 简单的文本换行
func wrapText(text string, maxWidth float64, pdf gopdf.GoPdf) []string {
	// 简化实现：每 60 个字符换行（假设平均字符宽度）
	maxChars := int(maxWidth / 6) // 粗略估计
	var lines []string
	for i := 0; i < len(text); i += maxChars {
		end := i + maxChars
		if end > len(text) {
			end = len(text)
		}
		lines = append(lines, text[i:end])
	}
	if len(lines) == 0 && text != "" {
		lines = append(lines, text)
	}
	return lines
}

// extractText 从 HTML 标签中提取文本
func extractText(line, startTag, endTag string) string {
	start := strings.Index(line, startTag) + len(startTag)
	end := strings.Index(line[start:], endTag)
	if end == -1 {
		return line[start:]
	}
	return line[start : start+end]
}

// 辅助函数
func getPlatformName(connectionID uint) string {
	if connectionID == 0 {
		return "Unknown"
	}
	// 这里可以从数据库查询实际平台名称
	return "vSphere" // 简化
}

func getConnectionName(metadata map[string]interface{}) string {
	if name, ok := metadata["connectionName"].(string); ok {
		return name
	}
	return "Unknown"
}

func getCount(metadata map[string]interface{}, key string) int {
	if val, ok := metadata[key].(int); ok {
		return val
	}
	return 0
}

func getMetricsDays(metadata map[string]interface{}) int {
	if val, ok := metadata["metricsDays"].(int); ok {
		return val
	}
	return 30
}

// getClusters 从 Sections 中提取集群数据
func getClusters(data *ReportData) []map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "cluster_table" {
			if clusters, ok := section.Data.([]map[string]interface{}); ok {
				return clusters
			}
		}
	}
	return []map[string]interface{}{}
}

// getHosts 从 Sections 中提取主机数据
func getHosts(data *ReportData) []map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "host_table" {
			if hosts, ok := section.Data.([]map[string]interface{}); ok {
				return hosts
			}
		}
	}
	return []map[string]interface{}{}
}

// getVMs 从 Sections 中提取虚拟机数据
func getVMs(data *ReportData) []map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "vm_table" {
			if vms, ok := section.Data.([]map[string]interface{}); ok {
				return vms
			}
		}
	}
	return []map[string]interface{}{}
}

// getZombieVMs 从 Sections 中提取僵尸 VM 数据
func getZombieVMs(data *ReportData) []map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "zombie_table" {
			if zombies, ok := section.Data.([]map[string]interface{}); ok {
				return zombies
			}
		}
	}
	return []map[string]interface{}{}
}

// getRightSizeResults 从 Sections 中提取 RightSize 数据
func getRightSizeResults(data *ReportData) []map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "rightsize_table" {
			if results, ok := section.Data.([]map[string]interface{}); ok {
				return results
			}
		}
	}
	return []map[string]interface{}{}
}

// getTidalResults 从 Sections 中提取潮汐数据
func getTidalResults(data *ReportData) []map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "tidal_table" {
			if results, ok := section.Data.([]map[string]interface{}); ok {
				return results
			}
		}
	}
	return []map[string]interface{}{}
}

// getHealthScore 从 Sections 中提取健康评分数据
func getHealthScore(data *ReportData) map[string]interface{} {
	for _, section := range data.Sections {
		if section.Type == "health_summary" {
			if score, ok := section.Data.(map[string]interface{}); ok {
				return score
			}
		}
	}
	return map[string]interface{}{}
}

// getChartRefs 从 ChartImages 获取图表引用
func getChartRefs(images *ChartImages) []ChartRef {
	if images == nil {
		return []ChartRef{}
	}

	// 使用反射遍历 ChartImages 的字段
	refs := make([]ChartRef, 0)
	v := reflect.ValueOf(*images)
	t := reflect.TypeOf(*images)

	// 图表标题映射
	chartTitles := map[string]string{
		"ClusterDistribution": "集群虚拟机分布",
		"HostUsageTop10":      "主机资源利用率 Top 10",
		"VMCpuDistribution":   "虚拟机 CPU 利用率分布",
		"VMMemoryTrend":       "虚拟机内存趋势",
		"RightSizeSummary":    "资源配置建议汇总",
	}

	for i := 0; i < v.NumField(); i++ {
		field := v.Field(i)
		fieldType := t.Field(i)

		// 获取图表路径（JSON tag 作为 key）
		jsonTag := fieldType.Tag.Get("json")
		if jsonTag == "" {
			continue
		}

		// 如果路径为空，跳过
		if field.Kind() == reflect.String && field.String() != "" {
			title := chartTitles[jsonTag]
			if title == "" {
				title = jsonTag
			}
			refs = append(refs, ChartRef{
				Title:       title,
				Path:        field.String(),
				Description: "",
				Index:       len(refs) + 1,
			})
		}
	}
	return refs
}

// ChartRef 图表引用
type ChartRef struct {
	Title       string
	Path        string
	Description string
	Index       int
}

// formatMemory 格式化内存显示
func formatMemory(mb int) string {
	if mb >= 1024 {
		return fmt.Sprintf("%.1f GB", float64(mb)/1024)
	}
	return fmt.Sprintf("%d MB", mb)
}
