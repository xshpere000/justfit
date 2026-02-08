import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { TaskInfo } from '@/api/types'
import { ConnectionApi } from '@/api/connection'

export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
export type TaskType = 'collection' | 'analysis_zombie' | 'analysis_rightsize' | 'analysis_tidal' | 'analysis_health'

export interface Task extends TaskInfo {
  type: TaskType
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
  // 任务列表
  const tasks = ref<Task[]>([])

  // 当前正在运行的任务
  const runningTasks = computed(() =>
    tasks.value.filter(t => t.status === 'running')
  )

  // 当前任务（用于向导流程）
  const currentTask = ref<Task | null>(null)

  // 是否有正在运行的任务
  const hasRunningTasks = computed(() => runningTasks.value.length > 0)

  // 获取任务
  function getTask(id: string): Task | undefined {
    return tasks.value.find(t => t.id === id)
  }

  // 创建任务
  function createTask(params: CreateTaskParams): Task {
    const task: Task = {
      id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
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

  // 更新任务状态
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

  // 更新任务进度
  function updateTaskProgress(id: string, progress: number, currentStep?: string) {
    const task = getTask(id)
    if (task) {
      task.progress = progress
      if (currentStep) {
        task.current_step = currentStep
      }
    }
  }

  // 更新采集进度
  function updateCollectionProgress(id: string, collected: number, total: number) {
    const task = getTask(id)
    if (task) {
      task.collectedVMs = collected
      task.totalVMs = total
      task.progress = Math.floor((collected / total) * 100)
      task.current_step = `正在采集 ${collected}/${total}`
    }
  }

  // 更新分析结果状态
  function updateAnalysisResult(id: string, analysisType: keyof Task['analysisResults'], completed: boolean) {
    const task = getTask(id)
    if (task && task.analysisResults) {
      task.analysisResults[analysisType] = completed
    }
  }

  // 设置任务错误
  function setTaskError(id: string, error: string) {
    const task = getTask(id)
    if (task) {
      task.error = error
      task.status = 'failed'
      task.ended_at = new Date().toISOString()
    }
  }

  // 暂停任务
  function pauseTask(id: string) {
    const task = getTask(id)
    if (task && task.status === 'running') {
      task.status = 'paused'
    }
  }

  // 恢复任务
  function resumeTask(id: string) {
    const task = getTask(id)
    if (task && task.status === 'paused') {
      task.status = 'running'
    }
  }

  // 取消任务
  function cancelTask(id: string) {
    const task = getTask(id)
    if (task && (task.status === 'running' || task.status === 'paused')) {
      task.status = 'cancelled'
      task.ended_at = new Date().toISOString()
    }
  }

  // 删除任务
  function deleteTask(id: string) {
    const index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) {
      tasks.value.splice(index, 1)
    }
  }

  // 清空已完成的任务
  function clearCompletedTasks() {
    tasks.value = tasks.value.filter(t => t.status !== 'completed' && t.status !== 'failed' && t.status !== 'cancelled')
  }

  // 设置当前任务
  function setCurrentTask(task: Task | null) {
    currentTask.value = task
  }

  // 重置当前任务
  function resetCurrentTask() {
    currentTask.value = null
  }

  // 持久化任务到本地存储
  function saveTasksToStorage() {
    try {
      localStorage.setItem('justfit_tasks', JSON.stringify(tasks.value))
    } catch (e) {
      console.error('Failed to save tasks to storage:', e)
    }
  }

  // 从本地存储加载任务
  function loadTasksFromStorage() {
    try {
      const saved = localStorage.getItem('justfit_tasks')
      if (saved) {
        const parsedTasks = JSON.parse(saved) as Task[]
        // 重置所有运行中的任务为失败状态
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

  // 执行采集任务
  async function startCollectionTask(taskId: string, connectionId: number, days: number = 30) {
    const task = getTask(taskId)
    if (!task) return

    try {
      updateTaskStatus(taskId, 'running', 0)
      
      // 模拟一点进度以便用户知道开始运行了
      updateTaskProgress(taskId, 10)

      const result = await ConnectionApi.collectData({
        connection_id: connectionId,
        data_types: ['clusters', 'hosts', 'vms', 'metrics'],
        metrics_days: days
      })

      if (result.success) {
        updateTaskStatus(taskId, 'completed', 100)
        // 更新统计信息
        if (task.analysisResults) {
            // 这里仅仅是采集成功，分析结果还未生成
            // 接下来的逻辑是自动触发分析吗？通常是的。
            // 但为了简单起见，先把采集做实。
        }
      } else {
        setTaskError(taskId, result.message || '采集失败')
        updateTaskStatus(taskId, 'failed')
      }
    } catch (e: any) {
      console.error('Task execution failed:', e)
      setTaskError(taskId, e.message || '执行异常')
      updateTaskStatus(taskId, 'failed')
    }
  }

  // 监听任务变化自动保存
  watch(tasks, () => {
    saveTasksToStorage()
  }, { deep: true })

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
    startCollectionTask // Export this
  }
})
