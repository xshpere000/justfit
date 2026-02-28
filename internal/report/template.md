# {{.Title}}

**生成时间**: {{.GeneratedAt.Format "2006-01-02 15:04:05"}}
**平台**: {{.Platform}}
**连接名称**: {{.ConnectionName}}

---

## 执行摘要

本报告基于云平台资源采集数据，对虚拟化环境的资源使用情况进行了全面评估，包括僵尸虚拟机检测、资源配置合理性分析、潮汐模式识别和平台健康评分。

### 关键指标

| 指标 | 数值 |
|------|------|
| 集群数量 | {{.ClusterCount}} |
| 主机数量 | {{.HostCount}} |
| 虚拟机数量 | {{.VMCount}} |
| 数据采集天数 | {{.MetricsDays}} 天 |

---

## 1. 集群信息

{{range .Clusters}}
### {{.Name}}

- **数据中心**: {{.Datacenter}}
- **CPU 总量**: {{.TotalCpu}} MHz
- **内存总量**: {{formatMemory .TotalMemory}}
- **主机数量**: {{.NumHosts}}
- **虚拟机数量**: {{.NumVMs}}
- **状态**: {{.Status}}

{{end}}

---

## 2. 主机信息

{{range .Hosts}}
### {{.Name}}

- **数据中心**: {{.Datacenter}}
- **IP 地址**: {{.IPAddress}}
- **CPU 核心数**: {{.CpuCores}}
- **CPU 频率**: {{.CpuMhz}} MHz
- **内存总量**: {{formatMemory .Memory}}
- **虚拟机数量**: {{.NumVMs}}
- **电源状态**: {{.PowerState}}
- **整体状态**: {{.OverallStatus}}

{{end}}

---

## 3. 虚拟机列表

| 名称 | 数据中心 | CPU | 内存 | 电源状态 | 主机 | 整体状态 |
|------|----------|-----|------|----------|------|----------|
{{range .VMs}}
| {{.Name}} | {{.Datacenter}} | {{.CpuCount}} 核 | {{formatMemory .MemoryMB}} | {{.PowerState}} | {{.HostName}} | {{.OverallStatus}} |
{{end}}

---

## 4. 分析结果

### 4.1 僵尸虚拟机检测

{{if .ZombieVMs}}
检测到 **{{len .ZombieVMs}}** 个可能为僵尸的虚拟机：

| 虚拟机 | 数据中心 | CPU 使用率 | 内存使用率 | 磁盘 I/O | 网络流量 | 置信度 | 建议 |
|--------|----------|-----------|-----------|---------|----------|-------|------|
{{range .ZombieVMs}}
| {{.VMName}} | {{.Datacenter}} | {{.CPUUsage}}% | {{.MemoryUsage}}% | {{.DiskIO}}% | {{.Network}}% | {{.Confidence}}% | {{.Recommendation}} |
{{end}}
{{else}}
未检测到僵尸虚拟机。
{{end}}

### 4.2 资源配置分析 (Right Size)

{{if .RightSizeResults}}
分析了 **{{len .RightSizeResults}}** 个虚拟机的资源配置：

| 虚拟机 | 数据中心 | 当前配置 | 建议配置 | 调整类型 | 风险等级 | 预计节省 |
|--------|----------|----------|----------|----------|----------|----------|
{{range .RightSizeResults}}
| {{.VMName}} | {{.Datacenter}} | CPU: {{.CurrentCPU}}核 / 内存: {{formatMemory .CurrentMemory}} | CPU: {{.SuggestedCPU}}核 / 内存: {{formatMemory .SuggestedMemory}} | {{.AdjustmentType}} | {{.RiskLevel}} | {{.EstimatedSaving}} |
{{end}}
{{else}}
未进行资源配置分析。
{{end}}

### 4.3 潮汐模式检测

{{if .TidalResults}}
检测到 **{{len .TidalResults}}** 个虚拟机存在潮汐模式：

| 虚拟机 | 数据中心 | 模式类型 | 稳定性 | 峰值时段 | 谷值时段 | 建议 |
|--------|----------|----------|--------|----------|----------|------|
{{range .TidalResults}}
| {{.VMName}} | {{.Datacenter}} | {{.PatternType}} | {{.StabilityScore}}% | {{.PeakHours}} | {{.ValleyHours}} | {{.Recommendation}} |
{{end}}
{{else}}
未检测到潮汐模式。
{{end}}

### 4.4 平台健康评分

{{if .HealthScore}}
| 评估维度 | 得分 | 等级 |
|----------|------|------|
| 资源均衡度 | {{.HealthScore.ResourceBalance}}% | {{.HealthScore.HealthLevel}} |
| 超配风险 | {{.HealthScore.OvercommitRisk}}% | - |
| 热点集中度 | {{.HealthScore.HotspotConcentration}}% | - |
| **综合评分** | **{{.HealthScore.OverallScore}}%** | **{{.HealthScore.HealthLevel}}** |

**评分说明**：
- 90-100 分: 优秀 (excellent)
- 75-89 分: 良好 (good)
- 60-74 分: 一般 (fair)
- 0-59 分: 较差 (poor)
{{else}}
未进行平台健康评分。
{{end}}

---

## 5. 图表分析

{{range .Charts}}
### {{.Title}}

![{{.Title}}]({{.Path}})

{{.Description}}

{{end}}

---

*报告生成于 {{.GeneratedAt.Format "2006-01-02 15:04:05"}}*
