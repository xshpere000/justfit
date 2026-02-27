/**
 * JustFit Backend API 类型定义
 * Version: 0.0.2
 * 更新日期: 2026-02-25
 * 命名规范: 统一使用驼峰命名
 */

// ==================== 基础类型 ====================

export type entityType = 'cluster' | 'host' | 'vm';
export type PlatformType = 'vcenter' | 'h3c-uis';
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';
export type TaskType = 'collection' | 'analysis' | 'report';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type alertType = 'zombieVM' | 'overprovisioned' | 'underprovisioned' | 'healthRisk';
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
  id: number;
  name: string;
  platform: PlatformType;
  host: string;
  port: number;
  username: string;
  insecure: boolean;
  status: ConnectionStatus;
  lastSync?: string;
}

export interface ConnectionInfo {
  id: number;
  name: string;
  platform: PlatformType;
  host: string;
  port: number;
  username: string;
  insecure: boolean;
  status: ConnectionStatus;
  lastSync?: string;
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
  success: boolean;
  message: string;
  version?: string;
  product?: string;
  latency?: number;
}

// ==================== 采集任务 ====================

export interface CollectionConfig {
  name: string;              // 任务名称
  connectionId: number;
  connectionName: string;    // 连接名称
  platform: string;          // 平台类型: vcenter, h3c-uis
  dataTypes: string[];       // clusters, hosts, vms, metrics
  metricsDays: number;
  vmCount: number;          // 虚拟机总数
  selectedVMs: string[];     // 用户选择的虚拟机列表（vmKey 格式）
}

export interface CollectionResult {
  success: boolean;
  message: string;
  clusters: number;
  hosts: number;
  vms: number;
  metrics: number;
  duration: number;
}

export interface TaskInfo {
  id: number;
  type: string;              // 任务类型
  name: string;
  status: string;            // 任务状态
  progress: number;          // 进度 (0-100)
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  // 任务关联信息（扩展字段）
  connectionId?: number;     // 关联的连接ID
  connectionName?: string;   // 连接名称
  host?: string;             // 主机名
  platform?: string;         // 平台类型: vcenter, h3c-uis
  selectedVMs?: string[];    // 选中的VM列表
  vmCount?: number;          // 虚拟机总数
  collectedVMCount?: number; // 已采集的VM数量
  currentStep?: string;      // 当前执行步骤
  analysisResults?: Record<string, boolean>;  // 分析结果状态
}

export interface TaskLogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
}

// ==================== 资源查询 ====================

export interface ClusterListItem {
  id: number;
  name: string;
  datacenter: string;
  totalCpu: number;
  totalMemoryGB: number;
  numHosts: number;
  numVMs: number;
  status: string;
  collectedAt: string;
}

export interface HostListItem {
  id: number;
  name: string;
  datacenter: string;
  ipAddress: string;
  cpuCores: number;
  cpuMhz: number;
  memoryGb: number;
  numVMs: number;
  powerState: string;
  overallStatus: string;
  collectedAt: string;
}

export interface VMListItem {
  id: number;
  name: string;
  datacenter: string;
  uuid: string;
  cpuCount: number;
  memoryGb: number;
  powerState: string;
  connectionState: string;
  ipAddress: string;
  guestOs: string;
  hostName: string;
  overallStatus: string;
  collectedAt: string;
}

export interface MetricPoint {
  timestamp: number;
  Value: number;
}

export interface MetricsData {
  vmId: number;
  vmName: string;
  metricType: string;
  startTime: string;
  endTime: string;
  data: MetricPoint[];
}

export interface EntityDetail {
  type: entityType;
  id: number;
  name: string;
  attributes: Record<string, any>;
}

// ==================== 分析服务 ====================

export interface ZombieVMConfig {
  analysisDays?: number;
  cpuThreshold?: number;
  memoryThreshold?: number;
  minConfidence?: number;
}

export interface ZombieVMResult {
  vmName: string;
  datacenter: string;
  host: string;
  cpuCount: number;
  memoryMb: number;
  cpuUsage: number;
  memoryUsage: number;
  confidence: number;
  daysLowUsage: number;
  evidence: string[];
  recommendation: string;
}

export interface RightSizeConfig {
  analysisDays?: number;
  bufferRatio?: number;
}

export interface RightSizeResult {
  vmName: string;
  datacenter: string;
  currentCpu: number;
  currentMemoryMb: number;
  recommendedCpu: number;
  recommendedMemoryMb: number;
  adjustmentType: 'none' | 'up' | 'down';
  riskLevel: 'low' | 'medium' | 'high';
  estimatedSaving: string;
  confidence: number;
}

export interface TidalConfig {
  analysisDays?: number;
  minStability?: number;
}

export interface TidalResult {
  vmName: string;
  datacenter: string;
  pattern: 'daily' | 'weekly' | 'none';
  stabilityScore: number;
  peakHours: number[];
  peakDays: number[];
  recommendation: string;
  estimatedSaving: string;
}

export interface HealthScoreResult {
  connectionId: number;
  connectionName: string;
  overallScore: number;
  healthLevel: 'excellent' | 'good' | 'fair' | 'poor';
  resourceBalance: number;
  overcommitRisk: number;
  hotspotConcentration: number;
  clusterCount: number;
  hostCount: number;
  vmCount: number;
  riskItems: string[];
  recommendations: string[];
}

export interface AnalysisRequest {
  connectionId: number;
  analysisTypes: string[];
  config: Record<string, any>;
}

export interface AnalysisResponse {
  status: string;
  Results: Record<string, any>;
}

export interface AnalysisSummary {
  connectionId: number;
  vmCount: number;
  zombieVMs: number;
  rightSizeVMs: number;
  tidalVMs: number;
  healthScore: number;
  totalSavings: string;
  lastAnalyzed: string;
  riskDistribution: Record<string, number>;
}

// ==================== 报告服务 ====================

export interface ReportRequest {
  title: string;
  connectionId: number;
  reportTypes: string[];
}

export interface ReportResponse {
  success: boolean;
  message: string;
  Files: string[];
}

export interface ReportListItem {
  id: number;
  type: string;
  name: string;
  connectionId: number;
  status: string;
  format: string;
  filePath: string;
  fileSize: number;
  createdAt: string;
}

export interface ReportDetail {
  id: number;
  type: string;
  name: string;
  connectionId: number;
  status: string;
  format: string;
  filePath: string;
  fileSize: number;
  createdAt: string;
  sections?: ReportSection[];
}

export interface ReportSection {
  title: string;
  type: string;
  content?: string;
  data?: Record<string, any>;
}

export interface ExportReportRequest {
  reportId: number;
  format: string;
  outputDir?: string;
}

// ==================== 系统配置 ====================

export interface SystemSettings {
  // 分析配置
  defaultAnalysisDays: number;
  defaultCpuThreshold: number;
  defaultMemoryThreshold: number;
  defaultBufferRatio: number;

  // 采集配置
  defaultMetricsDays: number;
  collectionConcurrency: number;

  // 报告配置
  defaultReportFormat: string;
  reportOutputDir: string;

  // 界面配置
  theme: string;
  language: string;
  autoRefreshInterval: number;
}

// ==================== 告警服务 ====================

export interface AlertListItem {
  id: number;
  targetType: string;
  targetKey: string;
  targetName: string;
  alertType: alertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  acknowledged: boolean;
  acknowledgedAt?: string;
  createdAt: string;
}

export interface MarkAlertRequest {
  id: number;
  acknowledged: boolean;
}

export interface AlertStats {
  total: number;
  unacknowledged: number;
  bySeverity: Record<string, number>;
  byType: Record<string, number>;
}

// ==================== 仪表盘 ====================

export interface DashboardStats {
  healthScore: number;
  zombieCount: number;
  totalSavings: string;
  vmCount: number;
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
  targetType: string;
  targetKey: string;
  targetName: string;
  alertType: string;
  severity: string;
  title: string;
  message: string;
  data?: string;
}

// ==================== 版本管理 ====================

export interface AppVersionInfo {
  version: string;
  storedVersion: string;
  majorVersions: string[];
  isDevelopment: boolean;
}

export interface VersionCheckResult {
  needsRebuild: boolean;
  currentVersion: string;
  databaseSize: number;
  hasData: boolean;
  latestVersion: string;
  message: string;
}
