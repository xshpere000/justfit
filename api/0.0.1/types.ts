/**
 * JustFit Backend API 类型定义
 * Version: 0.0.1
 * 生成日期: 2026-02-09
 */

// ==================== 基础类型 ====================

export type EntityType = 'cluster' | 'host' | 'vm';
export type PlatformType = 'vcenter' | 'h3c-uis';
export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type TaskType = 'collection' | 'analysis' | 'report' | 'sync';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertType = 'zombie_vm' | 'overprovisioned' | 'underprovisioned' | 'health_risk';
export type ConnectionStatus = 'connected' | 'disconnected' | 'error';

// ==================== 连接管理 ====================

export interface ConnectionRequest {
  name: string;
  platform: PlatformType;
  host: string;
  port: number;
  username: string;
  password: string;
  insecure: boolean;
}

export interface Connection {
  ID: number;
  Name: string;
  Platform: PlatformType;
  Host: string;
  Port: number;
  Username: string;
  Insecure: boolean;
  Status: ConnectionStatus;
  LastSync?: string;
}

export interface ConnectionInfo {
  ID: number;
  Name: string;
  Platform: PlatformType;
  Host: string;
  Port: number;
  Username: string;
  Insecure: boolean;
  Status: ConnectionStatus;
  LastSync?: string;
}

export interface UpdateConnectionRequest {
  id: number;
  name: string;
  platform: PlatformType;
  host: string;
  port: number;
  username: string;
  password?: string;
  insecure: boolean;
}

export interface TestConnectionRequest {
  id: number;
  host: string;
  username: string;
  password: string;
  platform: PlatformType;
  insecure: boolean;
}

export interface TestConnectionResult {
  Success: boolean;
  Message: string;
  Version?: string;
  Product?: string;
  Latency?: number;
}

// ==================== 采集任务 ====================

export interface CollectionConfig {
  connection_id: number;
  data_types: string[];
  metrics_days: number;
}

export interface CollectionResult {
  Success: boolean;
  Message: string;
  Clusters: number;
  Hosts: number;
  VMs: number;
  Metrics: number;
  Duration: number;
}

export interface TaskInfo {
  ID: number;
  Type: TaskType;
  Name: string;
  Status: TaskStatus;
  Progress: number;
  Error?: string;
  CreatedAt: string;
  StartedAt?: string;
  CompletedAt?: string;
}

export interface TaskAnalysisFlags {
  zombie: boolean;
  rightsize: boolean;
  tidal: boolean;
  health: boolean;
}

export interface TaskDetail {
  ID: number;
  Type: TaskType;
  Name: string;
  Status: TaskStatus;
  Progress: number;
  Error?: string;
  CreatedAt: string;
  StartedAt?: string;
  CompletedAt?: string;
  ConnectionID: number;
  Platform: PlatformType | string;
  SelectedVMs: string[];
  TotalVMs: number;
  CollectedVMs: number;
  CurrentStep: string;
  AnalysisResults: TaskAnalysisFlags;
  Result?: Record<string, any>;
}

export interface ListTaskVMsRequest {
  task_id: number;
  limit?: number;
  offset?: number;
  keyword?: string;
}

export type ListTaskVMsResponse = [VMListItem[], number];

export interface GetTaskAnalysisResultRequest {
  task_id: number;
  analysis_type?: 'zombie_vm' | 'right_size' | 'tidal' | 'health_score';
}

export interface TaskLogEntry {
  Timestamp: string;
  Level: 'info' | 'warning' | 'error';
  Message: string;
}

// ==================== 资源查询 ====================

export interface ClusterListItem {
  ID: number;
  Name: string;
  Datacenter: string;
  TotalCPU: number;
  TotalMemoryGB: number;
  NumHosts: number;
  NumVMs: number;
  Status: string;
  CollectedAt: string;
}

export interface HostListItem {
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

export interface VMListItem {
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

export interface MetricPoint {
  Timestamp: number;
  Value: number;
}

export interface MetricsData {
  VMID: number;
  VMName: string;
  MetricType: string;
  StartTime: string;
  EndTime: string;
  Data: MetricPoint[];
}

export interface EntityDetail {
  Type: EntityType;
  ID: number;
  Name: string;
  Attributes: Record<string, any>;
}

// ==================== 分析服务 ====================

export interface ZombieVMConfig {
  analysis_days?: number;
  cpu_threshold?: number;
  memory_threshold?: number;
  min_confidence?: number;
}

export interface ZombieVMResult {
  VMName: string;
  Datacenter: string;
  Host: string;
  CPUCount: number;
  MemoryMB: number;
  CPUUsage: number;
  MemoryUsage: number;
  Confidence: number;
  DaysLowUsage: number;
  Evidence: string[];
  Recommendation: string;
}

export interface RightSizeConfig {
  analysis_days?: number;
  buffer_ratio?: number;
}

export interface RightSizeResult {
  VMName: string;
  Datacenter: string;
  CurrentCPU: number;
  CurrentMemoryMB: number;
  RecommendedCPU: number;
  RecommendedMemoryMB: number;
  AdjustmentType: 'none' | 'up' | 'down';
  RiskLevel: 'low' | 'medium' | 'high';
  EstimatedSaving: string;
  Confidence: number;
}

export interface TidalConfig {
  analysis_days?: number;
  min_stability?: number;
}

export interface TidalResult {
  VMName: string;
  Datacenter: string;
  Pattern: 'daily' | 'weekly' | 'none';
  StabilityScore: number;
  PeakHours: number[];
  PeakDays: number[];
  Recommendation: string;
  EstimatedSaving: string;
}

export interface HealthScoreResult {
  ConnectionID: number;
  ConnectionName: string;
  OverallScore: number;
  HealthLevel: 'excellent' | 'good' | 'fair' | 'poor';
  ResourceBalance: number;
  OvercommitRisk: number;
  HotspotConcentration: number;
  TotalClusters: number;
  TotalHosts: number;
  TotalVMs: number;
  RiskItems: string[];
  Recommendations: string[];
}

export interface AnalysisRequest {
  connection_id: number;
  analysis_types: string[];
  config: Record<string, any>;
}

export interface AnalysisResponse {
  Status: string;
  Results: Record<string, any>;
}

export interface AnalysisSummary {
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

// ==================== 报告服务 ====================

export interface ReportRequest {
  title: string;
  connection_id: number;
  report_types: string[];
}

export interface ReportResponse {
  Success: boolean;
  Message: string;
  Files: string[];
}

export interface ReportListItem {
  ID: number;
  Type: string;
  Name: string;
  ConnectionID: number;
  Status: string;
  Format: string;
  FilePath: string;
  FileSize: number;
  CreatedAt: string;
}

export interface ReportDetail {
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

export interface ReportSection {
  Title: string;
  Type: string;
  Content?: string;
  Data?: Record<string, any>;
}

export interface ExportReportRequest {
  report_id: number;
  format: string;
  output_dir?: string;
}

export interface ExportTaskReportRequest {
  task_id: number;
  format?: 'json' | 'html' | 'xlsx';
}

// ==================== 系统配置 ====================

export interface SystemSettings {
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
  theme: string;
  language: string;
  auto_refresh_interval: number;
}

// ==================== 告警服务 ====================

export interface AlertListItem {
  ID: number;
  TargetType: string;
  TargetKey: string;
  TargetName: string;
  AlertType: AlertType;
  Severity: AlertSeverity;
  Title: string;
  Message: string;
  Acknowledged: boolean;
  AcknowledgedAt?: string;
  CreatedAt: string;
}

export interface MarkAlertRequest {
  id: number;
  acknowledged: boolean;
}

export interface AlertStats {
  Total: number;
  Unacknowledged: number;
  BySeverity: Record<string, number>;
  ByType: Record<string, number>;
}

// ==================== 仪表盘 ====================

export interface DashboardStats {
  health_score: number;
  zombie_count: number;
  total_savings: string;
  total_vms: number;
}

// ==================== API 响应包装 ====================

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// ==================== 创建告警 ====================

export interface CreateAlertRequest {
  target_type: string;
  target_key: string;
  target_name: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  data?: string;
}
