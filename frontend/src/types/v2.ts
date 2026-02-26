/**
 * JustFit v0.0.2 前端类型定义
 * 与后端 DTO 层保持一致
 * 命名规范: 统一使用驼峰命名
 */

// ==================== 通用响应 ====================

export interface Response<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
  code?: string
}

export interface PagedResponse<T = any> {
  total: number
  page: number
  size: number
  items: T[]
}

// ==================== 连接相关 ====================

export interface ConnectionResponse {
  id: number
  name: string
  platform: 'vcenter' | 'h3c-uis'
  host: string
  port: number
  username: string
  insecure: boolean
  status: 'connected' | 'disconnected' | 'error'
  createdAt: string
  lastSync?: string
}

export interface ConnectionListItem {
  id: number
  name: string
  platform: 'vcenter' | 'h3c-uis'
  host: string
  status: 'connected' | 'disconnected' | 'error'
  vmCount: number
  lastSync?: string
}

export interface TestConnectionResponse {
  success: boolean
  message: string
  version?: string
  product?: string
  latency?: number
}

export interface CreateConnectionRequest {
  name: string
  platform: 'vcenter' | 'h3c-uis'
  host: string
  port: number
  username: string
  password: string
  insecure: boolean
}

export interface UpdateConnectionRequest {
  id: number
  name: string
  platform: 'vcenter' | 'h3c-uis'
  host: string
  port: number
  username: string
  password?: string
  insecure: boolean
}

// ==================== 资源相关 ====================

export interface VMResponse {
  id: number
  name: string
  datacenter: string
  uuid: string
  cpuCount: number
  memoryMb: number
  memoryGb: number
  powerState: 'poweredOn' | 'poweredOff' | 'suspended'
  ipAddress?: string
  guestOs?: string
  hostName?: string
  overallStatus?: 'gray' | 'green' | 'yellow' | 'red'
  collectedAt: string
}

export interface HostResponse {
  id: number
  name: string
  datacenter: string
  ipAddress: string
  cpuCores: number
  cpuMhz: number
  memoryMb: number
  memoryGb: number
  numVMs: number
  powerState: string
  overallStatus: string
  collectedAt: string
}

export interface ClusterResponse {
  id: number
  name: string
  datacenter: string
  totalCpu: number
  totalMemory: number
  totalMemoryGb: number
  numHosts: number
  numVMs: number
  status: string
  collectedAt: string
}

export interface MetricPoint {
  timestamp: number
  value: number
}

export interface MetricsResponse {
  vmId: number
  vmName: string
  metricType: 'cpu' | 'memory' | 'diskRead' | 'diskWrite' | 'netRx' | 'netTx'
  startTime: string
  endTime: string
  dataPoints: MetricPoint[]
}

// ==================== 任务相关 ====================

export type TaskType = 'collection' | 'analysis'
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface TaskResponse {
  id: number
  type: TaskType
  name: string
  status: TaskStatus
  progress: number
  error?: string
  createdAt: string
  startedAt?: string
  completedAt?: string
  durationMs?: number
  connectionId?: number
  connectionName?: string
  platform?: string
  VMCount?: number
  collectedVMCount?: number
}

export interface TaskDetailResponse extends TaskResponse {
  currentStep?: string
  config?: Record<string, any>
  result?: Record<string, any>
  analysisResults?: {
    zombie?: boolean
    rightsize?: boolean
    tidal?: boolean
    health?: boolean
  }
}

export interface TaskLogEntry {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  fields?: Record<string, any>
}

export interface CreateCollectionRequest {
  connectionId: number
  connectionName: string
  platform: string
  dataTypes: string[]
  metricsDays: number
  vmCount: number
  selectedVMs: string[]
}

export interface CreateAnalysisRequest {
  connectionId: number
  analysisType: 'zombie' | 'rightsize' | 'tidal' | 'health'
  config?: Record<string, any>
}

// ==================== 分析结果 ====================

export interface ZombieVMResult {
  vmName: string
  datacenter: string
  host: string
  cpuCount: number
  memoryMb: number
  cpuUsage: number
  memoryUsage: number
  diskIoRate: number
  networkRate: number
  confidence: number
  daysLowUsage: number
  evidence: string[]
  recommendation: string
}

export interface RightSizeResult {
  vmName: string
  datacenter: string
  currentCpu: number
  currentMemoryMb: number
  currentMemoryGb: number
  recommendedCpu: number
  recommendedMemoryMb: number
  recommendedMemoryGb: number
  adjustmentType: 'none' | 'up' | 'down'
  riskLevel: 'low' | 'medium' | 'high'
  estimatedSaving: string
  confidence: number
}

export interface TidalResult {
  vmName: string
  datacenter: string
  pattern: 'daily' | 'weekly' | 'none'
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
  healthLevel: 'excellent' | 'good' | 'fair' | 'poor'
  resourceBalance: number
  overcommitRisk: number
  hotspotConcentration: number
  clusterCount: number
  hostCount: number
  vmCount: number
  riskItems: string[]
  recommendations: string[]
}

export interface AnalysisSummary {
  connectionId: number
  vmCount: number
  zombieVMs: number
  rightSizeVMs: number
  tidalVMs: number
  healthScore: number
  totalSavings: string
  lastAnalyzed: string
  riskDistribution: Record<string, number>
}

// ==================== 告警相关 ====================

export interface AlertResponse {
  id: number
  targetType: 'cluster' | 'host' | 'vm'
  targetKey: string
  targetName: string
  alertType: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  data?: string
  acknowledged: boolean
  acknowledgedAt?: string
  createdAt: string
}

export interface AlertListItem {
  id: number
  targetType: 'cluster' | 'host' | 'vm'
  targetName: string
  alertType: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  acknowledged: boolean
  createdAt: string
}

export interface AlertStats {
  total: number
  unacknowledged: number
  bySeverity: Record<string, number>
  byType: Record<string, number>
}

// ==================== 仪表盘 ====================

export interface DashboardStats {
  healthScore: number
  zombieCount: number
  totalSavings: string
  vmCount: number
  hostCount: number
  clusterCount: number
}
