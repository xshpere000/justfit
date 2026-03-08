/**
 * Format utility tests
 */

import { describe, it, expect } from 'vitest'
import { formatBytes, formatNumber, formatPercent, getCpuUsagePercent, getMemoryUsagePercent } from './format'

describe('formatBytes', () => {
  it('should format bytes correctly', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(1024)).toBe('1 KB')
    expect(formatBytes(1024 * 1024)).toBe('1 MB')
    expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB')
    expect(formatBytes(1024 * 1024 * 1024 * 1024)).toBe('1 TB')
  })

  it('should handle decimal values', () => {
    expect(formatBytes(1536)).toBe('1.5 KB')
    expect(formatBytes(1048576 * 1.5)).toBe('1.5 MB')
  })
})

describe('formatNumber', () => {
  it('should format numbers with locale', () => {
    expect(formatNumber(1000)).toBe('1,000')
    expect(formatNumber(1000000)).toBe('1,000,000')
    expect(formatNumber(0)).toBe('0')
  })
})

describe('formatPercent', () => {
  it('should format percentages', () => {
    expect(formatPercent(0.5)).toBe('50%')
    expect(formatPercent(1)).toBe('100%')
    expect(formatPercent(0.123)).toBe('12.3%')
  })
})

describe('getCpuUsagePercent', () => {
  it('should convert CPU metrics to percentage', () => {
    // 100 MHz from 1000 MHz CPU = 10%
    expect(getCpuUsagePercent(100, 1000)).toBe(10)
    expect(getCpuUsagePercent(500, 1000)).toBe(50)
    expect(getCpuUsagePercent(0, 1000)).toBe(0)
  })

  it('should handle zero CPU capacity', () => {
    expect(getCpuUsagePercent(100, 0)).toBe(0)
  })
})

describe('getMemoryUsagePercent', () => {
  it('should convert memory bytes to percentage', () => {
    // 512 MB used of 1024 MB = 50%
    const used = 512 * 1024 * 1024
    const total = 1024 * 1024 * 1024
    expect(getMemoryUsagePercent(used, total)).toBe(50)
  })

  it('should handle zero memory capacity', () => {
    expect(getMemoryUsagePercent(1024, 0)).toBe(0)
  })
})
