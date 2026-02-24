import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as TaskAPI from '@/api/connection'

export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
export type TaskType = 'collection' | 'analysis_zombie' | 'analysis_rightsize' | 'analysis_tidal' | 'analysis_health'

export interface Task {
  id: string
  type: TaskType
  name: string
  status: TaskStatus
  progress: number
  connectionId?: number
  connectionName?: string
  platform?: string
  selectedVMs?: string[]
  totalVMs?: number
  collectedVMs?: number
  analysisResults?: {
    zombie?: boolean
    rightsize?: boolean
    tidal?: boolean
    health?: boolean
  }
  error?: string
  canMinimize?: boolean
  backendTaskId?: number
  created_at?: string
  started_at?: string
  ended_at?: string
  current_step?: string
}

export interface CreateTaskParams {
  type: TaskType
  name: string
  connectionId: number
  connectionName: string
  platform: string
  selectedVMs: string[]
  totalVMs: number
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])

  const runningTasks = computed(() =>
    tasks.value.filter(t => t.status === 'running')
  )

  const currentTask = ref<Task | null>(null)

  const hasRunningTasks = computed(() => runningTasks.value.length > 0)

  // 辅助函数：找到任务在数组中的索引
  function findTaskIndex(id: string | undefined): number {
    if (!id || typeof id !== 'string') {
      return -1
    }

    // 首先尝试精确匹配 ID
    let index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) return index

    // 如果找不到，尝试通过 backendTaskId 匹配
    const numericId = id.replace('backend_', '')
    const backendId = parseInt(numericId, 10)
    if (!isNaN(backendId)) {
      index = tasks.value.findIndex(t => t.backendTaskId === backendId)
      if (index !== -1) return index
    }

    return -1
  }

  function getTask(id: string | undefined): Task | undefined {
    const index = findTaskIndex(id)
    return index !== -1 ? tasks.value[index] : undefined
  }

  function createTask(params: CreateTaskParams): Task {
    const timestamp = Date.now()
    const randomStr = Math.random().toString(36).substr(2, 9)
    const task: Task = {
      id: 'task_' + timestamp + '_' + randomStr,
      type: params.type,
      name: params.name,
      status: 'pending',
      progress: 0,
      connectionId: params.connectionId,
      connectionName: params.connectionName,
      platform: params.platform,
      selectedVMs: params.selectedVMs,
      totalVMs: params.totalVMs,
      collectedVMs: 0,
      analysisResults: {
        zombie: false,
        rightsize: false,
        tidal: false,
        health: false
      },
      canMinimize: true,
      created_at: new Date().toISOString()
    }

    tasks.value.unshift(task)
    console.log('[createTask] 创建任务, taskId:', task.id, 'totalVMs:', task.totalVMs, '完整的task对象:', JSON.parse(JSON.stringify(task)))
    return task
  }

  function updateTaskStatus(id: string, status: TaskStatus, progress?: number) {
    const index = findTaskIndex(id)
    if (index !== -1) {
      const task = tasks.value[index]
      const now = status === 'running' && !task.started_at ? new Date().toISOString() : task.started_at
      const end = (status === 'completed' || status === 'failed' || status === 'cancelled') ? new Date().toISOString() : task.ended_at

      // 创建新对象替换，确保触发响应式更新
      const newTask = {
        ...task,
        status,
        progress: progress !== undefined ? progress : task.progress,
        started_at: now,
        ended_at: end
      }
      tasks.value[index] = newTask
      console.log('[updateTaskStatus] 更新任务状态, taskId:', id, 'status:', status, '更新前totalVMs:', task.totalVMs, '更新后totalVMs:', newTask.totalVMs)
    }
  }

  function updateTaskProgress(id: string, progress: number, currentStep?: string) {
    const index = findTaskIndex(id)
    if (index !== -1) {
      const task = tasks.value[index]
      tasks.value[index] = {
        ...task,
        progress,
        current_step: currentStep || task.current_step
      }
    }
  }

  function updateCollectionProgress(id: string, collected: number, total: number) {
    const index = findTaskIndex(id)
    if (index !== -1) {
      const task = tasks.value[index]
      tasks.value[index] = {
        ...task,
        collectedVMs: collected,
        totalVMs: total,
        progress: Math.floor((collected / total) * 100),
        current_step: '正在采集 ' + collected + '/' + total
      }
    }
  }

  function updateAnalysisResult(id: string, analysisType: keyof Task['analysisResults'], completed: boolean) {
    const index = findTaskIndex(id)
    if (index !== -1) {
      const task = tasks.value[index]
      if (task.analysisResults) {
        tasks.value[index] = {
          ...task,
          analysisResults: {
            ...task.analysisResults,
            [analysisType]: completed
          }
        }
        console.log('[updateAnalysisResult] 更新分析结果状态:', id, analysisType, completed, '新的 analysisResults:', tasks.value[index].analysisResults)
      }
    } else {
      console.warn('[updateAnalysisResult] 任务未找到:', id)
    }
  }

  function setTaskError(id: string, error: string) {
    const index = findTaskIndex(id)
    if (index !== -1) {
      const task = tasks.value[index]
      tasks.value[index] = {
        ...task,
        error,
        status: 'failed',
        ended_at: new Date().toISOString()
      }
    }
  }

  function pauseTask(id: string) {
    const index = findTaskIndex(id)
    if (index !== -1 && tasks.value[index].status === 'running') {
      tasks.value[index] = {
        ...tasks.value[index],
        status: 'paused'
      }
    }
  }

  function resumeTask(id: string) {
    const index = findTaskIndex(id)
    if (index !== -1 && tasks.value[index].status === 'paused') {
      tasks.value[index] = {
        ...tasks.value[index],
        status: 'running'
      }
    }
  }

  function cancelTask(id: string) {
    const index = findTaskIndex(id)
    if (index !== -1 && (tasks.value[index].status === 'running' || tasks.value[index].status === 'paused')) {
      tasks.value[index] = {
        ...tasks.value[index],
        status: 'cancelled',
        ended_at: new Date().toISOString()
      }
    }
  }

  function deleteTask(id: string) {
    const index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) {
      tasks.value.splice(index, 1)
    }
  }

  function clearCompletedTasks() {
    tasks.value = tasks.value.filter(t => t.status !== 'completed' && t.status !== 'failed' && t.status !== 'cancelled')
  }

  function setCurrentTask(task: Task | null) {
    currentTask.value = task
  }

  function resetCurrentTask() {
    currentTask.value = null
  }

  async function startCollectionTask(taskId: string, connectionId: number, selectedVMs: string[] = [], days: number = 30) {
    const index = findTaskIndex(taskId)
    if (index === -1) return

    try {
      updateTaskStatus(taskId, 'running', 0)

      const backendTaskId = await TaskAPI.createCollectTask({
        connection_id: connectionId,
        data_types: ['clusters', 'hosts', 'vms', 'metrics'],
        metrics_days: days,
        selected_vms: selectedVMs
      })

      // 更新 backendTaskId
      tasks.value[index] = {
        ...tasks.value[index],
        backendTaskId
      }

      pollTaskStatus(taskId, backendTaskId)
    } catch (e: any) {
      console.error('Task execution failed:', e)
      setTaskError(taskId, e.message || '执行异常')
      updateTaskStatus(taskId, 'failed')
    }
  }

  function pollTaskStatus(taskId: string, backendTaskId: number) {
    const pollInterval = setInterval(async () => {
      try {
        const taskInfo = await TaskAPI.getTask(backendTaskId)

        const index = findTaskIndex(taskId)
        if (index !== -1) {
          const task = tasks.value[index]
          tasks.value[index] = {
            ...task,
            status: taskInfo.status as TaskStatus,
            progress: taskInfo.progress
          }

          if (taskInfo.status === 'completed') {
            updateTaskStatus(taskId, 'completed', 100)
            clearInterval(pollInterval)
          } else if (taskInfo.status === 'failed') {
            setTaskError(taskId, taskInfo.error || '任务失败')
            clearInterval(pollInterval)
          }
        }
      } catch (e) {
        console.error('Failed to poll task status:', e)
      }
    }, 2000)

    setTimeout(() => {
      clearInterval(pollInterval)
      const index = findTaskIndex(taskId)
      if (index !== -1 && tasks.value[index].status === 'running') {
        updateTaskStatus(taskId, 'failed')
        setTaskError(taskId, '任务超时')
      }
    }, 5 * 60 * 1000)
  }

  async function syncTasksFromBackend() {
    try {
      // 显式传递参数，避免 Wails 绑定参数错乱
      const backendTasks = await TaskAPI.listTasks('', 100, 0)

      // 创建一个映射，用于快速查找现有任务
      const existingTasksMap = new Map<string, Task>()
      for (const task of tasks.value) {
        if (task.backendTaskId) {
          existingTasksMap.set(String(task.backendTaskId), task)
        }
      }

      // 合并后端数据与现有任务数据，保留所有前端字段
      tasks.value = backendTasks.map(bt => {
        const existing = existingTasksMap.get(String(bt.id))
        if (existing) {
          // 如果任务已存在，更新状态和进度，但保留其他所有字段
          return {
            ...existing,
            status: bt.status as TaskStatus,
            progress: bt.progress,
            error: bt.error,
            started_at: bt.started_at || existing.started_at,
            ended_at: bt.completed_at || existing.ended_at
          }
        } else {
          // 如果是新任务，创建基础对象
          return {
            id: 'backend_' + bt.id,
            backendTaskId: bt.id,
            type: bt.type as TaskType,
            name: bt.name,
            status: bt.status as TaskStatus,
            progress: bt.progress,
            error: bt.error,
            created_at: bt.created_at,
            started_at: bt.started_at,
            ended_at: bt.completed_at,
            canMinimize: true,
            // 初始化缺失的字段为默认值
            totalVMs: 0,
            collectedVMs: 0,
            analysisResults: {
              zombie: false,
              rightsize: false,
              tidal: false,
              health: false
            }
          }
        }
      })
    } catch (e: any) {
      console.error('Failed to sync tasks from backend:', e)
    }
  }

  return {
    tasks,
    runningTasks,
    currentTask,
    hasRunningTasks,
    getTask,
    createTask,
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
    setCurrentTask,
    resetCurrentTask,
    startCollectionTask,
    syncTasksFromBackend,
    pollTaskStatus
  }
})
