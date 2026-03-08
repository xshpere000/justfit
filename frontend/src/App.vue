<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/task'

const taskStore = useTaskStore()

// 页面关闭前检查是否有正在运行的任务
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (taskStore.hasRunningTasks) {
    e.preventDefault()
    e.returnValue = '有任务正在运行，确定要退出吗？'
    return '有任务正在运行，确定要退出吗？'
  }
}

onMounted(async () => {
  console.log('[App.vue] 应用初始化开始')
  console.log('[App.vue] 开始同步任务列表')

  try {
    await taskStore.syncTasksFromBackend()
    console.log('[App.vue] 任务列表同步完成，任务数量:', taskStore.tasks.length)
  } catch (error) {
    console.error('[App.vue] 任务列表同步失败:', error)
  }

  console.log('[App.vue] 启动全局任务轮询')
  taskStore.startPolling()

  // 3秒后验证轮询是否工作
  setTimeout(() => {
    console.log('[App.vue] 验证轮询状态...')
    const hasRunning = taskStore.tasks.some(t => t.status === 'running')
    console.log('[App.vue] 运行中的任务数量:', hasRunning)
  }, 3000)

  console.log('[App.vue] 应用初始化完成')

  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  console.log('[App.vue] 应用卸载，停止轮询定时器')
  taskStore.stopPolling()
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style>
/* 全局样式已在 global.scss 中定义 */

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
