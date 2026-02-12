/**
 * API 服务统一入口
 * 所有前端通过此文件访问后端 API
 */

// 导出类型定义
export * from './connection_new'

// 导出 API 服务
export {
  ConnectionApi,
  TaskApi,
  CollectionApi,
  AnalysisApi,
  ResourceApi,
  DashboardApi
} from './connection_new'
