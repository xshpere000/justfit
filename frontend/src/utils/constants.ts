// =============== 平台类型 ===============

export const PLATFORM_TYPES = [
  { label: 'VMware vCenter', value: 'vcenter' },
  { label: 'H3C UIS', value: 'h3c' }
] as const

export const PLATFORM_LABELS: Record<string, string> = {
  vcenter: 'VMware vCenter',
  h3c: 'H3C UIS'
}

// =============== 连接状态 ===============

export const CONNECTION_STATUS = [
  { label: '已连接', value: 'connected', type: 'success' },
  { label: '未连接', value: 'disconnected', type: 'info' },
  { label: '连接失败', value: 'error', type: 'danger' },
  { label: '连接中', value: 'connecting', type: 'warning' }
] as const

// =============== 电源状态 ===============

export const POWER_STATES = [
  { label: '开机', value: 'poweredOn', type: 'success' },
  { label: '关机', value: 'poweredOff', type: 'info' },
  { label: '暂停', value: 'suspended', type: 'warning' }
] as const

// =============== 数据类型 ===============

export const DATA_TYPES = [
  { label: '集群信息', value: 'clusters' },
  { label: '主机信息', value: 'hosts' },
  { label: '虚拟机信息', value: 'vms' },
  { label: '性能指标', value: 'metrics' }
] as const

// =============== 分析类型 ===============

export const ANALYSIS_TYPES = [
  { label: '僵尸 VM 检测', value: 'zombie', icon: 'Monitor' },
  { label: 'Right Size 评估', value: 'rightsize', icon: 'Crop' },
  { label: '潮汐检测', value: 'tidal', icon: 'TrendCharts' },
  { label: '平台健康', value: 'health', icon: 'DataAnalysis' }
] as const

// =============== 风险等级 ===============

export const RISK_LEVELS = [
  { label: '低风险', value: 'low', type: 'success', color: '#67C23A' },
  { label: '中风险', value: 'medium', type: 'warning', color: '#E6A23C' },
  { label: '高风险', value: 'high', type: 'danger', color: '#F56C6C' }
] as const

// =============== 健康等级 ===============

export const HEALTH_LEVELS = [
  { label: '优秀', value: 'excellent', type: 'success', color: '#67C23A', minScore: 90 },
  { label: '良好', value: 'good', type: 'success', color: '#409EFF', minScore: 75 },
  { label: '一般', value: 'fair', type: 'warning', color: '#E6A23C', minScore: 60 },
  { label: '较差', value: 'poor', type: 'danger', color: '#F56C6C', minScore: 0 }
] as const

// =============== 调整类型 ===============

export const ADJUSTMENT_TYPES = [
  { label: '缩小配置', value: 'downsize', type: 'success' },
  { label: '扩大配置', value: 'upsize', type: 'warning' },
  { label: '配置合理', value: 'optimal', type: 'info' }
] as const

// =============== 默认配置 ===============

export const DEFAULT_COLLECTION_DAYS = 7
export const DEFAULT_ANALYSIS_DAYS = 30
export const MAX_METRICS_DAYS = 90

// =============== 路由 ===============

export const ROUTES = {
  DASHBOARD: '/',
  CONNECTIONS: '/connections',
  COLLECTION: '/collection',
  ANALYSIS_ZOMBIE: '/analysis/zombie',
  ANALYSIS_RIGHTSIZE: '/analysis/rightsize',
  ANALYSIS_TIDAL: '/analysis/tidal',
  ANALYSIS_HEALTH: '/analysis/health',
  REPORTS: '/reports',
  TASKS: '/tasks',
  SETTINGS: '/settings'
} as const
