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
  await taskStore.syncTasksFromBackend()

  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
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
