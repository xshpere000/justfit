package report

import (
	"encoding/json"
	"fmt"
	"time"
)

// ReportBuilder 报告数据构建器
type ReportBuilder struct {
	dataSource DataSource
}

// DataSource 数据源接口（与存储层解耦）
type DataSource interface {
	GetClusters() ([]ClusterInfo, error)
	GetHosts() ([]HostInfo, error)
	GetVMs() ([]VMInfo, error)
	GetAnalysisFindings(jobType string) ([]AnalysisFinding, error)
	GetTaskInfo() (*TaskInfo, error)
}

// 数据模型定义（与 storage 层解耦，保持平台无关）

type ClusterInfo struct {
	Name        string    `json:"name"`
	Datacenter  string    `json:"datacenter"`
	TotalCpu    int64     `json:"totalCpu"`
	TotalMemory int64     `json:"totalMemory"`
	NumHosts    int32     `json:"numHosts"`
	NumVMs      int       `json:"numVMs"`
	Status      string    `json:"status"`
	CollectedAt time.Time `json:"collectedAt"`
}

type HostInfo struct {
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	IPAddress     string    `json:"ipAddress"`
	CpuCores      int32     `json:"cpuCores"`
	CpuMhz        int32     `json:"cpuMhz"`
	Memory        int64     `json:"memory"`
	NumVMs        int       `json:"numVMs"`
	PowerState    string    `json:"powerState"`
	OverallStatus string    `json:"overallStatus"`
	CollectedAt   time.Time `json:"collectedAt"`
}

type VMInfo struct {
	Name          string    `json:"name"`
	Datacenter    string    `json:"datacenter"`
	CpuCount      int32     `json:"cpuCount"`
	MemoryMB      int32     `json:"memoryMb"`
	PowerState    string    `json:"powerState"`
	GuestOS       string    `json:"guestOs"`
	HostName      string    `json:"hostName"`
	HostIP        string    `json:"hostIp"`
	OverallStatus string    `json:"overallStatus"`
	CollectedAt   time.Time `json:"collectedAt"`
}

// VMMetricData VM指标数据（用于图表）
type VMMetricData struct {
	VMName     string        `json:"vmName"`
	MetricType string        `json:"metricType"`
	Metrics    []MetricPoint `json:"metrics"`
}

type MetricPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type AnalysisFinding struct {
	JobType     string `json:"jobType"` // zombie, rightsize, tidal, health
	TargetName  string `json:"targetName"`
	Severity    string `json:"severity"` // critical, warning, info
	Title       string `json:"title"`
	Description string `json:"description"`
	Action      string `json:"action"`
	Reason      string `json:"reason"`
	SavingCost  string `json:"savingCost"`
	Details     string `json:"details"` // JSON格式的详细数据
}

type TaskInfo struct {
	Name           string    `json:"name"`
	ConnectionName string    `json:"connectionName"`
	Platform       string    `json:"platform"`
	StartedAt      time.Time `json:"startedAt"`
	CompletedAt    time.Time `json:"completedAt"`
	MetricsDays    int       `json:"metricsDays"`
}

// NewReportBuilder 创建报告构建器
func NewReportBuilder(ds DataSource) *ReportBuilder {
	return &ReportBuilder{
		dataSource: ds,
	}
}

// BuildReportData 构建完整的报告数据
func (b *ReportBuilder) BuildReportData() (*ReportData, error) {
	taskInfo, err := b.dataSource.GetTaskInfo()
	if err != nil {
		return nil, fmt.Errorf("获取任务信息失败: %w", err)
	}

	// 并行获取各类数据
	var (
		clusters []ClusterInfo
		hosts    []HostInfo
		vms      []VMInfo
		findings map[string][]AnalysisFinding
		errCh    = make(chan error, 4)
	)

	go func() {
		var err error
		clusters, err = b.dataSource.GetClusters()
		if err != nil {
			// 日志：集群数据获取失败，但不中断报告生成
			// 继续使用空数据
		}
		errCh <- err
	}()

	go func() {
		var err error
		hosts, err = b.dataSource.GetHosts()
		if err != nil {
			// 主机数据获取失败，继续使用空数据
		}
		errCh <- err
	}()

	go func() {
		var err error
		vms, err = b.dataSource.GetVMs()
		if err != nil {
			// VM数据获取失败，继续使用空数据
		}
		errCh <- err
	}()

	go func() {
		var err error
		findings, err = b.getAllFindings()
		if err != nil {
			// 分析结果获取失败，继续使用空数据
		}
		errCh <- err
	}()

	// 收集所有错误（但不中断流程）
	var errors []error
	for i := 0; i < 4; i++ {
		if err := <-errCh; err != nil {
			errors = append(errors, err)
		}
	}

	// 构建报告数据（即使部分数据为空）
	reportData := &ReportData{
		Title:        fmt.Sprintf("%s - 资源评估报告", taskInfo.Name),
		GeneratedAt:  time.Now(),
		ConnectionID: 0, // 从 taskInfo 获取
		Metadata: map[string]interface{}{
			"taskName":       taskInfo.Name,
			"connectionName": taskInfo.ConnectionName,
			"platform":       taskInfo.Platform,
			"metricsDays":    taskInfo.MetricsDays,
			"startedAt":      taskInfo.StartedAt,
			"completedAt":    taskInfo.CompletedAt,
			"dataWarnings":   errors, // 记录数据获取警告
		},
		Sections: b.buildSections(clusters, hosts, vms, findings),
	}

	return reportData, nil
}

// buildSections 构建报告章节
func (b *ReportBuilder) buildSections(
	clusters []ClusterInfo,
	hosts []HostInfo,
	vms []VMInfo,
	findings map[string][]AnalysisFinding,
) []ReportSection {

	sections := []ReportSection{}

	// 1. 概览统计
	sections = append(sections, ReportSection{
		Type:  "summary",
		Title: "资源概览",
		Data: map[string]interface{}{
			"clusterCount": len(clusters),
			"hostCount":    len(hosts),
			"vmCount":      len(vms),
			"totalCpu":     calculateTotalCPU(hosts),
			"totalMemory":  calculateTotalMemory(hosts),
		},
	})

	// 2. 集群信息表格
	sections = append(sections, ReportSection{
		Type:  "cluster_table",
		Title: "集群信息",
		Data:  convertClustersToTable(clusters),
	})

	// 3. 主机信息表格
	sections = append(sections, ReportSection{
		Type:  "host_table",
		Title: "主机信息",
		Data:  convertHostsToTable(hosts),
	})

	// 4. 虚拟机信息表格
	sections = append(sections, ReportSection{
		Type:  "vm_table",
		Title: "虚拟机列表",
		Data:  convertVMsToTable(vms),
	})

	// 5. 分析结果章节 - 使用专门的转换函数
	if zombie, ok := findings["zombie"]; ok && len(zombie) > 0 {
		sections = append(sections, ReportSection{
			Type:  "zombie_table",
			Title: "僵尸VM检测",
			Data:  convertZombieFindingsToTable(zombie),
		})
	}

	if rightsize, ok := findings["rightsize"]; ok && len(rightsize) > 0 {
		sections = append(sections, ReportSection{
			Type:  "rightsize_table",
			Title: "RightSize分析",
			Data:  convertRightSizeFindingsToTable(rightsize),
		})
	}

	if tidal, ok := findings["tidal"]; ok && len(tidal) > 0 {
		sections = append(sections, ReportSection{
			Type:  "tidal_table",
			Title: "潮汐模式检测",
			Data:  convertTidalFindingsToTable(tidal),
		})
	}

	if health, ok := findings["health"]; ok && len(health) > 0 {
		sections = append(sections, buildHealthSection(health))
		sections = append(sections, buildRiskListSection(health))
		sections = append(sections, buildRecommendationListSection(health))
	}

	return sections
}

// getAllFindings 获取所有分析结果
func (b *ReportBuilder) getAllFindings() (map[string][]AnalysisFinding, error) {
	jobTypes := []string{"zombie", "rightsize", "tidal", "health"}
	result := make(map[string][]AnalysisFinding)

	for _, jobType := range jobTypes {
		findings, err := b.dataSource.GetAnalysisFindings(jobType)
		if err != nil {
			return nil, fmt.Errorf("获取 %s 分析结果失败: %w", jobType, err)
		}
		result[jobType] = findings
	}

	return result, nil
}

// 辅助函数

func calculateTotalCPU(hosts []HostInfo) int64 {
	var total int64
	for _, h := range hosts {
		total += int64(h.CpuCores) * int64(h.CpuMhz)
	}
	return total
}

func calculateTotalMemory(hosts []HostInfo) int64 {
	var total int64
	for _, h := range hosts {
		total += h.Memory
	}
	return total
}

func convertClustersToTable(clusters []ClusterInfo) []map[string]interface{} {
	rows := make([]map[string]interface{}, len(clusters))
	for i, c := range clusters {
		rows[i] = map[string]interface{}{
			"name":        c.Name,
			"datacenter":  c.Datacenter,
			"totalCpu":    c.TotalCpu,
			"totalMemory": c.TotalMemory / 1024 / 1024 / 1024, // 转换为 GB
			"numHosts":    c.NumHosts,
			"numVMs":      c.NumVMs,
			"status":      c.Status,
		}
	}
	return rows
}

func convertHostsToTable(hosts []HostInfo) []map[string]interface{} {
	rows := make([]map[string]interface{}, len(hosts))
	for i, h := range hosts {
		rows[i] = map[string]interface{}{
			"name":          h.Name,
			"datacenter":    h.Datacenter,
			"ipAddress":     h.IPAddress,
			"cpuCores":      h.CpuCores,
			"cpuMhz":        h.CpuMhz,
			"memory":        h.Memory / 1024 / 1024 / 1024, // 转换为 GB
			"numVMs":        h.NumVMs,
			"powerState":    h.PowerState,
			"overallStatus": h.OverallStatus,
		}
	}
	return rows
}

func convertVMsToTable(vms []VMInfo) []map[string]interface{} {
	rows := make([]map[string]interface{}, len(vms))
	for i, v := range vms {
		rows[i] = map[string]interface{}{
			"name":          v.Name,
			"datacenter":    v.Datacenter,
			"cpuCount":      v.CpuCount,
			"memoryMb":      v.MemoryMB,
			"memoryGb":      float64(v.MemoryMB) / 1024,
			"powerState":    v.PowerState,
			"guestOs":       v.GuestOS,
			"hostIp":        v.HostIP,
			"overallStatus": v.OverallStatus,
		}
	}
	return rows
}

func convertFindingsToTable(findings []AnalysisFinding) []map[string]interface{} {
	rows := make([]map[string]interface{}, len(findings))
	for i, f := range findings {
		rows[i] = map[string]interface{}{
			"targetName":  f.TargetName,
			"severity":    f.Severity,
			"title":       f.Title,
			"description": f.Description,
			"action":      f.Action,
			"reason":      f.Reason,
			"savingCost":  f.SavingCost,
		}
	}
	return rows
}

// zombieVMResultDetail 僵尸VM结果详情（从 Details JSON 解析）
type zombieVMResultDetail struct {
	VMName         string  `json:"vmName"`
	VMKey          string  `json:"vmKey"`
	Datacenter     string  `json:"datacenter"`
	Host           string  `json:"host"`
	HostIP         string  `json:"hostIp"`
	CPUCount       int32   `json:"cpuCount"`
	MemoryMB       int32   `json:"memoryMb"`
	CPUUsage       float64 `json:"cpuUsage"`
	MemoryUsage    float64 `json:"memoryUsage"`
	Confidence     float64 `json:"confidence"`
	DaysLowUsage   int     `json:"daysLowUsage"`
	Recommendation string  `json:"recommendation"`
}

// convertZombieFindingsToTable 将僵尸VM分析结果转换为表格数据
func convertZombieFindingsToTable(findings []AnalysisFinding) []map[string]interface{} {
	rows := make([]map[string]interface{}, 0, len(findings))
	for _, f := range findings {
		// 解析 Details JSON
		if f.Details == "" {
			continue
		}
		var detail zombieVMResultDetail
		if err := json.Unmarshal([]byte(f.Details), &detail); err != nil {
			continue
		}
		rows = append(rows, map[string]interface{}{
			"vmName":         detail.VMName,
			"cluster":        detail.Datacenter, // 使用 Datacenter 而非 Cluster
			"hostIp":         detail.HostIP,
			"cpuCores":       detail.CPUCount,
			"memoryGb":       float64(detail.MemoryMB) / 1024,
			"cpuUsage":       fmt.Sprintf("%.1f%%", detail.CPUUsage),
			"memoryUsage":    fmt.Sprintf("%.1f%%", detail.MemoryUsage),
			"confidence":     detail.Confidence,
			"recommendation": detail.Recommendation,
		})
	}
	return rows
}

// rightSizeResultDetail RightSize结果详情（从 Details JSON 解析）
type rightSizeResultDetail struct {
	VMName              string  `json:"vmName"`
	VMKey               string  `json:"vmKey"`
	Datacenter          string  `json:"datacenter"`
	CurrentCPU          int32   `json:"currentCpu"`
	RecommendedCPU      int32   `json:"recommendedCpu"`
	CurrentMemoryMB     int32   `json:"currentMemoryMb"`
	RecommendedMemoryMB int32   `json:"recommendedMemoryMb"`
	AdjustmentType      string  `json:"adjustmentType"`
	RiskLevel           string  `json:"riskLevel"`
	Confidence          float64 `json:"confidence"`
	EstimatedSaving     string  `json:"estimatedSaving"`
}

// convertRightSizeFindingsToTable 将RightSize分析结果转换为表格数据
func convertRightSizeFindingsToTable(findings []AnalysisFinding) []map[string]interface{} {
	rows := make([]map[string]interface{}, 0, len(findings))
	for _, f := range findings {
		// 解析 Details JSON
		if f.Details == "" {
			continue
		}
		var detail rightSizeResultDetail
		if err := json.Unmarshal([]byte(f.Details), &detail); err != nil {
			continue
		}
		rows = append(rows, map[string]interface{}{
			"vmName":          detail.VMName,
			"cluster":         detail.Datacenter, // 使用 Datacenter 而非 Cluster
			"currentCPU":      detail.CurrentCPU,
			"suggestedCPU":    detail.RecommendedCPU,
			"currentMemory":   float64(detail.CurrentMemoryMB) / 1024,
			"suggestedMemory": float64(detail.RecommendedMemoryMB) / 1024,
			"adjustmentType":  detail.AdjustmentType,
			"riskLevel":       detail.RiskLevel,
			"confidence":      detail.Confidence,
			"recommendation":  f.Action,
		})
	}
	return rows
}

// tidalResultDetail 潮汐检测结果详情（从 Details JSON 解析）
type tidalResultDetail struct {
	VMName         string  `json:"vmName"`
	VMKey          string  `json:"vmKey"`
	Datacenter     string  `json:"datacenter"`
	Host           string  `json:"host"`
	Pattern        string  `json:"pattern"` // 模式类型: weekly, daily, none
	StabilityScore float64 `json:"stabilityScore"`
	PeakHours      []int   `json:"peakHours"` // 高峰时段 (0-23)
	PeakDays       []int   `json:"peakDays"`  // 高峰日期 (0-6, 0=周日)
	Recommendation string  `json:"recommendation"`
}

// convertTidalFindingsToTable 将潮汐检测分析结果转换为表格数据
func convertTidalFindingsToTable(findings []AnalysisFinding) []map[string]interface{} {
	rows := make([]map[string]interface{}, 0, len(findings))
	for _, f := range findings {
		// 解析 Details JSON
		if f.Details == "" {
			continue
		}
		var detail tidalResultDetail
		if err := json.Unmarshal([]byte(f.Details), &detail); err != nil {
			continue
		}
		// 格式化高峰时段
		peakHoursStr := ""
		if len(detail.PeakHours) > 0 {
			peakHoursStr = fmt.Sprintf("%v", detail.PeakHours)
		} else {
			peakHoursStr = "无"
		}
		// 格式化高峰日期
		peakDaysStr := ""
		if len(detail.PeakDays) > 0 {
			dayNames := []string{"周日", "周一", "周二", "周三", "周四", "周五", "周六"}
			days := make([]string, len(detail.PeakDays))
			for i, d := range detail.PeakDays {
				if d >= 0 && d < len(dayNames) {
					days[i] = dayNames[d]
				} else {
					days[i] = fmt.Sprintf("%d", d)
				}
			}
			peakDaysStr = fmt.Sprintf("%v", days)
		} else {
			peakDaysStr = "无"
		}
		rows = append(rows, map[string]interface{}{
			"vmName":         detail.VMName,
			"cluster":        detail.Datacenter, // 使用 Datacenter 而非 Cluster
			"patternType":    detail.Pattern,
			"stabilityScore": fmt.Sprintf("%.0f%%", detail.StabilityScore),
			"peakHours":      peakHoursStr,
			"peakDays":       peakDaysStr,
			"recommendation": detail.Recommendation,
		})
	}
	return rows
}

func buildHealthSection(findings []AnalysisFinding) ReportSection {
	// 提取健康评分和风险项
	var score float64
	var healthLevel string
	var resourceBalance float64
	var overcommitRisk float64
	var risks []string
	var recommendations []string
	var clusterCount, hostCount, vmCount int

	for _, f := range findings {
		if f.JobType == "health" && f.Details != "" {
			// 解析 Details JSON 获取健康评分详情
			var detail map[string]interface{}
			if err := json.Unmarshal([]byte(f.Details), &detail); err == nil {
				if s, ok := detail["overallScore"].(float64); ok {
					score = s
				}
				if h, ok := detail["healthLevel"].(string); ok {
					healthLevel = h
				}
				if rb, ok := detail["resourceBalance"].(float64); ok {
					resourceBalance = rb
				}
				if or, ok := detail["overcommitRisk"].(float64); ok {
					overcommitRisk = or
				}
				if cc, ok := detail["clusterCount"].(float64); ok {
					clusterCount = int(cc)
				}
				if hc, ok := detail["hostCount"].(float64); ok {
					hostCount = int(hc)
				}
				if vc, ok := detail["vmCount"].(float64); ok {
					vmCount = int(vc)
				}
				if ri, ok := detail["riskItems"].([]interface{}); ok {
					for _, r := range ri {
						if riskStr, ok := r.(string); ok {
							risks = append(risks, riskStr)
						}
					}
				}
				if rec, ok := detail["recommendations"].([]interface{}); ok {
					for _, r := range rec {
						if recStr, ok := r.(string); ok {
							recommendations = append(recommendations, recStr)
						}
					}
				}
			}
		}
		// 也从 Title 中提取风险项
		if f.Title != "" {
			risks = append(risks, f.Title)
		}
		if f.Action != "" {
			recommendations = append(recommendations, f.Action)
		}
	}

	// 构建多个 section 以支持 Excel 的不同部分
	return ReportSection{
		Type:  "health_summary",
		Title: "健康评分",
		Data: map[string]interface{}{
			"overallScore":    score,
			"healthLevel":     healthLevel,
			"resourceBalance": resourceBalance,
			"overcommitRisk":  overcommitRisk,
			"clusterCount":    clusterCount,
			"hostCount":       hostCount,
			"vmCount":         vmCount,
		},
	}
}

// buildRiskListSection 构建风险列表 section
func buildRiskListSection(findings []AnalysisFinding) ReportSection {
	var risks []string
	for _, f := range findings {
		if f.Details != "" {
			var detail map[string]interface{}
			if err := json.Unmarshal([]byte(f.Details), &detail); err == nil {
				if ri, ok := detail["riskItems"].([]interface{}); ok {
					for _, r := range ri {
						if riskStr, ok := r.(string); ok {
							risks = append(risks, riskStr)
						}
					}
				}
			}
		}
		risks = append(risks, f.Title)
	}
	return ReportSection{
		Type:  "risk_list",
		Title: "风险项",
		Data:  risks,
	}
}

// buildRecommendationListSection 构建建议列表 section
func buildRecommendationListSection(findings []AnalysisFinding) ReportSection {
	var recommendations []string
	for _, f := range findings {
		if f.Details != "" {
			var detail map[string]interface{}
			if err := json.Unmarshal([]byte(f.Details), &detail); err == nil {
				if rec, ok := detail["recommendations"].([]interface{}); ok {
					for _, r := range rec {
						if recStr, ok := r.(string); ok {
							recommendations = append(recommendations, recStr)
						}
					}
				}
			}
		}
		if f.Action != "" {
			recommendations = append(recommendations, f.Action)
		}
	}
	return ReportSection{
		Type:  "recommendation_list",
		Title: "改进建议",
		Data:  recommendations,
	}
}
