/**
 * Wails API 服务层
 * 直接使用 Wails 生成的绑定调用后端 API
 */

import * as App from '../../wailsjs/go/main/App.js'
import type * as Models from '../../wailsjs/go/models.js'

// 导出类型供其他模块使用
export type * from '../../wailsjs/go/models'

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

export async function createCollectTask(config: any): Promise<number> {
  return await App.CreateCollectTask(config)
}

export async function stopTask(id: number): Promise<void> {
  await App.StopTask(id)
}

export async function retryTask(id: number): Promise<number> {
  return await App.RetryTask(id)
}

export async function getTaskLogs(id: number, limit: number = 100): Promise<main.TaskLogEntry[]> {
  return await App.GetTaskLogs(id, limit)
}

// =============== 采集 API ===============

export async function collectData(config: any): Promise<main.CollectionResult> {
  return await App.CollectData(config)
}

// =============== 分析 API ===============

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
  createCollectTask: createCollectTask,
  stop: stopTask,
  retry: retryTask,
  getLogs: getTaskLogs
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

export {
  ConnectionApi,
  TaskApi,
  CollectionApi,
  AnalysisApi,
  ResourceApi,
  DashboardApi
}
