/**
 * 类型转换工具函数
 * 用于前后端数据类型之间的转换
 */

import type { TaskInfo } from '@/types/api'
import type { Task, CreateTaskParams } from '@/stores/task'

/**
 * 将后端TaskInfo转换为前端Task类型
 */
export function transformBackendTaskToFrontend(taskInfo: TaskInfo): Task {
  const task: Task = {
    id: String(taskInfo.ID),
    type: mapBackendTypeToFrontend(taskInfo.Type),
    name: taskInfo.Name,
    status: mapBackendStatusToFrontend(taskInfo.Status),
    progress: taskInfo.Progress,
    error: taskInfo.Error,
    connectionId: taskInfo.ConnectionID,
    connectionName: taskInfo.ConnectionName,
    platform: taskInfo.Platform,
    totalVMs: taskInfo.TotalVMs || 0,
    collectedVMs: 0,
    analysisResults: {
      zombie: false,
      rightsize: false,
      tidal: false,
      health: false,
    },
    created_at: taskInfo.CreatedAt,
    started_at: taskInfo.StartedAt,
    ended_at: taskInfo.CompletedAt,
  }

  // 解析selectedVMs JSON字符串
  if (taskInfo.SelectedVMs) {
    try {
      task.selectedVMs = JSON.parse(taskInfo.SelectedVMs) as string[]
    } catch {
      task.selectedVMs = []
    }
  } else {
    task.selectedVMs = []
  }

  // 解析Result JSON（可能包含分析结果状态）
  if (taskInfo.Result) {
    try {
      const resultData = JSON.parse(taskInfo.Result)
      if (resultData.analysisResults) {
        task.analysisResults = {
          zombie: resultData.analysisResults.zombie || false,
          rightsize: resultData.analysisResults.rightsize || false,
          tidal: resultData.analysisResults.tidal || false,
          health: resultData.analysisResults.health || false,
        }
      }
    } catch {
      // 忽略解析错误
    }
  }

  return task
}

/**
 * 将前端Task类型转换为后端CreateTaskParams
 */
export function transformFrontendTaskToBackend(
  task: Task,
  connectionId: number,
  connectionName: string,
  platform: string
): Record<string, any> {
  return {
    type: mapFrontendTypeToBackend(task.type),
    name: task.name,
    connectionId,
    connectionName,
    platform,
    totalVMs: task.totalVMs,
    selectedVMs: JSON.stringify(task.selectedVMs || []),
    status: mapFrontendStatusToBackend(task.status),
  }
}

/**
 * 将前端任务参数转换为后端请求格式
 */
export function transformCreateTaskParams(params: CreateTaskParams): Record<string, any> {
  return {
    type: 'collection', // 采集任务
    name: params.name,
    connectionId: params.connectionId,
    connectionName: params.connectionName,
    platform: params.platform,
    totalVMs: params.totalVMs,
    selectedVMs: JSON.stringify(params.selectedVMs || []),
  }
}

/**
 * 映射后端任务类型到前端任务类型
 */
function mapBackendTypeToFrontend(backendType: string): Task['type'] {
  const typeMap: Record<string, Task['type']> = {
    collection: 'collection',
    analyze: 'analysis_zombie',
    'analysis.zombie': 'analysis_zombie',
    'analysis.rightsize': 'analysis_rightsize',
    'analysis.tidal': 'analysis_tidal',
    'analysis.health': 'analysis_health',
  }
  return typeMap[backendType] || 'collection'
}

/**
 * 映射前端任务类型到后端任务类型
 */
function mapFrontendTypeToBackend(frontendType: Task['type']): string {
  const typeMap: Record<string, string> = {
    collection: 'collection',
    analysis_zombie: 'analyze',
    analysis_rightsize: 'analyze',
    analysis_tidal: 'analyze',
    analysis_health: 'analyze',
  }
  return typeMap[frontendType] || 'collection'
}

/**
 * 映射后端任务状态到前端任务状态
 */
function mapBackendStatusToFrontend(backendStatus: string): Task['status'] {
  const statusMap: Record<string, Task['status']> = {
    pending: 'pending',
    running: 'running',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
  }
  return statusMap[backendStatus] || 'pending'
}

/**
 * 映射前端任务状态到后端任务状态
 */
function mapFrontendStatusToBackend(frontendStatus: Task['status']): string {
  const statusMap: Record<string, string> = {
    pending: 'pending',
    running: 'running',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
    paused: 'pending',
  }
  return statusMap[frontendStatus] || 'pending'
}

/**
 * 解析SelectedVMs JSON字符串
 */
export function parseSelectedVMs(selectedVMsJson: string | undefined): string[] {
  if (!selectedVMsJson) return []
  try {
    return JSON.parse(selectedVMsJson) as string[]
  } catch {
    return []
  }
}

/**
 * 将selectedVMs数组转换为JSON字符串
 */
export function stringifySelectedVMs(selectedVMs: string[] | undefined): string {
  if (!selectedVMs || !Array.isArray(selectedVMs)) return '[]'
  return JSON.stringify(selectedVMs)
}

/**
 * 创建安全的任务对象
 * 确保所有必要字段都有默认值
 */
export function createSafeTask(taskInfo: Partial<TaskInfo>): TaskInfo {
  return {
    ID: taskInfo.ID || 0,
    Type: taskInfo.Type || 'collection',
    Name: taskInfo.Name || '',
    Status: taskInfo.Status || 'pending',
    Progress: taskInfo.Progress || 0,
    Message: taskInfo.Message,
    Result: taskInfo.Result,
    Error: taskInfo.Error,
    CreatedAt: taskInfo.CreatedAt || new Date().toISOString(),
    StartedAt: taskInfo.StartedAt,
    CompletedAt: taskInfo.CompletedAt,
    ConnectionID: taskInfo.ConnectionID,
    ConnectionName: taskInfo.ConnectionName,
    Platform: taskInfo.Platform,
    TotalVMs: taskInfo.TotalVMs,
    SelectedVMs: taskInfo.SelectedVMs,
  }
}
