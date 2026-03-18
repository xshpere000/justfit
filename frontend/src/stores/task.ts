import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Task, TaskCreate, TaskStatus, TaskListResponse } from '@/api/task'
import * as TaskAPI from '@/api/task'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const runningTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'running')
  )

  const hasRunningTasks = computed(() => runningTasks.value.length > 0)

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
      console.log(
        '[TaskStore] 任务详情:',
        result.items.map((t) => ({ id: t.id, name: t.name, status: t.status, progress: t.progress }))
      )

      tasks.value = result.items

      console.log('[TaskStore] tasks.value 已更新，当前任务数量:', tasks.value.length)
    } catch (e: any) {
      error.value = e.message || '同步任务列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

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

  function getTask(id: number): Task | undefined {
    return tasks.value.find((t) => t.id === id)
  }

  function updateTask(id: number, updates: Partial<Task>) {
    const index = tasks.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      tasks.value[index] = { ...tasks.value[index], ...updates }
    }
  }

  async function fetchTaskDetail(id: number) {
    loading.value = true
    error.value = null
    try {
      const detail = await TaskAPI.getTaskDetail(id)
      const index = tasks.value.findIndex((t) => t.id === id)
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

  async function deleteTask(id: number) {
    loading.value = true
    error.value = null
    try {
      await TaskAPI.deleteTask(id)
      tasks.value = tasks.value.filter((t) => t.id !== id)
    } catch (e: any) {
      error.value = e.message || '删除任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  let pollTimer: ReturnType<typeof setTimeout> | null = null
  let isPolling = false
  let consecutiveFailures = 0
  let currentPollInterval = 2000
  let pollRequestInFlight = false
  let latestPollRequestId = 0
  let latestAppliedPollRequestId = 0
  const MAX_CONSECUTIVE_FAILURES = 3
  const MAX_POLL_INTERVAL = 30000

  async function pollOnce() {
    if (pollRequestInFlight) {
      console.log('[TaskStore] pollOnce skipped: previous request still in flight')
      return
    }

    const pollStart = Date.now()
    const requestId = ++latestPollRequestId
    pollRequestInFlight = true
    console.log('[TaskStore] 轮询开始', { requestId, time: new Date().toLocaleTimeString() })

    try {
      const result: TaskListResponse = await TaskAPI.listTasks()
      const pollElapsed = Date.now() - pollStart
      console.log('[TaskStore] 轮询完成', {
        requestId,
        count: result.items.length,
        elapsed: `${pollElapsed}ms`
      })

      if (requestId > latestAppliedPollRequestId) {
        latestAppliedPollRequestId = requestId
        tasks.value = result.items
      } else {
        console.log('[TaskStore] stale poll response ignored', { requestId, latestAppliedPollRequestId })
      }

      consecutiveFailures = 0
      if (currentPollInterval > 2000) {
        console.log('[TaskStore] 后端恢复正常，轮询间隔重置为 2000ms')
        restartPollingWithInterval(2000)
      }
    } catch (pollError) {
      const pollElapsed = Date.now() - pollStart
      console.error('[TaskStore] 轮询同步失败', { error: pollError, elapsed: `${pollElapsed}ms` })

      consecutiveFailures++
      console.warn(`[TaskStore] 连续失败次数: ${consecutiveFailures}/${MAX_CONSECUTIVE_FAILURES}`)

      if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
        const newInterval = Math.min(currentPollInterval * 2, MAX_POLL_INTERVAL)
        if (newInterval !== currentPollInterval) {
          console.warn(`[TaskStore] 连续失败 ${consecutiveFailures} 次，轮询间隔调整为 ${newInterval}ms`)
          restartPollingWithInterval(newInterval)
        }
      }
    } finally {
      pollRequestInFlight = false
    }
  }

  function scheduleNextPoll(intervalMs: number) {
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }

    if (!isPolling) {
      return
    }

    pollTimer = setTimeout(async () => {
      if (!isPolling) {
        return
      }

      await pollOnce()
      scheduleNextPoll(currentPollInterval)
    }, intervalMs)
  }

  function restartPollingWithInterval(intervalMs: number) {
    currentPollInterval = intervalMs
    scheduleNextPoll(intervalMs)
  }

  function startPolling(intervalMs: number = 2000) {
    if (isPolling && currentPollInterval === intervalMs) {
      console.log('[TaskStore] startPolling skipped: already polling with same interval')
      return
    }

    stopPolling()
    isPolling = true
    consecutiveFailures = 0
    currentPollInterval = intervalMs
    console.log('[TaskStore] startPolling', { intervalMs })

    void pollOnce()
    scheduleNextPoll(intervalMs)
  }

  function stopPolling() {
    console.log('[TaskStore] stopPolling', { pollTimer })
    isPolling = false
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

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
    startPolling,
    stopPolling,
    init
  }
})
