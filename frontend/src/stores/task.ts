import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Task, TaskCreate, TaskStatus, TaskListResponse } from '@/api/task'
import * as TaskAPI from '@/api/task'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const runningTasks = computed(() =>
    tasks.value.filter(t => t.status === 'running')
  )

  const hasRunningTasks = computed(() => runningTasks.value.length > 0)

  // 从后端同步任务列表（唯一数据源）
  async function syncTasksFromBackend(params?: {
    type?: Task['type']
    status?: TaskStatus
    page?: number
    size?: number
  }) {
    loading.value = true
    error.value = null
    try {
      const result: TaskListResponse = await TaskAPI.listTasks(params)
      console.log('[TaskStore] syncTasksFromBackend: 收到', result.items.length, '个任务')
      console.log('[TaskStore] 任务详情:', result.items.map(t => ({ id: t.id, name: t.name, status: t.status, progress: t.progress })))

      // 直接替换数组，触发响应式更新
      tasks.value = result.items

      console.log('[TaskStore] tasks.value 已更新，当前任务数量:', tasks.value.length)
    } catch (e: any) {
      error.value = e.message || '同步任务列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 创建任务
  async function createTask(params: TaskCreate): Promise<Task> {
    loading.value = true
    error.value = null
    try {
      const newTask = await TaskAPI.createTask(params)
      tasks.value.push(newTask)
      return newTask
    } catch (e: any) {
      error.value = e.message || '创建任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 获取单个任务
  function getTask(id: number): Task | undefined {
    return tasks.value.find(t => t.id === id)
  }

  // 更新任务状态（使用对象替换确保响应式更新）
  function updateTask(id: number, updates: Partial<Task>) {
    const index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) {
      tasks.value[index] = { ...tasks.value[index], ...updates }
    }
  }

  // 获取任务详情
  async function fetchTaskDetail(id: number) {
    loading.value = true
    error.value = null
    try {
      const detail = await TaskAPI.getTaskDetail(id)
      // 更新任务列表中的对应项
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index] = detail
      }
      return detail
    } catch (e: any) {
      error.value = e.message || '获取任务详情失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 取消任务
  async function cancelTask(id: number) {
    loading.value = true
    error.value = null
    try {
      await TaskAPI.cancelTask(id)
      updateTask(id, { status: 'cancelled' })
    } catch (e: any) {
      error.value = e.message || '取消任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 删除任务
  async function deleteTask(id: number) {
    loading.value = true
    error.value = null
    try {
      await TaskAPI.deleteTask(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
    } catch (e: any) {
      error.value = e.message || '删除任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 暂停任务（暂未实现，后端缺少对应API）
  async function pauseTask(id: number) {
    // TODO: 等待后端实现暂停任务API
    throw new Error('暂停任务功能暂未实现，请使用取消任务功能')
  }

  // 恢复任务（暂未实现，后端缺少对应API）
  async function resumeTask(id: number) {
    // TODO: 等待后端实现恢复任务API
    throw new Error('恢复任务功能暂未实现，请创建新任务')
  }

  // 清除已完成的任务
  function clearCompletedTasks() {
    tasks.value = tasks.value.filter(
      t => t.status !== 'completed' && t.status !== 'failed' && t.status !== 'cancelled'
    )
  }

  // 轮询运行中的任务
  let pollInterval: ReturnType<typeof setInterval> | null = null
  let isPolling = false
  let consecutiveFailures = 0
  let currentPollInterval = 2000
  const MAX_CONSECUTIVE_FAILURES = 3
  const MAX_POLL_INTERVAL = 30000 // 最大轮询间隔30秒

  async function pollOnce() {
    const pollStart = Date.now()
    console.log(`[TaskStore] 轮询开始`, { time: new Date().toLocaleTimeString() })
    try {
      // 轮询请求使用默认超时（API 慢是正常的）
      const result: TaskListResponse = await TaskAPI.listTasks()
      const pollElapsed = Date.now() - pollStart
      console.log(`[TaskStore] 轮询完成，收到 ${result.items.length} 个任务`, { elapsed: `${pollElapsed}ms` })

      // 直接更新任务列表
      tasks.value = result.items

      // 成功后重置失败计数和轮询间隔
      consecutiveFailures = 0
      if (currentPollInterval > 2000) {
        currentPollInterval = 2000
        console.log('[TaskStore] 后端恢复正常，重置轮询间隔为 2000ms')
        restartPollingWithInterval(2000)
      }
    } catch (error) {
      const pollElapsed = Date.now() - pollStart
      console.error(`[TaskStore] 轮询同步失败`, { error, elapsed: `${pollElapsed}ms` })

      consecutiveFailures++
      console.warn(`[TaskStore] 连续失败次数: ${consecutiveFailures}/${MAX_CONSECUTIVE_FAILURES}`)

      // 连续失败后，降低轮询频率，避免控制台刷屏
      if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
        const newInterval = Math.min(currentPollInterval * 2, MAX_POLL_INTERVAL)
        if (newInterval !== currentPollInterval) {
          currentPollInterval = newInterval
          console.warn(`[TaskStore] 连续失败${consecutiveFailures}次，降低轮询频率为 ${newInterval}ms`)
          restartPollingWithInterval(newInterval)
        }
      }
    }
  }

  function restartPollingWithInterval(intervalMs: number) {
    if (pollInterval) {
      clearInterval(pollInterval)
    }
    pollInterval = setInterval(() => {
      if (isPolling) {
        console.log('[TaskStore] setInterval 触发')
        pollOnce()
      } else {
        console.log('[TaskStore] setInterval 触发但 isPolling=false，跳过')
      }
    }, intervalMs)
  }

  function startPolling(intervalMs: number = 2000) {
    stopPolling()
    isPolling = true
    consecutiveFailures = 0
    currentPollInterval = intervalMs
    console.log('[TaskStore] startPolling: 启动轮询，间隔', intervalMs, 'ms')

    // 立即执行一次，避免等待第一个 interval
    pollOnce()

    pollInterval = setInterval(() => {
      if (isPolling) {
        console.log('[TaskStore] setInterval 触发')
        pollOnce()
      } else {
        console.log('[TaskStore] setInterval 触发但 isPolling=false，跳过')
      }
    }, intervalMs)

    console.log('[TaskStore] setInterval ID:', pollInterval)
  }

  function stopPolling() {
    console.log('[TaskStore] stopPolling: 停止轮询, pollInterval:', pollInterval)
    isPolling = false
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
      console.log('[TaskStore] 轮询已停止')
    } else {
      console.warn('[TaskStore] stopPolling: pollInterval 为 null，没有需要停止的轮询')
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
    getTask,
    updateTask,
    fetchTaskDetail,
    cancelTask,
    deleteTask,
    pauseTask,
    resumeTask,
    clearCompletedTasks,
    startPolling,
    stopPolling,
    init
  }
})
