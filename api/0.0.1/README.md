# JustFit Backend API Reference

**Version**: 0.0.1
**Last Updated**: 2026-02-12
**Protocol**: Wails IPC (Go Backend ↔ Frontend)

---

## 目录

- [连接管理](#连接管理)
- [采集任务](#采集任务)
- [资源查询](#资源查询)
- [分析服务](#分析服务)
- [报告服务](#报告服务)
- [系统配置](#系统配置)
- [告警服务](#告警服务)
- [仪表盘](#仪表盘)

---

## 连接管理

### CreateConnection

创建新的平台连接。

**方法**: `CreateConnection(req ConnectionRequest) (uint, error)`

**请求参数**:
```typescript
interface ConnectionRequest {
  name: string;        // 连接名称
  platform: string;    // 平台类型: "vcenter" | "h3c-uis"
  host: string;        // 主机地址
  port: number;        // 端口号 (vCenter默认443)
  username: string;    // 用户名
  password: string;    // 密码
  insecure: boolean;   // 是否跳过TLS验证
}
```

**返回参数**:
```typescript
type ConnectionID = number;  // 返回新创建的连接ID
```

**示例**:
```typescript
const connId = await CreateConnection({
  name: "生产环境vCenter",
  platform: "vcenter",
  host: "192.168.1.100",
  port: 443,
  username: "administrator@vsphere.local",
  password: "password123",
  insecure: true
});
```

---

### TestConnection

测试连接是否可用。

**方法**: `TestConnection(id uint, host string, username string, password string, platform string, insecure bool) (*TestConnectionResult, error)`

**请求参数**:
```typescript
interface TestConnectionRequest {
  id: number;         // 连接ID (用于更新现有连接状态)
  host: string;       // 主机地址
  username: string;   // 用户名
  password: string;   // 密码
  platform: string;   // 平台类型
  insecure: boolean;  // 是否跳过TLS验证
}
```

**返回参数**:
```typescript
interface TestConnectionResult {
  Success: boolean;   // 是否连接成功
  Message: string;    // 返回消息
  Version?: string;   // 服务器版本 (成功时)
  Product?: string;   // 产品名称 (成功时)
  Latency?: number;   // 连接延迟(毫秒) (成功时)
}
```

---

### ListConnections

获取所有连接列表。

**方法**: `ListConnections() ([]*Connection, error)`

**返回参数**:
```typescript
interface Connection {
  ID: number;
  Name: string;
  Platform: string;
  Host: string;
  Port: number;
  Username: string;
  Insecure: boolean;
  Status: string;           // "connected" | "disconnected" | "error"
  LastSync?: string;        // ISO 8601 格式时间
}
```

---

### GetConnection

获取单个连接详情。

**方法**: `GetConnection(id uint) (*ConnectionInfo, error)`

**请求参数**:
```typescript
interface GetConnectionRequest {
  id: number;  // 连接ID
}
```

**返回参数**:
```typescript
interface ConnectionInfo {
  ID: number;
  Name: string;
  Platform: string;
  Host: string;
  Port: number;
  Username: string;
  Insecure: boolean;
  Status: string;
  LastSync?: string;
}
```

---

### UpdateConnection

更新连接配置。

**方法**: `UpdateConnection(req UpdateConnectionRequest) error`

**请求参数**:
```typescript
interface UpdateConnectionRequest {
  id: number;
  name: string;
  platform: string;
  host: string;
  port: number;
  username: string;
  password?: string;  // 可选，为空则不更新密码
  insecure: boolean;
}
```

---

### DeleteConnection

删除连接。

**方法**: `DeleteConnection(id uint) error`

**请求参数**:
```typescript
interface DeleteConnectionRequest {
  id: number;
}
```

---

## 采集任务

### CreateCollectTask

创建数据采集任务。

**方法**: `CreateCollectTask(config CollectionConfig) (uint, error)`

**请求参数**:
```typescript
interface CollectionConfig {
  connection_id: number;
  data_types: string[];    // ["clusters", "hosts", "vms", "metrics"]
  metrics_days: number;    // 性能指标采集天数
}
```

**返回参数**:
```typescript
type TaskID = number;  // 返回任务ID
```

---

### ListTasks

获取任务列表。

**方法**: `ListTasks(status string, limit int, offset int) ([]TaskInfo, error)`

**请求参数**:
```typescript
interface ListTasksRequest {
  status?: string;  // "" | "pending" | "running" | "completed" | "failed"
  limit?: number;   // 默认10
  offset?: number;  // 默认0
}
```

**返回参数**:
```typescript
interface TaskInfo {
  ID: number;
  Type: string;        // "collection" | "analysis" | "report"
  Name: string;
  Status: string;      // "pending" | "running" | "completed" | "failed"
  Progress: number;    // 0-100
  Error?: string;
  CreatedAt: string;   // ISO 8601 格式
  StartedAt?: string;
  CompletedAt?: string;
}
```

---

### GetTask

获取任务详情。

**方法**: `GetTask(id uint) (*TaskInfo, error)`

---

### GetTaskDetail

获取任务详情（任务维度扩展字段）。

**方法**: `GetTaskDetail(taskID uint) (*TaskDetail, error)`

**返回参数**:
```typescript
interface TaskDetail {
  id: number;
  type: string;
  name: string;
  status: string;
  progress: number;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  connection_id: number;
  platform: string;
  selected_vms: string[];
  total_vms: number;
  collected_vms: number;
  current_step: string;
  analysis_results: {
    zombie: boolean;
    rightsize: boolean;
    tidal: boolean;
    health: boolean;
  };
  result?: Record<string, any>;
}
```

---

### ListTaskVMs

获取任务快照维度 VM 列表（避免使用连接当前态）。

**方法**: `ListTaskVMs(taskID uint, limit int, offset int, keyword string) ([]VMListItem, int, error)`

**请求参数**:
```typescript
interface ListTaskVMsRequest {
  task_id: number;
  limit?: number;
  offset?: number;
  keyword?: string;
}
```

**返回参数**:
```typescript
type ListTaskVMsResponse = [VMListItem[], number]; // [列表, 总数]
```

---

### GetTaskAnalysisResult

按任务维度获取分析结果。

**方法**: `GetTaskAnalysisResult(taskID uint, analysisType string) (interface{}, error)`

**请求参数**:
```typescript
interface GetTaskAnalysisResultRequest {
  task_id: number;
  analysis_type?: string; // zombie_vm | right_size | tidal | health_score；为空返回全部
}
```

---

### StopTask

停止任务。

**方法**: `StopTask(id uint) error`

---

### RetryTask

重试失败的任务（创建新任务）。

**方法**: `RetryTask(id uint) (uint, error)`

**返回参数**: 新任务ID

---

### GetTaskLogs

获取任务日志。

**方法**: `GetTaskLogs(id uint, limit int) ([]TaskLogEntry, error)`

**返回参数**:
```typescript
interface TaskLogEntry {
  Timestamp: string;  // ISO 8601 格式
  Level: string;      // "info" | "warning" | "error"
  Message: string;
}
```

---

## 资源查询

### ListClusters

获取集群列表。

**方法**: `ListClusters(connectionID uint) ([]ClusterListItem, error)`

**请求参数**:
```typescript
interface ListClustersRequest {
  connection_id: number;
}
```

**返回参数**:
```typescript
interface ClusterListItem {
  ID: number;
  Name: string;
  Datacenter: string;
  TotalCPU: number;        // MHz
  TotalMemoryGB: number;   // GB
  NumHosts: number;
  NumVMs: number;
  Status: string;
  CollectedAt: string;
}
```

---

### ListHosts

获取主机列表。

**方法**: `ListHosts(connectionID uint) ([]HostListItem, error)`

**返回参数**:
```typescript
interface HostListItem {
  ID: number;
  Name: string;
  Datacenter: string;
  IPAddress: string;
  CPUCores: number;
  CPUMHz: number;
  MemoryGB: number;
  NumVMs: number;
  PowerState: string;
  OverallStatus: string;
  CollectedAt: string;
}
```

---

### ListVMs

获取虚拟机列表。

**方法**: `ListVMs(connectionID uint) ([]VMListItem, error)`

**返回参数**:
```typescript
interface VMListItem {
  ID: number;
  Name: string;
  Datacenter: string;
  UUID: string;
  CPUCount: number;
  MemoryGB: number;
  PowerState: string;
  IPAddress: string;
  GuestOS: string;
  HostName: string;
  OverallStatus: string;
  CollectedAt: string;
}
```

---

### GetMetrics

获取虚拟机性能指标。

**方法**: `GetMetrics(vmID uint, metricType string, days int) (*MetricsData, error)`

**请求参数**:
```typescript
interface GetMetricsRequest {
  vm_id: number;
  metric_type: string;  // "cpu" | "memory" | "disk_read" | "disk_write" | "net_rx" | "net_tx"
  days: number;         // 查询天数
}
```

**返回参数**:
```typescript
interface MetricsData {
  VMID: number;
  VMName: string;
  MetricType: string;
  StartTime: string;
  EndTime: string;
  Data: MetricPoint[];
}

interface MetricPoint {
  Timestamp: number;  // Unix timestamp
  Value: number;
}
```

---

### GetEntityDetail

获取实体详情。

**方法**: `GetEntityDetail(entityType EntityType, id uint) (*EntityDetail, error)`

**请求参数**:
```typescript
type EntityType = "cluster" | "host" | "vm";

interface GetEntityDetailRequest {
  entity_type: EntityType;
  id: number;
}
```

**返回参数**:
```typescript
interface EntityDetail {
  Type: EntityType;
  ID: number;
  Name: string;
  Attributes: Record<string, any>;
}
```

---

## 分析服务

### DetectZombieVMs

僵尸虚拟机检测。

**方法**: `DetectZombieVMs(connectionID uint, config ZombieVMConfig) ([]ZombieVMResult, error)`

**请求参数**:
```typescript
interface ZombieVMConfig {
  analysis_days: number;     // 分析天数，默认7
  cpu_threshold: number;     // CPU阈值%，默认5
  memory_threshold: number;  // 内存阈值%，默认10
  min_confidence: number;    // 最小置信度，默认0.7
}
```

**返回参数**:
```typescript
interface ZombieVMResult {
  VMName: string;
  Datacenter: string;
  Host: string;
  CPUCount: number;
  MemoryMB: number;
  CPUUsage: number;
  MemoryUsage: number;
  Confidence: number;       // 0-1
  DaysLowUsage: number;
  Evidence: string[];
  Recommendation: string;
}
```

---

### AnalyzeRightSize

资源规格优化分析。

**方法**: `AnalyzeRightSize(connectionID uint, config RightSizeConfig) ([]RightSizeResult, error)`

**请求参数**:
```typescript
interface RightSizeConfig {
  analysis_days: number;  // 分析天数，默认7
  buffer_ratio: number;   // 缓冲比例，默认1.2
}
```

**返回参数**:
```typescript
interface RightSizeResult {
  VMName: string;
  Datacenter: string;
  CurrentCPU: number;
  CurrentMemoryMB: number;
  RecommendedCPU: number;
  RecommendedMemoryMB: number;
  AdjustmentType: string;  // "none" | "up" | "down"
  RiskLevel: string;       // "low" | "medium" | "high"
  EstimatedSaving: string;
  Confidence: number;
}
```

---

### DetectTidalPattern

潮汐模式检测。

**方法**: `DetectTidalPattern(connectionID uint, config TidalConfig) ([]TidalResult, error)`

**请求参数**:
```typescript
interface TidalConfig {
  analysis_days: number;  // 分析天数，默认30
  min_stability: number;  // 最小稳定性，默认0.8
}
```

**返回参数**:
```typescript
interface TidalResult {
  VMName: string;
  Datacenter: string;
  Pattern: string;          // "daily" | "weekly" | "none"
  StabilityScore: number;
  PeakHours: number[];
  PeakDays: number[];
  Recommendation: string;
  EstimatedSaving: string;
}
```

---

### AnalyzeHealthScore

健康度评分分析。

**方法**: `AnalyzeHealthScore(connectionID uint, config map[string]interface{}) (*HealthScoreResult, error)`

**返回参数**:
```typescript
interface HealthScoreResult {
  ConnectionID: number;
  ConnectionName: string;
  OverallScore: number;       // 0-100
  HealthLevel: string;        // "excellent" | "good" | "fair" | "poor"
  ResourceBalance: number;    // 0-100
  OvercommitRisk: number;     // 0-100
  HotspotConcentration: number; // 0-100
  TotalClusters: number;
  TotalHosts: number;
  TotalVMs: number;
  RiskItems: string[];
  Recommendations: string[];
}
```

---

### RunAnalysis

统一分析入口（同步执行）。

**方法**: `RunAnalysis(req AnalysisRequest) (*AnalysisResponse, error)`

**请求参数**:
```typescript
interface AnalysisRequest {
  connection_id: number;
  analysis_types: string[];  // ["zombie_vm", "right_size", "tidal", "health_score"]
  config: Record<string, any>;
}
```

**返回参数**:
```typescript
interface AnalysisResponse {
  Status: string;                        // "completed"
  Results: Record<string, any>;  // 各类型分析结果
}
```

---

### GetAnalysisResult

获取已保存的分析结果。

**方法**: `GetAnalysisResult(resultID uint) (map[string]interface{}, error)`

---

### GetAnalysisSummary

获取分析汇总。

**方法**: `GetAnalysisSummary(connectionID uint) (*AnalysisSummary, error)`

**返回参数**:
```typescript
interface AnalysisSummary {
  ConnectionID: number;
  TotalVMs: number;
  ZombieVMs: number;
  RightSizeVMs: number;
  TidalVMs: number;
  HealthScore: number;
  TotalSavings: string;
  LastAnalyzed: string;
  RiskDistribution: Record<string, number>;
}
```

---

## 报告服务

### GenerateReport

生成分析报告。

**方法**: `GenerateReport(req ReportRequest) (*ReportResponse, error)`

**请求参数**:
```typescript
interface ReportRequest {
  title: string;
  connection_id: number;
  report_types: string[];  // ["json", "html"]
}
```

**返回参数**:
```typescript
interface ReportResponse {
  Success: boolean;
  Message: string;
  Files: string[];  // 生成的文件路径
}
```

---

### ListReports

获取报告列表。

**方法**: `ListReports(limit int, offset int) ([]ReportListItem, error)`

**返回参数**:
```typescript
interface ReportListItem {
  ID: number;
  Type: string;
  Name: string;
  ConnectionID: number;
  Status: string;      // "pending" | "generating" | "completed" | "failed"
  Format: string;      // "json" | "html" | "pdf"
  FilePath: string;
  FileSize: number;
  CreatedAt: string;
}
```

---

### GetReport

获取报告详情。

**方法**: `GetReport(id uint) (*ReportDetail, error)`

**返回参数**:
```typescript
interface ReportDetail {
  ID: number;
  Type: string;
  Name: string;
  ConnectionID: number;
  Status: string;
  Format: string;
  FilePath: string;
  FileSize: number;
  CreatedAt: string;
  Sections?: ReportSection[];
}

interface ReportSection {
  Title: string;
  Type: string;
  Content?: string;
  Data?: Record<string, any>;
}
```

---

### ExportReport

导出报告。

**方法**: `ExportReport(req ExportReportRequest) (string, error)`

**请求参数**:
```typescript
interface ExportReportRequest {
  report_id: number;
  format: string;      // "json" | "html" | "xlsx"
  output_dir?: string; // 可选，默认临时目录
}
```

**返回参数**: 导出文件的完整路径

---

### ExportTaskReport

按任务维度导出报告。

**方法**: `ExportTaskReport(taskID uint, format string) (string, error)`

**请求参数**:
```typescript
interface ExportTaskReportRequest {
  task_id: number;
  format?: string; // "json" | "html" | "xlsx"，默认 json
}
```

**返回参数**: 导出文件的完整路径

---

## 系统配置

### GetSettings

获取系统配置。

**方法**: `GetSettings() (*SystemSettings, error)`

**返回参数**:
```typescript
interface SystemSettings {
  // 分析配置
  default_analysis_days: number;
  default_cpu_threshold: number;
  default_memory_threshold: number;
  default_buffer_ratio: number;

  // 采集配置
  default_metrics_days: number;
  collection_concurrency: number;

  // 报告配置
  default_report_format: string;
  report_output_dir: string;

  // 界面配置
  theme: string;            // "light" | "dark"
  language: string;         // "zh-CN" | "en-US"
  auto_refresh_interval: number;
}
```

---

### UpdateSettings

更新系统配置。

**方法**: `UpdateSettings(settings SystemSettings) error`

---

### ExportDiagnosticPackage

导出诊断包。

**方法**: `ExportDiagnosticPackage() (string, error)`

**返回参数**: 导出文件的完整路径

---

## 告警服务

### ListAlerts

获取告警列表。

**方法**: `ListAlerts(acknowledged *bool, limit int, offset int) ([]AlertListItem, error)`

**请求参数**:
```typescript
interface ListAlertsRequest {
  acknowledged?: boolean;  // 可选过滤
  limit?: number;         // 默认10
  offset?: number;        // 默认0
}
```

**返回参数**:
```typescript
interface AlertListItem {
  ID: number;
  TargetType: string;     // "cluster" | "host" | "vm"
  TargetKey: string;
  TargetName: string;
  AlertType: string;      // "zombie_vm" | "overprovisioned" | "underprovisioned" | "health_risk"
  Severity: string;       // "info" | "warning" | "critical"
  Title: string;
  Message: string;
  Acknowledged: boolean;
  AcknowledgedAt?: string;
  CreatedAt: string;
}
```

---

### MarkAlert

标记告警（确认/取消确认）。

**方法**: `MarkAlert(req MarkAlertRequest) error`

**请求参数**:
```typescript
interface MarkAlertRequest {
  id: number;
  acknowledged: boolean;
}
```

---

### GetAlertStats

获取告警统计。

**方法**: `GetAlertStats() (*AlertStats, error)`

**返回参数**:
```typescript
interface AlertStats {
  Total: number;
  Unacknowledged: number;
  BySeverity: Record<string, number>;
  ByType: Record<string, number>;
}
```

---

## 仪表盘

### GetDashboardStats

获取仪表盘统计数据。

**方法**: `GetDashboardStats() (*DashboardStats, error)`

**返回参数**:
```typescript
interface DashboardStats {
  health_score: number;   // 0-100
  zombie_count: number;
  total_savings: string;  // 如 "¥12,400/月"
  total_vms: number;
}
```

---

## 错误处理

所有 API 方法在发生错误时返回错误信息，前端应做如下处理：

```typescript
try {
  const result = await apiMethod(params);
} catch (error) {
  // error.message 包含错误描述
  console.error('API Error:', error.message);
  // 显示错误提示给用户
}
```

---

## 类型定义

所有 TypeScript 类型定义可从前端生成或参考此文档实现。

建议在前端创建 `types/api.ts` 文件，导出所有接口定义。
