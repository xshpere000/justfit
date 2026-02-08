import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 侧边栏状态
  const sidebarCollapsed = ref(false)

  // 加载状态
  const globalLoading = ref(false)

  // 当前连接
  const currentConnectionId = ref<number | null>(null)

  // 通知
  const notifications = ref<Array<{ id: string; message: string; type: string }>>([])

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarCollapsed(collapsed: boolean) {
    sidebarCollapsed.value = collapsed
  }

  function setGlobalLoading(loading: boolean) {
    globalLoading.value = loading
  }

  function setCurrentConnectionId(id: number | null) {
    currentConnectionId.value = id
  }

  function addNotification(message: string, type: 'success' | 'warning' | 'error' | 'info') {
    const id = Date.now().toString()
    notifications.value.push({ id, message, type })
    // 3秒后自动移除
    setTimeout(() => {
      removeNotification(id)
    }, 3000)
  }

  function removeNotification(id: string) {
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function clearNotifications() {
    notifications.value = []
  }

  return {
    sidebarCollapsed,
    globalLoading,
    currentConnectionId,
    notifications,
    toggleSidebar,
    setSidebarCollapsed,
    setGlobalLoading,
    setCurrentConnectionId,
    addNotification,
    removeNotification,
    clearNotifications
  }
})
