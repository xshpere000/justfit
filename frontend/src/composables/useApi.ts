/**
 * API 调用组合函数
 * 提供统一的错误处理和加载状态管理
 */

import { ref } from 'vue'
import type { Ref } from 'vue'

export interface ApiResult<T> {
  data: T | null
  error: string | null
  loading: boolean
}

export function useApi() {
  /**
   * 包装 API 调用，统一处理错误和加载状态
   */
  async function callApi<T>(
    apiFn: () => Promise<T>,
    options: {
      loading?: Ref<boolean>
      error?: Ref<string | null>
      successMessage?: string
    } = {}
  ): Promise<T> {
    const { loading, error, successMessage } = options

    try {
      if (loading) loading.value = true
      if (error) error.value = null

      const result = await apiFn()
      return result
    } catch (err: any) {
      const errorMsg = err.response?.data?.error?.message || err.message || '操作失败'
      if (error) error.value = errorMsg
      throw err
    } finally {
      if (loading) loading.value = false
    }
  }

  /**
   * 批量调用 API
   */
  async function callMultiple<T>(
    apiFns: Array<() => Promise<T>>,
    options: {
      loading?: Ref<boolean>
    } = {}
  ): Promise<T[]> {
    const { loading } = options

    try {
      if (loading) loading.value = true
      const results = await Promise.all(apiFns.map(fn => fn()))
      return results
    } finally {
      if (loading) loading.value = false
    }
  }

  /**
   * 轮询 API
   */
  function pollApi<T>(
    apiFn: () => Promise<T>,
    condition: (data: T) => boolean,
    options: {
      interval?: number
      maxAttempts?: number
      loading?: Ref<boolean>
    } = {}
  ) {
    const {
      interval = 2000,
      maxAttempts = 300,  // 10 minutes
      loading
    } = options

    let attempts = 0
    let timer: ReturnType<typeof setInterval> | null = null

    const stop = () => {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
      if (loading) loading.value = false
    }

    const start = async () => {
      if (loading) loading.value = true

      try {
        const result = await apiFn()

        if (condition(result) || attempts >= maxAttempts) {
          stop()
          return result
        }

        attempts++
      } catch (err) {
        if (attempts >= maxAttempts) {
          stop()
          throw err
        }
        attempts++
      }
    }

    timer = setInterval(start, interval)
    start()

    return { stop }
  }

  return {
    callApi,
    callMultiple,
    pollApi
  }
}

/**
 * 创建可重试的 API 调用
 */
export function useRetryApi(maxRetries = 3, delay = 1000) {
  return async function retryApi<T>(apiFn: () => Promise<T>): Promise<T> {
    let lastError: any

    for (let i = 0; i < maxRetries; i++) {
      try {
        return await apiFn()
      } catch (err) {
        lastError = err
        if (i < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay * (i + 1)))
        }
      }
    }

    throw lastError
  }
}
