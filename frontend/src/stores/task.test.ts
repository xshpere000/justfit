/**
 * Task Store tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTaskStore } from './task'

// Mock API
vi.mock('../api/task', () => ({
  listTasks: vi.fn(() => Promise.resolve({
    data: { data: { items: [], total: 0 } }
  })),
  createTask: vi.fn(() => Promise.resolve({
    data: { data: { id: 1, name: 'Test Task', type: 'collection', status: 'pending' } }
  })),
  cancelTask: vi.fn(),
  deleteTask: vi.fn(),
}))

describe('useTaskStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with empty tasks', () => {
    const store = useTaskStore()
    expect(store.tasks).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('should have runningTasks getter', () => {
    const store = useTaskStore()
    store.tasks = [
      { id: 1, name: 'Running Task', status: 'running' as const, type: 'collection' as const },
      { id: 2, name: 'Completed Task', status: 'completed' as const, type: 'collection' as const },
    ] as any
    expect(store.runningTasks).toHaveLength(1)
    expect(store.runningTasks[0].id).toBe(1)
  })

  it('should have hasRunningTasks getter', () => {
    const store = useTaskStore()
    expect(store.hasRunningTasks).toBe(false)

    store.tasks = [
      { id: 1, name: 'Running Task', status: 'running' as const, type: 'collection' as const },
    ] as any
    expect(store.hasRunningTasks).toBe(true)
  })
})
