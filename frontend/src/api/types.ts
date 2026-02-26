// =============== 通用类型 ===============

export interface ApiResponse<T = any> {
  code?: number
  message?: string
  data: T
}

export interface PageParams {
  page?: number
  pageSize?: number
}

export interface PageResponse<T = any> extends ApiResponse<T[]> {
  total: number
  page: number
  pageSize: number
}

// =============== 版本管理相关 ===============

export interface AppVersionInfo {
  version: string          // 当前应用版本
  storedVersion: string   // 数据库中存储的版本
  majorVersions: string[] // 大版本列表
  isDevelopment: boolean  // 是否开发版本
}

export interface VersionCheckResult {
  needsRebuild: boolean
  currentVersion: string
  databaseSize: number
  hasData: boolean
  latestVersion: string
  message: string
}

// =============== 连接相关 ===============

export interface ConnectionInfo {
  id: number
  name: string
  platform: string
  host: string
  port: number
  username: string
  insecure: boolean
  status: string
  lastSync: string
}

export interface CreateConnectionRequest {
  name: string
  platform: 'vcenter' | 'h3c'
  host: string
  port: number
  username: string
  password: string
  insecure?: boolean
}

export interface UpdateConnectionRequest extends CreateConnectionRequest {
  id: number
}

// =============== 数据采集相关 ===============

export interface CollectionConfig {
  connectionId: number
  dataTypes: string[]
  metricsDays: number
}

export interface CollectionResult {
  success: boolean
  message: string
  clusters: number
  hosts: number
  vms: number
  metrics: number
  duration: number
}

// =============== 分析相关 ===============

export interface ZombieVMConfig {
  analysisDays?: number
  cpuThreshold?: number
  memoryThreshold?: number
  minConfidence?: number
}

export interface ZombieVMResult {
  vmName: string
  datacenter: string
  host: string
  cpuCount: number
  memoryMb: number
  cpuUsage: number
  memoryUsage: number
  confidence: number
  daysLowUsage: number
  evidence: string[]
  recommendation: string
}

export interface RightSizeConfig {
  analysisDays?: number
  bufferRatio?: number
}

export interface RightSizeResult {
  vmName: string
  datacenter: string
  currentCpu: number
  currentMemoryMb: number
  recommendedCpu: number
  recommendedMemoryMb: number
  adjustmentType: string
  riskLevel: string
  estimatedSaving: string
  confidence: number
}

export interface TidalConfig {
  analysisDays?: number
  minStability?: number
}

export interface TidalResult {
  vmName: string
  datacenter: string
  pattern: string
  stabilityScore: number
  peakHours: number[]
  peakDays: number[]
  recommendation: string
  estimatedSaving: string
}

export interface HealthScoreResult {
  connectionId: number
  connectionName: string
  overallScore: number
  healthLevel: string
  resourceBalance: number
  overcommitRisk: number
  hotspotConcentration: number
  clusterCount: number
  hostCount: number
  VMCount: number
  riskItems: string[]
  recommendations: string[]
}

// =============== 数据实体相关 ===============

export interface ClusterInfo {
  id: number
  connectionId: number
  name: string
  datacenter: string
  vendor: string
  totalCpu: number
  totalMemoryMb: number
  hostCount: number
  VMCount: number
  createdAt: string
}

export interface HostInfo {
  id: number
  connectionId: number
  clusterId: number
  clusterName: string
  name: string
  vendor: string
  model: string
  cpuCores: number
  cpuMhz: number
  memoryMb: number
  VMCount: number
  powerState: string
  createdAt: string
}

export interface VMInfo {
  id: number
  connectionId: number
  hostId: number
  hostName: string
  clusterId: number
  clusterName: string
  name: string
  uuid: string
  vcpu: number
  memoryMb: number
  diskGb: number
  osType: string
  powerState: string
  ipAddress: string
  createdAt: string
}

// =============== 图表数据相关 ===============

export interface MetricPoint {
  timestamp: number
  value: number
}

export interface ChartData {
  name: string
  data: MetricPoint[]
  color?: string
}

// =============== 任务相关 ===============

export interface TaskInfo {
  id: string
  type: string
  name: string
  status: string
  progress: number
  currentStep?: string
  totalSteps?: number
  startedAt?: string
  endedAt?: string
  createdAt: string
}

// =============== 报告相关 ===============

export interface ReportSection {
  Title: string
  Content: string
  Data: any
  Type: string // text, table, chart, summary, list, zombieTable, rightsizeTable, tidalTable, vmTable, healthSummary, riskList, recommendationList
}

export interface ReportData {
  Title: string
  GeneratedAt: string
  ConnectionID: number
  Metadata: Record<string, any>
  Sections: ReportSection[]
}

export interface ReportExportOptions {
  Format: 'json' | 'html' | 'xlsx'
  OutputDir?: string
}
