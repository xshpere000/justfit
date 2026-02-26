/**
 * Wails API 服务层
 * 直接使用 Wails 生成的绑定调用后端 API
 * 类型定义使用自定义类型，与后端 JSON tags 对齐（驼峰命名）
 */

import * as App from '../../wailsjs/go/main/App.js'
import type * as Models from '../../wailsjs/go/models.js'

// 使用自定义类型定义（与后端 JSON 对齐）
export type * from '../types/api'

// 保留 main 命名空间用于向后兼容，但使用自定义类型
export namespace main {
  export type ConnectionInfo = import('../types/api').ConnectionInfo
  export type TaskInfo = import('../types/api').TaskInfo
  export type TaskDetail = import('../types/api').TaskDetail
  export type TaskLogEntry = import('../types/api').TaskLogEntry
  export type CollectionResult = import('../types/api').CollectionResult
  export type CollectionConfig = import('../types/api').CollectionConfig
  export type ZombieVMResult = import('../types/api').ZombieVMResult
  export type RightSizeResult = import('../types/api').RightSizeResult
  export type TidalResult = import('../types/api').TidalResult
  export type HealthScoreResult = import('../types/api').HealthScoreResult
  export type ClusterListItem = import('../types/api').ClusterListItem
  export type HostListItem = import('../types/api').HostListItem
  export type VMListItem = import('../types/api').VMListItem
  export type DashboardStats = import('../types/api').DashboardStats
  export type AppVersionInfo = import('../types/api').AppVersionInfo
  export type VersionCheckResult = import('../types/api').VersionCheckResult
  export type AlertListItem = import('../types/api').AlertListItem
  export type AlertStats = import('../types/api').AlertStats
}

// =============== 连接管理 API ===============

export async function listConnections(): Promise<main.ConnectionInfo[]> {
  return await App.ListConnections()
}

export async function createConnection(req: any): Promise<number> {
  return await App.CreateConnection(req)
}

export async function testConnection(id: number): Promise<string> {
  return await App.TestConnection(id)
}

export async function deleteConnection(id: number): Promise<void> {
  await App.DeleteConnection(id)
}

export async function getConnection(id: number): Promise<main.ConnectionInfo> {
  return await App.GetConnection(id)
}

export async function updateConnection(req: any): Promise<void> {
  await App.UpdateConnection(req)
}

// =============== 任务管理 API ===============

export async function listTasks(status?: string, limit: number = 10, offset: number = 0): Promise<main.TaskInfo[]> {
  return await App.ListTasks(status || '', limit, offset)
}

export async function getTask(id: number): Promise<main.TaskInfo> {
  return await App.GetTask(id)
}

export async function getTaskDetail(id: number): Promise<main.TaskDetail> {
  return await App.GetTaskDetail(id)
}

export async function createCollectTask(config: any): Promise<number> {
  return await App.CreateCollectTask(config)
}

/**
 * 创建分析任务 (旧版，保持向后兼容)
 * @deprecated 使用 runAnalysisJob 代替，将分析任务关联到评估任务下
 * @param analysisType 分析类型: zombie, rightsize, tidal, health
 * @param connectionId 连接ID
 * @param config 分析配置
 * @returns 任务ID
 */
export async function createAnalysisTask(analysisType: string, connectionId: number, config: any): Promise<number> {
  return await App.CreateAnalysisTask(analysisType, connectionId, config)
}

/**
 * 运行分析子任务 (新版)
 * 在指定的评估任务下创建的运行分析子任务
 * @param taskId 评估任务ID
 * @param analysisType 分析类型: zombie, rightsize, tidal, health
 * @param config 分析配置
 * @returns 分析子任务ID
 */
export async function runAnalysisJob(taskId: number, analysisType: string, config: any): Promise<number> {
  return await App.RunAnalysisJob(taskId, analysisType, config)
}

/**
 * 获取指定任务的所有分析子任务
 * @param taskId 评估任务ID
 * @returns 分析子任务列表
 */
export async function getAnalysisJobs(taskId: number): Promise<any[]> {
  return await App.GetAnalysisJobs(taskId)
}

/**
 * 获取分析子任务状态
 * @param jobId 分析子任务ID
 * @returns 子任务状态信息
 */
export async function getAnalysisJobStatus(jobId: number): Promise<any> {
  return await App.GetAnalysisJobStatus(jobId)
}

export async function stopTask(id: number): Promise<void> {
  await App.StopTask(id)
}

export async function retryTask(id: number): Promise<number> {
  return await App.RetryTask(id)
}

export async function deleteTask(id: number): Promise<void> {
  await App.DeleteTask(id)
}

export async function getTaskLogs(id: number, limit: number = 100): Promise<main.TaskLogEntry[]> {
  return await App.GetTaskLogs(id, limit)
}

/**
 * 获取任务分析结果
 * @param taskId 任务ID
 * @param analysisType 分析类型，为空则返回所有分析结果
 * @returns 按分析类型分组的结果
 *
 * 后端 analysis_type 命名: zombie, rightsize, tidal, health
 * 前端应使用 createAnalysisTask 创建任务后调用此函数获取结果
 */
export async function getTaskAnalysisResult(taskId: number, analysisType: string = ''): Promise<Record<string, any>> {
  return await App.GetTaskAnalysisResult(taskId, analysisType)
}

// =============== 采集 API ===============

export async function collectData(config: any): Promise<main.CollectionResult> {
  return await App.CollectData(config)
}

// =============== 分析 API ===============
// 注意：以下为实时分析 API，直接返回结果但不保存到数据库
// 如需持久化结果，请使用 createAnalysisTask 创建分析任务

export async function detectZombieVMs(connectionId: number, config: any): Promise<main.ZombieVMResult[]> {
  return await App.DetectZombieVMs(connectionId, config)
}

export async function analyzeRightSize(connectionId: number, config: any): Promise<main.RightSizeResult[]> {
  return await App.AnalyzeRightSize(connectionId, config)
}

export async function detectTidalPattern(connectionId: number, config: any): Promise<main.TidalResult[]> {
  return await App.DetectTidalPattern(connectionId, config)
}

export async function analyzeHealthScore(connectionId: number): Promise<main.HealthScoreResult> {
  return await App.AnalyzeHealthScore(connectionId)
}

// =============== 资源查询 API ===============

export async function listClusters(connectionId: number): Promise<main.ClusterListItem[]> {
  return await App.ListClusters(connectionId)
}

export async function listHosts(connectionId: number): Promise<main.HostListItem[]> {
  return await App.ListHosts(connectionId)
}

export async function listVMs(connectionId: number): Promise<main.VMListItem[]> {
  return await App.ListVMs(connectionId)
}

export async function listTaskVMs(taskId: number, limit: number = 100, offset: number = 0, keyword: string = ''): Promise<{vms: main.VMListItem[], total: number}> {
  const result = await App.ListTaskVMs(taskId, limit, offset, keyword)
  // 后端现在返回 TaskVMListResponse 结构体
  if (result && result.vms) {
    return {
      vms: result.vms || [],
      total: result.total || 0
    }
  }
  // 如果返回值格式不对，返回空结果
  console.warn('[listTaskVMs] 返回值格式异常:', result)
  return {
    vms: [],
    total: 0
  }
}

export async function getVMList(connectionId: number): Promise<{vms: any[], total: number}> {
  const result = await App.GetVMList(connectionId)
  const vms = JSON.parse(result)
  return {
    vms: vms,
    total: vms.length
  }
}

export async function getHostListRaw(connectionId: number): Promise<string> {
  return await App.GetHostList(connectionId)
}

export async function getClusterListRaw(connectionId: number): Promise<string> {
  return await App.GetClusterList(connectionId)
}

// =============== 仪表盘 API ===============

export async function getDashboardStats(): Promise<main.DashboardStats> {
  return await App.GetDashboardStats()
}

// =============== 版本管理 API ===============

/**
 * 获取应用版本信息
 * @returns 版本信息
 */
export async function getAppVersion(): Promise<main.AppVersionInfo> {
  return await App.GetAppVersion()
}

/**
 * 检查应用版本
 * @returns 版本检查结果
 */
export async function checkVersion(): Promise<main.VersionCheckResult> {
  return await App.CheckVersion()
}

/**
 * 重建数据库（清除所有历史数据）
 * 仅在大版本升级时使用，需要用户确认
 */
export async function rebuildDatabase(): Promise<void> {
  await App.RebuildDatabase()
}

// =============== 导出方便对象 ===============

const ConnectionApi = {
  list: listConnections,
  create: createConnection,
  test: testConnection,
  delete: deleteConnection,
  get: getConnection,
  update: updateConnection
}

const TaskApi = {
  list: listTasks,
  get: getTask,
  getTaskDetail: getTaskDetail,
  createCollectTask: createCollectTask,
  createAnalysisTask: createAnalysisTask,
  runAnalysisJob: runAnalysisJob,
  getAnalysisJobs: getAnalysisJobs,
  getAnalysisJobStatus: getAnalysisJobStatus,
  stop: stopTask,
  retry: retryTask,
  delete: deleteTask,
  getLogs: getTaskLogs,
  getTaskAnalysisResult: getTaskAnalysisResult
}

const CollectionApi = {
  collect: collectData
}

const AnalysisApi = {
  detectZombieVMs,
  analyzeRightSize,
  detectTidalPattern,
  analyzeHealthScore
}

const ResourceApi = {
  listClusters,
  listHosts,
  listVMs,
  getVMList,
  getHostListRaw,
  getClusterListRaw
}

const DashboardApi = {
  getStats: getDashboardStats
}

const VersionApi = {
  getAppVersion,
  checkVersion,
  rebuildDatabase
}

export {
  ConnectionApi,
  TaskApi,
  CollectionApi,
  AnalysisApi,
  ResourceApi,
  DashboardApi,
  VersionApi
}
