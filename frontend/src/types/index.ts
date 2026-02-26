/**
 * JustFit 前端类型定义
 * 与后端 API 对接的类型定义
 */

// 导入 API 官方类型定义
export * from './api'
export * from './common'

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
