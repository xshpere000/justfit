/**
 * API Client tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { apiClient } from './client'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      request: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('apiClient', () => {
  it('should be defined', () => {
    expect(apiClient).toBeDefined()
  })

  it('should have axios methods', () => {
    expect(apiClient).toHaveProperty('get')
    expect(apiClient).toHaveProperty('post')
    expect(apiClient).toHaveProperty('put')
    expect(apiClient).toHaveProperty('delete')
  })
})
