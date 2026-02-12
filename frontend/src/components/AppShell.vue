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
import { useConnectionStore } from '@/stores/connection'
import { useAppStore } from '@/stores/app'
import {
  DataAnalysis,
  ArrowLeft,
  Setting,
  CircleCheck,
  CircleClose,
  Warning,
  Minus,
  FullScreen,
  CopyDocument,
  Close
} from '@element-plus/icons-vue'
import * as Runtime from '../../wailsjs/runtime/runtime.js'

const router = useRouter()
const isMaximized = ref(false)
const route = useRoute()
const connectionStore = useConnectionStore()
const appStore = useAppStore()

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
// 窗口控制函数
function minimizeWindow() {
  Runtime.WindowMinimise()
}

function toggleMaximize() {
  Runtime.WindowToggleMaximise()
  isMaximized.value = !isMaximized.value
}

function closeWindow() {
  Runtime.Quit()
}


onMounted(async () => {
  // 加载连接列表
  try {
    await connectionStore.fetchConnections()
  } catch (error) {
    console.error('Failed to load connections:', error)
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
          opacity: 0;
          transition: opacity 0.2s;
          position: absolute;
          color: #fff;
        }

        &:hover .el-icon {
          opacity: 1;
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
