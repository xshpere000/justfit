import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as TaskAPI from '@/api/connection'

export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
export type TaskType = 'collection' | 'analysis_zombie' | 'analysis_rightsize' | 'analysis_tidal' | 'analysis_health'

export interface Task {
  id: number
  type: string
  name: string
  status: TaskStatus
  progress: number
  error?: string
  createdAt: string
  startedAt?: string
  completedAt?: string
  connectionId?: number
  connectionName?: string
  platform?: string
  selectedVMs?: string[]
  vmCount?: number
  collectedVMCount?: number
  currentStep?: string
  analysisResults?: {
    zombie?: boolean
    rightsize?: boolean
    tidal?: boolean
    health?: boolean
  }
}

export interface CreateTaskParams {
  type: TaskType
  name: string
  connectionId: number
  connectionName: string
  platform: string
  selectedVMs: string[]
  vmCount: number
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const runningTasks = computed(() =>
    tasks.value.filter(t => t.status === 'running')
  )

  const hasRunningTasks = computed(() => runningTasks.value.length > 0)

  // 从后端获取任务列表（唯一的数据来源）
  async function syncTasksFromBackend() {
    console.log('[taskStore] syncTasksFromBackend 开始同步任务列表')
    loading.value = true
    error.value = null
    try {
      const backendTasks = await TaskAPI.listTasks('', 100, 0)
      console.log('[taskStore] syncTasksFromBackend 从后端获取到任务数量:', backendTasks.length)
      console.log('[taskStore] syncTasksFromBackend 任务详情:', backendTasks.map(t => ({
        id: t.id,
        name: t.name,
        status: t.status,
        progress: t.progress,
        vmCount: t.vmCount,
        collectedVMCount: t.collectedVMCount,
        analysisResults: t.analysisResults
      })))

      tasks.value = backendTasks.map(bt => ({
        id: bt.id,
        type: bt.type,
        name: bt.name,
        status: bt.status as TaskStatus,
        progress: bt.progress,
        error: bt.error,
        createdAt: bt.createdAt,
        startedAt: bt.startedAt,
        completedAt: bt.completedAt,
        connectionId: bt.connectionId,
        connectionName: bt.connectionName,
        platform: bt.platform,
        host: bt.host,
        selectedVMs: bt.selectedVMs,
        vmCount: bt.vmCount,
        collectedVMCount: bt.collectedVMCount,
        currentStep: bt.currentStep,
        analysisResults: bt.analysisResults
      }))
      console.log('[taskStore] syncTasksFromBackend 同步完成')
    } catch (e: any) {
      console.error('[taskStore] syncTasksFromBackend 同步失败:', e)
      error.value = e.message || '同步任务列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 创建任务（直接调用后端）
  async function createTask(params: CreateTaskParams): Promise<Task> {
    console.log('[taskStore] createTask 开始创建任务, params:', {
      type: params.type,
      name: params.name,
      connectionId: params.connectionId,
      platform: params.platform,
      selectedVMsCount: params.selectedVMs.length,
      vmCount: params.vmCount
    })

    try {
      const backendTaskId = await TaskAPI.createCollectTask({
        name: params.name,
        connectionId: params.connectionId,
        connectionName: params.connectionName,
        platform: params.platform,
        dataTypes: ['clusters', 'hosts', 'vms', 'metrics'],
        metricsDays: 30,
        vmCount: params.vmCount,
        selectedVMs: params.selectedVMs
      })
      console.log('[taskStore] createTask 后端任务创建成功, backendTaskId:', backendTaskId)

      // 创建成功后刷新任务列表
      await syncTasksFromBackend()

      // 返回创建的任务
      const createdTask = tasks.value.find(t => t.id === backendTaskId)
      if (createdTask) {
        console.log('[taskStore] createTask 从任务列表中找到创建的任务:', createdTask)
        return createdTask
      }

      // 如果找不到，返回基础对象
      console.warn('[taskStore] createTask 未在任务列表中找到创建的任务, 返回基础对象')
      return {
        id: backendTaskId,
        type: params.type,
        name: params.name,
        status: 'pending',
        progress: 0,
        createdAt: new Date().toISOString()
      }
    } catch (e: any) {
      console.error('[taskStore] createTask 创建任务失败:', e)
      throw e
    }
  }

  // 启动采集任务（向后兼容）
  async function startCollectionTask(taskId: number, connectionId: number, selectedVMs: string[] = [], days: number = 30) {
    // 任务已在 createTask 时创建，这里只刷新状态
    await syncTasksFromBackend()
  }

  // 获取单个任务
  function getTask(id: number | string): Task | undefined {
    const numId = typeof id === 'string' ? parseInt(id.replace('backend_', ''), 10) : id
    return tasks.value.find(t => t.id === numId)
  }

  // 更新任务状态（向后兼容，实际上会刷新整个列表）
  async function updateTaskStatus(id: string | number, status: TaskStatus, progress?: number) {
    // 这个方法现在只是触发刷新，实际状态由后端管理
    await syncTasksFromBackend()
  }

  // 更新任务进度（向后兼容）
  async function updateTaskProgress(id: string | number, progress: number, currentStep?: string) {
    await syncTasksFromBackend()
  }

  // 更新采集进度（向后兼容）
  async function updateCollectionProgress(id: string | number, collected: number, total: number) {
    await syncTasksFromBackend()
  }

  // 更新分析结果（向后兼容，现在数据从后端直接获取）
  async function updateAnalysisResult(id: string | number, analysisType: string, completed: boolean) {
    // 不做任何操作，分析结果状态从后端直接获取
    console.log('[updateAnalysisResult] 已弃用，数据将从后端同步获取')
  }

  // 设置任务错误（向后兼容）
  async function setTaskError(id: string | number, errorMsg: string) {
    await syncTasksFromBackend()
  }

  // 暂停任务（后端不支持，保留接口）
  async function pauseTask(id: string | number) {
    console.warn('pauseTask is not supported by backend')
  }

  // 恢复任务（后端不支持，保留接口）
  async function resumeTask(id: string | number) {
    console.warn('resumeTask is not supported by backend')
  }

  // 取消任务
  async function cancelTask(id: string | number) {
    const numId = typeof id === 'string' ? parseInt(id, 10) : id
    console.log('[taskStore] cancelTask 取消任务, taskId:', numId)
    try {
      await TaskAPI.stopTask(numId)
      console.log('[taskStore] cancelTask 后端停止成功, 刷新任务列表')
      await syncTasksFromBackend()
    } catch (e: any) {
      console.error('[taskStore] cancelTask 取消任务失败:', e)
      throw e
    }
  }

  // 删除任务
  async function deleteTask(id: string | number) {
    const numId = typeof id === 'string' ? parseInt(id, 10) : id
    console.log('[taskStore] deleteTask 删除任务, taskId:', numId)
    try {
      await TaskAPI.deleteTask(numId)
      console.log('[taskStore] deleteTask 后端删除成功, 从本地列表移除')
      // 从本地列表中移除
      tasks.value = tasks.value.filter(t => t.id !== numId)
    } catch (e: any) {
      console.error('[taskStore] deleteTask 删除任务失败:', e)
      throw e
    }
  }

  // 清除已完成的任务
  function clearCompletedTasks() {
    tasks.value = tasks.value.filter(t => t.status !== 'completed' && t.status !== 'failed' && t.status !== 'cancelled')
  }

  // 轮询运行中的任务
  let pollInterval: ReturnType<typeof setInterval> | null = null
  function startPolling(interval: number = 2000) {
    stopPolling()
    pollInterval = setInterval(async () => {
      // 始终同步任务列表，即使没有运行中的任务
      // 这样可以确保：
      // 1. 新创建的任务状态能及时更新
      // 2. 任务从 pending 变成 running 时能立即反映
      // 3. 任务完成或失败时能及时更新
      await syncTasksFromBackend()
    }, interval)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  // 初始化
  async function init() {
    await syncTasksFromBackend()
    startPolling()
  }

  return {
    tasks,
    loading,
    error,
    runningTasks,
    hasRunningTasks,
    syncTasksFromBackend,
    createTask,
    startCollectionTask,
    getTask,
    updateTaskStatus,
    updateTaskProgress,
    updateCollectionProgress,
    updateAnalysisResult,
    setTaskError,
    pauseTask,
    resumeTask,
    cancelTask,
    deleteTask,
    clearCompletedTasks,
    startPolling,
    stopPolling,
    init
  }
})
