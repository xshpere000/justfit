<template>
  <el-container class="app-shell">
    <!-- 主内容区 -->
    <el-container class="app-main">
      <!-- 顶部栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <!-- Logo 和标题 -->
          <div class="logo" @click="goHome">
            <img src="@/assets/images/logo.png" alt="JustFit Logo" class="logo-image" />
            <span class="version-text">v{{ appVersion }}<template v-if="isDevVersion"> 开发版</template></span>
          </div>

          <!-- 返回按钮 -->
          <el-button
            v-if="showBackButton"
            :icon="'ArrowLeft'"
            text
            @click="goBack"
          >
            返回
          </el-button>
        </div>

        <div class="header-center">
          <!-- 页面标题 -->
          <div class="page-title">{{ currentRouteTitle }}</div>
        </div>

        <div class="header-right">
          <!-- 窗口控制按钮 - macOS 风格 -->
          <div class="window-controls">
            <button class="window-control-btn window-control-btn--close" @click="closeWindow" title="关闭">
              <el-icon><Close /></el-icon>
            </button>
            <button class="window-control-btn window-control-btn--minimize" @click="minimizeWindow" title="最小化">
              <el-icon><Minus /></el-icon>
            </button>
            <button class="window-control-btn window-control-btn--maximize" @click="toggleMaximize" title="最大化/还原">
              <el-icon><FullScreen v-if="!isMaximized" /><CopyDocument v-else /></el-icon>
            </button>
          </div>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="app-content">
        <router-view v-slot="{ Component }">
          <keep-alive exclude="Wizard">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>

    <!-- 通知 -->
    <div class="notifications">
      <transition-group name="notification">
        <div
          v-for="notification in appStore.notifications"
          :key="notification.id"
          class="notification-item"
          :class="'notification-item--' + notification.type"
        >
          <el-icon class="notification-icon">
            <component
              :is="
                notification.type === 'success'
                  ? 'CircleCheck'
                  : notification.type === 'error'
                    ? 'CircleClose'
                    : 'Warning'
              "
            />
          </el-icon>
          <span>{{ notification.message }}</span>
        </div>
      </transition-group>
    </div>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useConnectionStore } from '@/stores/connection'
import { useTaskStore } from '@/stores/task'
import { useAppStore } from '@/stores/app'
import { checkBackendHealth } from '@/api/client'
import type { AppVersionInfo } from '@/types/api'
import {
  ArrowLeft,
  CircleCheck,
  CircleClose,
  Warning,
  Minus,
  FullScreen,
  CopyDocument,
  Close
} from '@element-plus/icons-vue'

const router = useRouter()
const isMaximized = ref(false)
const route = useRoute()
const connectionStore = useConnectionStore()
const taskStore = useTaskStore()
const appStore = useAppStore()

// 版本信息
const appVersion = ref('0.0.3')
const isDevVersion = ref(false)

const currentRouteTitle = computed(() => route.meta?.title || '首页')

// 是否显示返回按钮（在非首页时显示）
const showBackButton = computed(() => {
  return route.path !== '/' && route.path !== '' && !route.path.startsWith('/wizard')
})

function goHome() {
  router.push('/')
}

function goBack() {
  if (route.path.startsWith('/task/')) {
    // 从任务详情返回首页
    router.push('/')
  } else {
    // 其他情况返回上一页
    router.back()
  }
}

function goToSettings() {
  router.push('/settings')
}

// 窗口控制函数 - 仅在 Electron 环境中可用
function minimizeWindow() {
  if (window.electronAPI?.minimize) {
    window.electronAPI.minimize()
  }
}

function toggleMaximize() {
  if (window.electronAPI?.toggleMaximize) {
    window.electronAPI.toggleMaximize()
    isMaximized.value = !isMaximized.value
  }
}

async function closeWindow() {
  // 仅在 Electron 环境中允许关闭
  if (!window.electronAPI?.close) {
    console.log('Close window: 仅在 Electron 应用中可用')
    return
  }

  try {
    const hasRunningTasks = taskStore.hasRunningTasks
    const message = hasRunningTasks
      ? '当前有任务正在运行，关闭应用可能中断任务。确定要关闭应用吗？'
      : '确定要关闭应用吗？'

    await ElMessageBox.confirm(
      message,
      '退出确认',
      {
        type: hasRunningTasks ? 'error' : 'warning',
        confirmButtonText: '确认关闭',
        cancelButtonText: '取消'
      }
    )
    window.electronAPI.close()
  } catch {
    // 用户取消关闭
  }
}

// 检查是否在 Electron 环境中
const isElectron = computed(() => {
  return typeof window !== 'undefined' && window.electronAPI
})


onMounted(async () => {
  // 加载连接列表
  try {
    await connectionStore.fetchConnections()
  } catch (error) {
    console.error('[AppShell] Failed to load connections:', error)
  }

  // 检查后端健康状态（静默检查，不弹窗）
  // 网络错误已在 API 拦截器中处理
  try {
    const isHealthy = await checkBackendHealth()
    console.log('[AppShell] Backend health check:', isHealthy ? 'OK' : 'Not healthy')
    // 不再弹窗，因为网络错误已经有详细的控制台日志
  } catch (error) {
    console.log('[AppShell] Backend health check skipped (network error, see console for details)')
  }
})
</script>

<style scoped lang="scss">
.app-shell {
  height: 100%;
  background: $background-color-base;
}

.app-main {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  background: #fff;
  border-bottom: 1px solid $border-color-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $spacing-xl;
  height: 64px;
  box-sizing: border-box;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  --wails-draggable: drag; /* 整个 header 可拖动 */

  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    min-width: 200px;

    .logo {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      cursor: pointer;
      transition: opacity 0.2s;
      --wails-draggable: no-drag; /* logo 可点击，不拖动 */

      &:hover {
        opacity: 0.8;
      }

      .logo-image {
        width: 28px;
        height: 28px;
        object-fit: contain;
      }

      .version-text {
        margin-left: 4px;
        font-size: 12px;
        color: $text-color-secondary;
        font-weight: 400;
      }

      .app-name {
        font-size: 20px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
    }

    /* 返回按钮不拖动 */
    .el-button {
      --wails-draggable: no-drag;
    }
  }

  .header-center {
    flex: 1;
    display: flex;
    justify-content: center;

    .page-title {
      font-size: 16px;
      font-weight: 600;
      color: $text-color-primary;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    min-width: 200px;
    justify-content: flex-end;

    /* 右侧按钮不拖动 */
    .el-button {
      --wails-draggable: no-drag;
    }

    /* 窗口控制按钮 - macOS 风格 */
    .window-controls {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-left: $spacing-md;
      --wails-draggable: no-drag;

      .window-control-btn {
        width: 20px;
        height: 20px;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        position: relative;
        padding: 0;

        .el-icon {
          font-size: 12px;
          opacity: 1;
          transition: opacity 0.2s;
          position: absolute;
          color: #fff;
        }

        &--close {
          background: #FF5F57;

          &:hover {
            background: #FF4037;
          }

          &:active {
            background: #E0362E;
          }
        }

        &--minimize {
          background: #FFBD2E;

          &:hover {
            background: #FFAA1E;
          }

          &:active {
            background: #E09A1E;
          }
        }

        &--maximize {
          background: #28CA42;

          &:hover {
            background: #20B038;
          }

          &:active {
            background: #1A9930;
          }
        }
      }
    }
  }
}

.app-content {
  flex: 1;
  /*
    修改为 hidden，防止外层出现滚动条。
    页面内容（如 Home, Wizard）应该自己管理滚动区域。
    */
  overflow: hidden;
  padding: 0;
  display: flex; /* 确保子元素能撑开高度 */
  flex-direction: column;
}

.notifications {
  position: fixed;
  top: $spacing-lg;
  right: $spacing-lg;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.notification-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-md $spacing-lg;
  background: #fff;
  border-radius: $border-radius-base;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  min-width: 300px;

  &--success {
    border-left: 4px solid $success-color;
  }

  &--error {
    border-left: 4px solid $danger-color;
  }

  &--warning {
    border-left: 4px solid $warning-color;
  }

  &--info {
    border-left: 4px solid $info-color;
  }

  .notification-icon {
    font-size: 20px;
  }
}

.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
