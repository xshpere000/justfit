/**
 * Pinia Stores Index
 * Central export point for all stores
 */

export { useAppStore } from './app'
export { useConnectionStore } from './connection'
export { useTaskStore } from './task'

// Re-export types
export type { Task, TaskStatus, TaskType, TaskCreate } from '@/api/task'
export type { Connection, ConnectionCreate, ConnectionUpdate } from '@/api/connection'
