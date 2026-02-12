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

  function getTask(id: string): Task | undefined {
    return tasks.value.find(t => t.id === id)
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
    return task
  }

  function updateTaskStatus(id: string, status: TaskStatus, progress?: number) {
    const task = getTask(id)
    if (task) {
      task.status = status
      if (progress !== undefined) {
        task.progress = progress
      }
      if (status === 'running' && !task.started_at) {
        task.started_at = new Date().toISOString()
      }
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        task.ended_at = new Date().toISOString()
      }
    }
  }

  function updateTaskProgress(id: string, progress: number, currentStep?: string) {
    const task = getTask(id)
    if (task) {
      task.progress = progress
      if (currentStep) {
        task.current_step = currentStep
      }
    }
  }

  function updateCollectionProgress(id: string, collected: number, total: number) {
    const task = getTask(id)
    if (task) {
      task.collectedVMs = collected
      task.totalVMs = total
      task.progress = Math.floor((collected / total) * 100)
      task.current_step = '正在采集 ' + collected + '/' + total
    }
  }

  function updateAnalysisResult(id: string, analysisType: keyof Task['analysisResults'], completed: boolean) {
    const task = getTask(id)
    if (task && task.analysisResults) {
      task.analysisResults[analysisType] = completed
    }
  }

  function setTaskError(id: string, error: string) {
    const task = getTask(id)
    if (task) {
      task.error = error
      task.status = 'failed'
      task.ended_at = new Date().toISOString()
    }
  }

  function pauseTask(id: string) {
    const task = getTask(id)
    if (task && task.status === 'running') {
      task.status = 'paused'
    }
  }

  function resumeTask(id: string) {
    const task = getTask(id)
    if (task && task.status === 'paused') {
      task.status = 'running'
    }
  }

  function cancelTask(id: string) {
    const task = getTask(id)
    if (task && (task.status === 'running' || task.status === 'paused')) {
      task.status = 'cancelled'
      task.ended_at = new Date().toISOString()
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

  async function startCollectionTask(taskId: string, connectionId: number, days: number = 30) {
    const task = getTask(taskId)
    if (!task) return

    try {
      updateTaskStatus(taskId, 'running', 0)

      const backendTaskId = await TaskAPI.createCollectTask({
        connection_id: connectionId,
        data_types: ['clusters', 'hosts', 'vms', 'metrics'],
        metrics_days: days
      })

      task.backendTaskId = backendTaskId

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

        const task = getTask(taskId)
        if (task) {
          task.status = taskInfo.status as TaskStatus
          task.progress = taskInfo.progress

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
      const task = getTask(taskId)
      if (task && task.status === 'running') {
        updateTaskStatus(taskId, 'failed')
        task.error = '任务超时'
      }
    }, 5 * 60 * 1000)
  }

  async function syncTasksFromBackend() {
    try {
      const backendTasks = await TaskAPI.listTasks()

      tasks.value = backendTasks.map(bt => ({
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
        canMinimize: true
      }))
    } catch (e: any) {
      console.error('Failed to sync tasks from backend:', e)
    }
  }

  function saveTasksToStorage() {
    try {
      localStorage.setItem('justfit_tasks', JSON.stringify(tasks.value))
    } catch (e) {
      console.error('Failed to save tasks to storage:', e)
    }
  }

  function loadTasksFromStorage() {
    try {
      const saved = localStorage.getItem('justfit_tasks')
      if (saved) {
        const parsedTasks = JSON.parse(saved) as Task[]
        parsedTasks.forEach(task => {
          if (task.status === 'running') {
            task.status = 'failed'
            task.error = '任务被中断'
            task.ended_at = new Date().toISOString()
          }
        })
        tasks.value = parsedTasks
      }
    } catch (e) {
      console.error('Failed to load tasks from storage:', e)
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
    saveTasksToStorage,
    loadTasksFromStorage,
    startCollectionTask,
    syncTasksFromBackend,
    pollTaskStatus
  }
})
