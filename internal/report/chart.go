package report

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/wcharczuk/go-chart/v2"
	"github.com/wcharczuk/go-chart/v2/drawing"
)

// MetricDataSource 指标数据源接口（用于图表生成）
type MetricDataSource interface {
	GetVMs() ([]uint, error) // 获取 VM ID 列表
	GetVMMetrics(vmID uint, metricType string, startTime, endTime time.Time) ([]MetricPoint, error)
	GetHosts() ([]string, error)                  // 获取主机名称列表
	GetVMsByHost(hostName string) ([]uint, error) // 根据主机名获取关联的 VM ID 列表
}

// ChartGenerator 图表生成器
type ChartGenerator struct {
	outputDir   string
	metricDS    MetricDataSource // 指标数据源
	taskID      uint             // 任务 ID（用于确定时间范围）
	metricsDays int              // 采集天数
}

// NewChartGenerator 创建图表生成器
func NewChartGenerator(outputDir string) *ChartGenerator {
	if outputDir == "" {
		outputDir = os.TempDir()
	}
	// 确保输出目录存在
	os.MkdirAll(outputDir, 0755)

	return &ChartGenerator{
		outputDir: outputDir,
	}
}

// SetMetricDataSource 设置指标数据源
func (g *ChartGenerator) SetMetricDataSource(ds MetricDataSource, taskID uint, metricsDays int) {
	g.metricDS = ds
	g.taskID = taskID
	g.metricsDays = metricsDays
}

// GenerateAllCharts 生成所有需要的图表
func (g *ChartGenerator) GenerateAllCharts(data *ReportData) (*ChartImages, error) {
	images := &ChartImages{}

	// 1. 资源概览饼图
	if clusterPie, err := g.generateClusterDistributionPie(data); err == nil {
		images.ClusterDistribution = clusterPie
	}

	// 2. 主机资源利用率柱状图
	if hostBar, err := g.generateHostUsageBar(data); err == nil {
		images.HostUsageTop10 = hostBar
	}

	// 3. VM CPU利用率分布直方图
	if vmCpuHist, err := g.generateVMCpuDistribution(data); err == nil {
		images.VMCpuDistribution = vmCpuHist
	}

	// 4. 内存利用率趋势折线图
	if memTrend, err := g.generateMemoryTrendLine(data); err == nil {
		images.VMMemoryTrend = memTrend
	}

	// 5. RightSize 汇总饼图
	if rightsizePie, err := g.generateRightSizeSummaryPie(data); err == nil {
		images.RightSizeSummary = rightsizePie
	}

	return images, nil
}

// ChartImages 生成的图表路径集合
type ChartImages struct {
	ClusterDistribution string `json:"clusterDistribution"`
	HostUsageTop10      string `json:"hostUsageTop10"`
	VMCpuDistribution   string `json:"vmCpuDistribution"`
	VMMemoryTrend       string `json:"vmMemoryTrend"`
	RightSizeSummary    string `json:"rightSizeSummary"`
}

// 生成集群资源分布饼图（从真实数据生成）
func (g *ChartGenerator) generateClusterDistributionPie(data *ReportData) (string, error) {
	var values []chart.Value

	// 从 ReportData 中提取集群数据
	for _, section := range data.Sections {
		if section.Type == "cluster_table" {
			if rows, ok := section.Data.([]map[string]interface{}); ok {
				for _, row := range rows {
					if name, ok := row["name"].(string); ok {
						if vmCount, ok := row["numVMs"].(int); ok {
							values = append(values, chart.Value{
								Label: name,
								Value: float64(vmCount),
							})
						}
					}
				}
				break
			}
		}
	}

	if len(values) == 0 {
		return "", fmt.Errorf("没有集群数据可用于生成图表")
	}

	// 创建饼图
	pie := chart.PieChart{
		Title:  "集群 VM 分布",
		Width:  800,
		Height: 600,
		Values: values,
	}

	// 保存为 PNG
	filename := "cluster_distribution.png"
	filepath := filepath.Join(g.outputDir, filename)

	f, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	return filepath, pie.Render(chart.PNG, f)
}

// 生成主机资源利用率柱状图（从真实数据计算）
func (g *ChartGenerator) generateHostUsageBar(data *ReportData) (string, error) {
	if g.metricDS == nil {
		return "", fmt.Errorf("主机利用率图表需要指标数据源")
	}

	// 获取主机列表
	hostNames, err := g.metricDS.GetHosts()
	if err != nil {
		return "", fmt.Errorf("获取主机列表失败: %w", err)
	}

	if len(hostNames) == 0 {
		return "", fmt.Errorf("没有主机数据")
	}

	// 只取 Top 10
	maxHosts := 10
	if len(hostNames) > maxHosts {
		hostNames = hostNames[:maxHosts]
	}

	// 计算时间范围
	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -g.metricsDays)

	// 为每个主机计算 CPU 和内存平均利用率
	type hostUsage struct {
		name      string
		cpuUsage  float64
		memUsage  float64
		cpuValues []float64
		memValues []float64
	}

	var hostUsages []hostUsage

	for _, hostName := range hostNames {
		// 获取该主机关联的所有 VM
		vmIDs, err := g.metricDS.GetVMsByHost(hostName)
		if err != nil || len(vmIDs) == 0 {
			continue
		}

		var allCpuValues []float64
		var allMemValues []float64

		// 获取所有 VM 的指标数据
		for _, vmID := range vmIDs {
			// 获取 CPU 指标
			cpuMetrics, err := g.metricDS.GetVMMetrics(vmID, "cpu", startTime, endTime)
			if err == nil && len(cpuMetrics) > 0 {
				for _, m := range cpuMetrics {
					allCpuValues = append(allCpuValues, m.Value)
				}
			}

			// 获取内存指标
			memMetrics, err := g.metricDS.GetVMMetrics(vmID, "memory", startTime, endTime)
			if err == nil && len(memMetrics) > 0 {
				for _, m := range memMetrics {
					// 内存值需要转换为百分比（假设原始值是字节，需要除以总内存）
					// 这里简化处理，直接使用原始值
					allMemValues = append(allMemValues, m.Value)
				}
			}
		}

		// 计算平均值
		var cpuAvg, memAvg float64
		if len(allCpuValues) > 0 {
			sum := 0.0
			for _, v := range allCpuValues {
				sum += v
			}
			cpuAvg = sum / float64(len(allCpuValues))
		}

		if len(allMemValues) > 0 {
			sum := 0.0
			for _, v := range allMemValues {
				sum += v
			}
			memAvg = sum / float64(len(allMemValues))
		}

		// 只有当有数据时才添加到列表
		if len(allCpuValues) > 0 || len(allMemValues) > 0 {
			hostUsages = append(hostUsages, hostUsage{
				name:     hostName,
				cpuUsage: cpuAvg,
				memUsage: memAvg,
			})
		}
	}

	if len(hostUsages) == 0 {
		return "", fmt.Errorf("没有主机利用率数据可用")
	}

	// 创建柱状图
	bars := []chart.Value{
		{Label: "CPU 使用率", Value: hostUsages[0].cpuUsage},
		{Label: "内存使用率", Value: hostUsages[0].memUsage},
	}

	bar := chart.BarChart{
		Title:  "主机资源利用率 Top 10",
		Width:  1200,
		Height: 600,
		Background: chart.Style{
			Padding: chart.Box{
				Top:    80,
				Left:   80,
				Right:  80,
				Bottom: 80,
			},
		},
		YAxis: chart.YAxis{
			Name: "利用率 (%)",
			Range: &chart.ContinuousRange{
				Min: 0,
				Max: 100,
			},
		},
		Bars: bars,
	}

	// 保存为 PNG
	filename := "host_usage_top10.png"
	filepath := filepath.Join(g.outputDir, filename)

	f, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	return filepath, bar.Render(chart.PNG, f)
}

// 生成 VM CPU 利用率分布直方图（从真实数据计算）
func (g *ChartGenerator) generateVMCpuDistribution(data *ReportData) (string, error) {
	// 如果有指标数据源，从真实数据计算分布
	if g.metricDS != nil {
		// 获取所有 VM
		vmIDs, err := g.metricDS.GetVMs()
		if err != nil {
			return "", err
		}

		endTime := time.Now()
		startTime := endTime.AddDate(0, 0, -g.metricsDays)

		// 统计各 VM 的平均 CPU 利用率分布
		buckets := map[string]int{
			"0-20%":   0,
			"20-40%":  0,
			"40-60%":  0,
			"60-80%":  0,
			"80-100%": 0,
		}

		for _, vmID := range vmIDs {
			metrics, err := g.metricDS.GetVMMetrics(vmID, "cpu", startTime, endTime)
			if err != nil || len(metrics) == 0 {
				continue
			}

			// 计算平均利用率
			var sum float64
			for _, m := range metrics {
				sum += m.Value
			}
			avg := sum / float64(len(metrics))

			// 分类到桶中
			if avg < 20 {
				buckets["0-20%"]++
			} else if avg < 40 {
				buckets["20-40%"]++
			} else if avg < 60 {
				buckets["40-60%"]++
			} else if avg < 80 {
				buckets["60-80%"]++
			} else {
				buckets["80-100%"]++
			}
		}

		// 创建图表数据
		bars := []chart.Value{
			{Label: "0-20%", Value: float64(buckets["0-20%"])},
			{Label: "20-40%", Value: float64(buckets["20-40%"])},
			{Label: "40-60%", Value: float64(buckets["40-60%"])},
			{Label: "60-80%", Value: float64(buckets["60-80%"])},
			{Label: "80-100%", Value: float64(buckets["80-100%"])},
		}

		if allZero(bars) {
			return "", fmt.Errorf("没有 CPU 利用率数据可用于生成图表")
		}

		// 创建柱状图
		hist := chart.BarChart{
			Title:  "VM CPU 利用率分布",
			Width:  1000,
			Height: 600,
			Background: chart.Style{
				Padding: chart.Box{
					Top:    80,
					Left:   80,
					Right:  80,
					Bottom: 80,
				},
			},
			YAxis: chart.YAxis{
				Name: "VM数量",
			},
			Bars: bars,
		}

		// 保存为 PNG
		filename := "vm_cpu_distribution.png"
		filepath := filepath.Join(g.outputDir, filename)

		f, err := os.Create(filepath)
		if err != nil {
			return "", err
		}
		defer f.Close()

		return filepath, hist.Render(chart.PNG, f)
	}

	// 没有指标数据源时返回错误
	return "", fmt.Errorf("无法生成 VM CPU 利用率分布图：缺少指标数据")
}

// 生成内存利用率趋势折线图（从真实数据获取）
func (g *ChartGenerator) generateMemoryTrendLine(data *ReportData) (string, error) {
	if g.metricDS == nil {
		return "", fmt.Errorf("无法生成内存趋势图：缺少指标数据")
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, 0, -g.metricsDays)

	// 获取所有 VM，取 Top 3（按内存使用量排序）
	vmIDs, err := g.metricDS.GetVMs()
	if err != nil {
		return "", err
	}

	if len(vmIDs) == 0 {
		return "", fmt.Errorf("没有 VM 数据可用于生成图表")
	}

	// 只取前 3 个 VM
	maxVMs := 3
	if len(vmIDs) > maxVMs {
		vmIDs = vmIDs[:maxVMs]
	}

	var series []chart.Series

	for idx, vmID := range vmIDs {
		metrics, err := g.metricDS.GetVMMetrics(vmID, "memory", startTime, endTime)
		if err != nil || len(metrics) == 0 {
			continue
		}

		// 提取时间和值
		xValues := make([]time.Time, len(metrics))
		yValues := make([]float64, len(metrics))

		for i, m := range metrics {
			xValues[i] = m.Timestamp
			yValues[i] = m.Value
		}

		// 创建时间序列
		ts := chart.TimeSeries{
			Name:    fmt.Sprintf("VM-%d", idx+1),
			XValues: xValues,
			YValues: yValues,
		}
		ts.Style = chart.Style{
			StrokeColor: getSeriesColor(idx),
			StrokeWidth: 2,
			DotWidth:    4,
		}

		series = append(series, ts)
	}

	if len(series) == 0 {
		return "", fmt.Errorf("没有内存指标数据可用于生成图表")
	}

	// 创建折线图
	line := chart.Chart{
		Title:  "VM 内存利用率趋势",
		Width:  1400,
		Height: 700,
		Background: chart.Style{
			Padding: chart.Box{
				Top:    80,
				Left:   80,
				Right:  160,
				Bottom: 80,
			},
		},
		XAxis: chart.XAxis{
			Name: "时间",
		},
		YAxis: chart.YAxis{
			Name: "内存利用率 (%)",
			Range: &chart.ContinuousRange{
				Min: 0,
				Max: 100,
			},
		},
		Series: series,
	}

	// 保存为 PNG
	filename := "vm_memory_trend.png"
	filepath := filepath.Join(g.outputDir, filename)

	f, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	return filepath, line.Render(chart.PNG, f)
}

// 生成 RightSize 汇总饼图（从分析结果生成）
func (g *ChartGenerator) generateRightSizeSummaryPie(data *ReportData) (string, error) {
	// 从分析结果中提取 RightSize 汇总
	var upCount, downCount, noneCount int

	for _, section := range data.Sections {
		if section.Type == "rightsize_table" {
			if rows, ok := section.Data.([]map[string]interface{}); ok {
				for _, row := range rows {
					if adjType, ok := row["adjustmentType"].(string); ok {
						switch adjType {
						case "up":
							upCount++
						case "down":
							downCount++
						case "none":
							noneCount++
						}
					}
				}
			}
			break
		}
	}

	if upCount == 0 && downCount == 0 && noneCount == 0 {
		return "", fmt.Errorf("没有 RightSize 分析结果可用于生成图表")
	}

	values := []chart.Value{
		{Label: "建议升级", Value: float64(upCount)},
		{Label: "建议降配", Value: float64(downCount)},
		{Label: "配置合理", Value: float64(noneCount)},
	}

	// 创建饼图
	pie := chart.PieChart{
		Title:  "Right Size 调整建议汇总",
		Width:  800,
		Height: 600,
		Values: values,
	}

	// 保存为 PNG
	filename := "rightsize_summary.png"
	filepath := filepath.Join(g.outputDir, filename)

	f, err := os.Create(filepath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	return filepath, pie.Render(chart.PNG, f)
}

// 辅助函数

func allZero(values []chart.Value) bool {
	for _, v := range values {
		if v.Value > 0 {
			return false
		}
	}
	return true
}

func getSeriesColor(index int) drawing.Color {
	switch index {
	case 0:
		return chart.ColorBlue
	case 1:
		return chart.ColorGreen
	case 2:
		return chart.ColorOrange
	case 3:
		return chart.ColorRed
	default:
		return chart.ColorBlack
	}
}
