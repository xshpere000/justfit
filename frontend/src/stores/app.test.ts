/**
 * App Store tests
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAppStore } from './app'

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with default values', () => {
    const store = useAppStore()
    expect(store.sidebarCollapsed).toBe(false)
    expect(store.globalLoading).toBe(false)
    expect(store.currentConnectionId).toBeNull()
  })

  it('should toggle sidebar', () => {
    const store = useAppStore()
    expect(store.sidebarCollapsed).toBe(false)
    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(true)
    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(false)
  })

  it('should set global loading', () => {
    const store = useAppStore()
    store.setGlobalLoading(true)
    expect(store.globalLoading).toBe(true)
    store.setGlobalLoading(false)
    expect(store.globalLoading).toBe(false)
  })

  it('should set current connection', () => {
    const store = useAppStore()
    store.setCurrentConnectionId(123)
    expect(store.currentConnectionId).toBe(123)
    store.setCurrentConnectionId(null)
    expect(store.currentConnectionId).toBeNull()
  })

  it('should add and remove notifications', () => {
    const store = useAppStore()
    expect(store.notifications).toHaveLength(0)

    store.addNotification('Test notification', 'success')

    expect(store.notifications).toHaveLength(1)
    expect(store.notifications[0].message).toBe('Test notification')

    store.removeNotification(store.notifications[0].id)
    expect(store.notifications).toHaveLength(0)
  })
})
