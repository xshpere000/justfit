/**
 * Format utility tests
 */

import { describe, it, expect } from 'vitest'
import { formatBytes, formatNumber, formatPercent } from './format'

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
    expect(formatPercent(0.5)).toBe('0.50%')
    expect(formatPercent(1)).toBe('1.00%')
    expect(formatPercent(12.345, 1)).toBe('12.3%')
  })
})
