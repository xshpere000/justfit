/**
 * 前端配置模块
 * 管理应用程序配置，支持开发和生产环境配置切换
 */

// 环境变量类型定义
interface ImportMetaEnv {
  readonly VITE_APP_ENV: string
  readonly VITE_DEFAULT_PLATFORM: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_ENABLE_COLLECTION: string
  readonly VITE_ENABLE_ANALYSIS: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// 应用配置接口
export interface AppConfig {
  env: 'development' | 'test' | 'production'
  defaultPlatform: 'h3c-uis' | 'vcenter'
  apiBaseUrl: string
  enableCollection: boolean
  enableAnalysis: boolean
}

// 获取环境变量值
function getEnv(key: string, defaultValue: string): string {
  return import.meta.env[key] || defaultValue
}

function getEnvBool(key: string, defaultValue: boolean): boolean {
  const value = import.meta.env[key]
  if (!value) return defaultValue
  const lower = value.toLowerCase()
  return lower === 'true' || lower === '1' || lower === 'yes' || lower === 'on'
}

// 应用配置单例
let config: AppConfig | null = null

/**
 * 获取应用配置
 */
export function getConfig(): AppConfig {
  if (!config) {
    config = {
      env: getEnv('VITE_APP_ENV', 'test') as AppConfig['env'],
      defaultPlatform: (getEnv('VITE_DEFAULT_PLATFORM', 'h3c-uis') || 'h3c-uis') as AppConfig['defaultPlatform'],
      apiBaseUrl: getEnv('VITE_API_BASE_URL', '/api'),
      enableCollection: getEnvBool('VITE_ENABLE_COLLECTION', true),
      enableAnalysis: getEnvBool('VITE_ENABLE_ANALYSIS', true),
    }
  }
  return config
}

/**
 * 检查是否为测试环境
 */
export function isTest(): boolean {
  return getConfig().env === 'test'
}

/**
 * 检查是否为开发环境
 */
export function isDevelopment(): boolean {
  return getConfig().env === 'development'
}

/**
 * 检查是否为生产环境
 */
export function isProduction(): boolean {
  return getConfig().env === 'production'
}

/**
 * 获取默认虚拟化平台
 */
export function getDefaultPlatform(): 'h3c-uis' | 'vcenter' {
  return getConfig().defaultPlatform
}

/**
 * 平台选项列表
 */
export const PLATFORM_OPTIONS = [
  { value: 'h3c-uis', label: 'H3C UIS' },
  { value: 'vcenter', label: 'VMware vCenter' },
] as const

export type PlatformType = 'h3c-uis' | 'vcenter'

/**
 * 获取平台显示名称
 */
export function getPlatformDisplayName(platform: PlatformType): string {
  const option = PLATFORM_OPTIONS.find(opt => opt.value === platform)
  return option?.label || platform
}

/**
 * 任务类型定义
 */
export const TASK_TYPE_LABELS = {
  collection: '数据采集',
  analysis_zombie: '僵尸VM检测',
  analysis_rightsize: '容量优化',
  analysis_tidal: '潮汐分析',
  analysis_health: '健康评估',
} as const

export type TaskTypeKey = keyof typeof TASK_TYPE_LABELS

/**
 * 获取任务类型显示名称
 */
export function getTaskTypeLabel(type: TaskTypeKey): string {
  return TASK_TYPE_LABELS[type] || type
}

/**
 * 评估功能定义
 */
export const ANALYSIS_FEATURES = {
  zombie: {
    key: 'zombie',
    label: '僵尸VM检测',
    description: '识别长时间未使用或已关闭的虚拟机',
  },
  rightsize: {
    key: 'rightsize',
    label: '容量优化',
    description: '分析虚拟机资源使用情况，提供优化建议',
  },
  tidal: {
    label: '潮汐分析',
    description: '分析虚拟机负载的周期性变化',
  },
  health: {
    label: '健康评估',
    description: '评估虚拟机和主机的健康状态',
  },
} as const

export type AnalysisFeatureKey = keyof typeof ANALYSIS_FEATURES
