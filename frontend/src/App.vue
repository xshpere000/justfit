<template>
  <router-view />

  <!-- 版本升级对话框 -->
  <VersionUpgradeDialog
    v-model="showUpgradeDialog"
    :version-info="versionInfo"
    @confirmed="handleUpgradeConfirmed"
    @cancelled="handleUpgradeCancelled"
  />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useTaskStore } from '@/stores/task'
import { VersionApi } from '@/api/connection'
import VersionUpgradeDialog from '@/components/VersionUpgradeDialog.vue'
import type { VersionCheckResult } from '@/types/api'

const taskStore = useTaskStore()

// 版本升级相关
const showUpgradeDialog = ref(false)
const versionInfo = ref<VersionCheckResult | null>(null)
let hasCheckedVersion = false

// 检查版本
async function checkAppVersion() {
  if (hasCheckedVersion) return
  hasCheckedVersion = true

  try {
    const result = await VersionApi.checkVersion()
    console.log('[VersionCheck] 版本检查结果:', result)

    if (result.needsRebuild) {
      // 需要大版本升级，显示对话框
      versionInfo.value = result
      showUpgradeDialog.value = true
    }
  } catch (error) {
    console.error('[VersionCheck] 版本检查失败:', error)
  }
}

// 版本升级确认
function handleUpgradeConfirmed() {
  console.log('[VersionCheck] 用户确认升级')
  // 重建完成后重新加载页面或刷新数据
  setTimeout(() => {
    window.location.reload()
  }, 2000)
}

// 版本升级取消
function handleUpgradeCancelled() {
  console.log('[VersionCheck] 用户取消升级，退出应用')
  // 用户选择取消，关闭应用
  window.close()
}

// 页面关闭前检查是否有正在运行的任务
function handleBeforeUnload(e: BeforeUnloadEvent) {
  // 如果版本升级对话框显示中，不允许关闭
  if (showUpgradeDialog.value) {
    e.preventDefault()
    e.returnValue = '请先完成版本升级'
    return '请先完成版本升级'
  }

  if (taskStore.hasRunningTasks) {
    e.preventDefault()
    e.returnValue = '有任务正在运行，确定要退出吗？'
    return '有任务正在运行，确定要退出吗？'
  }
}

onMounted(async () => {
  console.log('[App.vue] onMounted 应用初始化开始')

  // 先检查版本
  await checkAppVersion()

  // 如果需要升级，不继续初始化
  if (showUpgradeDialog.value) {
    console.log('[App.vue] 需要版本升级，暂停初始化')
    return
  }

  console.log('[App.vue] 开始同步任务列表')
  await taskStore.syncTasksFromBackend()
  console.log('[App.vue] 启动全局任务轮询')
  taskStore.startPolling()
  console.log('[App.vue] 应用初始化完成')

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
