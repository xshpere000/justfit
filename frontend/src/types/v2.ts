/**
 * JustFit v0.0.2 前端类型定义
 * 与后端 DTO 层保持一致
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
  created_at: string
  last_sync?: string
}

export interface ConnectionListItem {
  id: number
  name: string
  platform: 'vcenter' | 'h3c-uis'
  host: string
  status: 'connected' | 'disconnected' | 'error'
  vm_count: number
  last_sync?: string
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
  cpu_count: number
  memory_mb: number
  memory_gb: number
  power_state: 'poweredOn' | 'poweredOff' | 'suspended'
  ip_address?: string
  guest_os?: string
  host_name?: string
  overall_status?: 'gray' | 'green' | 'yellow' | 'red'
  collected_at: string
}

export interface HostResponse {
  id: number
  name: string
  datacenter: string
  ip_address: string
  cpu_cores: number
  cpu_mhz: number
  memory_mb: number
  memory_gb: number
  num_vms: number
  power_state: string
  overall_status: string
  collected_at: string
}

export interface ClusterResponse {
  id: number
  name: string
  datacenter: string
  total_cpu: number
  total_memory: number
  total_memory_gb: number
  num_hosts: number
  num_vms: number
  status: string
  collected_at: string
}

export interface MetricPoint {
  timestamp: number
  value: number
}

export interface MetricsResponse {
  vm_id: number
  vm_name: string
  metric_type: 'cpu' | 'memory' | 'disk_read' | 'disk_write' | 'net_rx' | 'net_tx'
  start_time: string
  end_time: string
  data_points: MetricPoint[]
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
  created_at: string
  started_at?: string
  completed_at?: string
  duration_ms?: number
  connection_id?: number
  connection_name?: string
  platform?: string
  total_vms?: number
  collected_vms?: number
}

export interface TaskDetailResponse extends TaskResponse {
  current_step?: string
  config?: Record<string, any>
  result?: Record<string, any>
  analysis_results?: {
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
  connection_id: number
  connection_name: string
  platform: string
  data_types: string[]
  metrics_days: number
  total_vms: number
  selected_vms: string[]
}

export interface CreateAnalysisRequest {
  connection_id: number
  analysis_type: 'zombie' | 'rightsize' | 'tidal' | 'health'
  config?: Record<string, any>
}

// ==================== 分析结果 ====================

export interface ZombieVMResult {
  vm_name: string
  datacenter: string
  host: string
  cpu_count: number
  memory_mb: number
  cpu_usage: number
  memory_usage: number
  disk_io_rate: number
  network_rate: number
  confidence: number
  days_low_usage: number
  evidence: string[]
  recommendation: string
}

export interface RightSizeResult {
  vm_name: string
  datacenter: string
  current_cpu: number
  current_memory_mb: number
  current_memory_gb: number
  recommended_cpu: number
  recommended_memory_mb: number
  recommended_memory_gb: number
  adjustment_type: 'none' | 'up' | 'down'
  risk_level: 'low' | 'medium' | 'high'
  estimated_saving: string
  confidence: number
}

export interface TidalResult {
  vm_name: string
  datacenter: string
  pattern: 'daily' | 'weekly' | 'none'
  stability_score: number
  peak_hours: number[]
  peak_days: number[]
  recommendation: string
  estimated_saving: string
}

export interface HealthScoreResult {
  connection_id: number
  connection_name: string
  overall_score: number
  health_level: 'excellent' | 'good' | 'fair' | 'poor'
  resource_balance: number
  overcommit_risk: number
  hotspot_concentration: number
  total_clusters: number
  total_hosts: number
  total_vms: number
  risk_items: string[]
  recommendations: string[]
}

export interface AnalysisSummary {
  connection_id: number
  total_vms: number
  zombie_vms: number
  rightsize_vms: number
  tidal_vms: number
  health_score: number
  total_savings: string
  last_analyzed: string
  risk_distribution: Record<string, number>
}

// ==================== 告警相关 ====================

export interface AlertResponse {
  id: number
  target_type: 'cluster' | 'host' | 'vm'
  target_key: string
  target_name: string
  alert_type: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  data?: string
  acknowledged: boolean
  acknowledged_at?: string
  created_at: string
}

export interface AlertListItem {
  id: number
  target_type: 'cluster' | 'host' | 'vm'
  target_name: string
  alert_type: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  message: string
  acknowledged: boolean
  created_at: string
}

export interface AlertStats {
  total: number
  unacknowledged: number
  by_severity: Record<string, number>
  by_type: Record<string, number>
}

// ==================== 仪表盘 ====================

export interface DashboardStats {
  health_score: number
  zombie_count: number
  total_savings: string
  total_vms: number
  total_hosts: number
  total_clusters: number
}
