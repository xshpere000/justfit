/**
 * JustFit 前端类型定义统一入口
 */

// 导入 API 相关类型
export * from './api'

// 从 common.ts 导入通用类型（只导出真正通用的，避免与 api.ts 冲突）
export type { ReportData, ReportSection, ReportExportOptions } from './common'

// =============== 其他通用类型 ===============

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
