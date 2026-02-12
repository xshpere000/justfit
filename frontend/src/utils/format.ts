import dayjs from './dayjs'

// 格式化日期时间
export function formatDateTime(timestamp: string | number | Date): string {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

// 格式化日期
export function formatDate(timestamp: string | number | Date): string {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('YYYY-MM-DD')
}

// 格式化时间
export function formatTime(timestamp: string | number | Date): string {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('HH:mm:ss')
}

// 相对时间
export function formatRelative(timestamp: string | number | Date): string {
  if (!timestamp) return '-'
  return dayjs(timestamp).fromNow()
}

// 格式化文件大小
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 格式化内存 (MB)
export function formatMemory(mb: number): string {
  if (mb < 1024) return mb + ' MB'
  return (mb / 1024).toFixed(2) + ' GB'
}

// 格式化 CPU
export function formatCPU(cores: number): string {
  return cores + ' 核'
}

// 格式化百分比
export function formatPercent(value: number, decimals: number = 2): string {
  return value.toFixed(decimals) + '%'
}

// 格式化时长 (毫秒)
export function formatDuration(ms: number): string {
  if (ms < 1000) return ms + 'ms'
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's'
  if (ms < 3600000) return Math.floor(ms / 60000) + 'm ' + Math.floor((ms % 60000) / 1000) + 's'
  return Math.floor(ms / 3600000) + 'h ' + Math.floor((ms % 3600000) / 60000) + 'm'
}

// 格式化数字
export function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN')
}

// 获取连接状态类型
export function getConnectionStatusType(status: string): string {
  const statusMap: Record<string, string> = {
    connected: 'success',
    disconnected: 'info',
    error: 'danger',
    connecting: 'warning'
  }
  return statusMap[status] || 'info'
}

// 获取连接状态文本
export function getConnectionStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    connected: '已连接',
    disconnected: '未连接',
    error: '连接失败',
    connecting: '连接中'
  }
  return statusMap[status] || status
}

// 获取电源状态类型
export function getPowerStateType(state: string): string {
  const stateMap: Record<string, string> = {
    poweredOn: 'success',
    poweredOff: 'info',
    suspended: 'warning'
  }
  return stateMap[state] || 'info'
}

// 获取风险等级类型
export function getRiskLevelType(level: string): string {
  const levelMap: Record<string, string> = {
    low: 'success',
    medium: 'warning',
    high: 'danger'
  }
  return levelMap[level] || 'info'
}

// 获取健康等级类型
export function getHealthLevelType(level: string): string {
  const levelMap: Record<string, string> = {
    excellent: 'success',
    good: 'success',
    fair: 'warning',
    poor: 'danger'
  }
  return levelMap[level] || 'info'
}

// 获取调整类型
export function getAdjustmentType(type: string): string {
  const typeMap: Record<string, string> = {
    downsize: '缩小配置',
    upsize: '扩大配置',
    optimal: '配置合理',
    none: '无需调整'
  }
  return typeMap[type] || type
}
