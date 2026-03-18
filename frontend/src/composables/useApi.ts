/**
 * API 调用组合函数
 * 提供统一的错误处理和加载状态管理
 */

import type { Ref } from 'vue'

export function useApi() {
  /**
   * 包装 API 调用，统一处理错误和加载状态
   */
  async function callApi<T>(
    apiFn: () => Promise<T>,
    options: {
      loading?: Ref<boolean>
      error?: Ref<string | null>
    } = {}
  ): Promise<T> {
    const { loading, error } = options

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

  return {
    callApi,
    callMultiple
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
