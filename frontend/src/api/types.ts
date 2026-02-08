// =============== 通用类型 ===============

export interface ApiResponse<T = any> {
  code?: number
  message?: string
  data: T
}

export interface PageParams {
  page?: number
  page_size?: number
}

export interface PageResponse<T = any> extends ApiResponse<T[]> {
  total: number
  page: number
  page_size: number
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
  last_sync: string
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
  connection_id: number
  data_types: string[]
  metrics_days: number
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
  analysis_days?: number
  cpu_threshold?: number
  memory_threshold?: number
  min_confidence?: number
}

export interface ZombieVMResult {
  vm_name: string
  datacenter: string
  host: string
  cpu_count: number
  memory_mb: number
  cpu_usage: number
  memory_usage: number
  confidence: number
  days_low_usage: number
  evidence: string[]
  recommendation: string
}

export interface RightSizeConfig {
  analysis_days?: number
  buffer_ratio?: number
}

export interface RightSizeResult {
  vm_name: string
  datacenter: string
  current_cpu: number
  current_memory_mb: number
  recommended_cpu: number
  recommended_memory_mb: number
  adjustment_type: string
  risk_level: string
  estimated_saving: string
  confidence: number
}

export interface TidalConfig {
  analysis_days?: number
  min_stability?: number
}

export interface TidalResult {
  vm_name: string
  datacenter: string
  pattern: string
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
  health_level: string
  resource_balance: number
  overcommit_risk: number
  hotspot_concentration: number
  total_clusters: number
  total_hosts: number
  total_vms: number
  risk_items: string[]
  recommendations: string[]
}

// =============== 数据实体相关 ===============

export interface ClusterInfo {
  id: number
  connection_id: number
  name: string
  datacenter: string
  vendor: string
  total_cpu: number
  total_memory_mb: number
  total_hosts: number
  total_vms: number
  created_at: string
}

export interface HostInfo {
  id: number
  connection_id: number
  cluster_id: number
  cluster_name: string
  name: string
  vendor: string
  model: string
  cpu_cores: number
  cpu_mhz: number
  memory_mb: number
  vm_count: number
  power_state: string
  created_at: string
}

export interface VMInfo {
  id: number
  connection_id: number
  host_id: number
  host_name: string
  cluster_id: number
  cluster_name: string
  name: string
  uuid: string
  vcpu: number
  memory_mb: number
  disk_gb: number
  os_type: string
  power_state: string
  ip_address: string
  created_at: string
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
  current_step?: string
  total_steps?: number
  started_at?: string
  ended_at?: string
  created_at: string
}

// =============== 报告相关 ===============

export interface ReportSection {
  Title: string
  Content: string
  Data: any
  Type: string // text, table, chart, summary, list, zombie_table, rightsize_table, tidal_table, vm_table, health_summary, risk_list, recommendation_list
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
