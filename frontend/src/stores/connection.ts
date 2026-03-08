import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Connection, ConnectionCreate, ConnectionUpdate, ConnectionListResponse } from '@/api/connection'
import * as ConnectionAPI from '@/api/connection'

export const useConnectionStore = defineStore('connection', () => {
  // 状态
  const connections = ref<Connection[]>([])
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

  // 辅助函数：找到连接在数组中的索引
  function findConnectionIndex(id: number): number {
    return connections.value.findIndex((c) => c.id === id)
  }

  // 操作
  async function fetchConnections(params?: { page?: number; size?: number }) {
    loading.value = true
    error.value = null
    try {
      const result: ConnectionListResponse = await ConnectionAPI.listConnections(params)
      connections.value = result.items
    } catch (e: any) {
      error.value = e.message || '获取连接列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createConnection(data: ConnectionCreate): Promise<Connection> {
    loading.value = true
    error.value = null
    try {
      const newConnection = await ConnectionAPI.createConnection(data)
      connections.value.push(newConnection)
      return newConnection
    } catch (e: any) {
      error.value = e.message || '创建连接失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateConnection(id: number, data: ConnectionUpdate): Promise<Connection> {
    loading.value = true
    error.value = null
    try {
      const updated = await ConnectionAPI.updateConnection(id, data)
      const index = findConnectionIndex(id)
      if (index !== -1) {
        connections.value[index] = updated
      }
      return updated
    } catch (e: any) {
      error.value = e.message || '更新连接失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function testConnection(id: number): Promise<string> {
    error.value = null
    try {
      const result = await ConnectionAPI.testConnection(id)
      // 更新连接状态
      const index = findConnectionIndex(id)
      if (index !== -1) {
        connections.value[index] = {
          ...connections.value[index],
          status: result.status,
          lastSync: new Date().toISOString()
        }
      }
      return result.message
    } catch (e: any) {
      error.value = e.message || '测试连接失败'
      throw e
    }
  }

  async function deleteConnection(id: number): Promise<void> {
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

  function updateConnectionStatus(id: number, status: string, lastSync?: string | null) {
    const index = findConnectionIndex(id)
    if (index !== -1) {
      connections.value[index] = {
        ...connections.value[index],
        status,
        ...(lastSync !== undefined && { lastSync })
      }
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
    updateConnection,
    testConnection,
    deleteConnection,
    updateConnectionStatus
  }
})
