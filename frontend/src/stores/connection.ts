import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionInfo, CreateConnectionRequest } from '@/api/types'
import * as ConnectionAPI from '@/api/connection'

export const useConnectionStore = defineStore('connection', () => {
  // 状态
  const connections = ref<ConnectionInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const connectedCount = computed(() =>
    connections.value.filter((c) => c.status === 'connected').length
  )

  const disconnectedCount = computed(() =>
    connections.value.filter((c) => c.status === 'disconnected').length
  )

  const errorCount = computed(() =>
    connections.value.filter((c) => c.status === 'error').length
  )

  const connectionById = computed(() => (id: number) =>
    connections.value.find((c) => c.id === id)
  )

  const activeConnections = computed(() =>
    connections.value.filter((c) => c.status === 'connected')
  )

  // 操作
  async function fetchConnections() {
    loading.value = true
    error.value = null
    try {
      connections.value = await ConnectionAPI.listConnections()
    } catch (e: any) {
      error.value = e.message || '获取连接列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createConnection(data: CreateConnectionRequest) {
    loading.value = true
    error.value = null
    try {
      await ConnectionAPI.createConnection(data)
      await fetchConnections()
    } catch (e: any) {
      error.value = e.message || '创建连接失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function testConnection(id: number) {
    error.value = null
    try {
      const status = await ConnectionAPI.testConnection(id)
      // 更新连接状态
      const conn = connections.value.find((c) => c.id === id)
      if (conn) {
        conn.status = status
      }
      return status
    } catch (e: any) {
      error.value = e.message || '测试连接失败'
      throw e
    }
  }

  async function deleteConnection(id: number) {
    loading.value = true
    error.value = null
    try {
      await ConnectionAPI.deleteConnection(id)
      connections.value = connections.value.filter((c) => c.id !== id)
    } catch (e: any) {
      error.value = e.message || '删除连接失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function updateConnectionStatus(id: number, status: string) {
    const conn = connections.value.find((c) => c.id === id)
    if (conn) {
      conn.status = status
    }
  }

  return {
    connections,
    loading,
    error,
    connectedCount,
    disconnectedCount,
    errorCount,
    connectionById,
    activeConnections,
    fetchConnections,
    createConnection,
    testConnection,
    deleteConnection,
    updateConnectionStatus
  }
})
