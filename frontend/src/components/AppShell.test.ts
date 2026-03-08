/**
 * AppShell Component tests
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import AppShell from './AppShell.vue'

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
  })

  it('should have window controls', () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [createPinia(), ElementPlus],
        stubs: ['router-view'],
      },
    })

    expect(wrapper.find('.window-controls').exists()).toBe(true)
  })
})
