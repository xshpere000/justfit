/**
 * 前端通用类型定义
 * 这些类型与前端代码使用的命名规范一致
 * 命名规范: 统一使用驼峰命名
 */

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
  connectionId?: number
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
  connectionId?: number
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
  connectionId?: number
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
  vmCount: number
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
  vmCount: number
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
  hostIp?: string
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
  Type: string
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
