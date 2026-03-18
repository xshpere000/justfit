/**
 * AppShell Component tests
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import AppShell from './AppShell.vue'

const { fetchConnectionsMock, checkBackendHealthMock } = vi.hoisted(() => ({
  fetchConnectionsMock: vi.fn().mockResolvedValue(undefined),
  checkBackendHealthMock: vi.fn().mockResolvedValue(true),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: { title: '首页' } }),
}))

vi.mock('@/stores/connection', () => ({
  useConnectionStore: () => ({
    fetchConnections: fetchConnectionsMock,
  }),
}))

vi.mock('@/api/client', () => ({
  checkBackendHealth: checkBackendHealthMock,
}))

describe('AppShell', () => {
  it('should render component', () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [createPinia(), ElementPlus],
        stubs: ['router-view'],
      },
    })

    expect(wrapper.find('.app-shell').exists()).toBe(true)
  })

  it('should render header with title', () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [createPinia(), ElementPlus],
        stubs: ['router-view'],
      },
    })

    expect(wrapper.find('.app-header').exists()).toBe(true)
    expect(wrapper.find('.page-title').text()).toBe('首页')
  })

  it('should render version badge', () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [createPinia(), ElementPlus],
        stubs: ['router-view'],
      },
    })

    expect(wrapper.find('.version-badge').exists()).toBe(true)
  })
})
