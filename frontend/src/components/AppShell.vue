<template>
  <el-container class="app-shell">
    <!-- 主内容区 -->
    <el-container class="app-main">
      <!-- 顶部栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <div class="version-badge">v{{ appVersion }}<template v-if="isDevVersion"> 开发版</template></div>
        </div>

        <div class="header-center">
          <!-- 页面标题 -->
          <div class="page-title">{{ currentRouteTitle }}</div>
        </div>

        <div class="header-right-spacer"></div>
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
import { useRoute } from 'vue-router'
import { useConnectionStore } from '@/stores/connection'
import { useAppStore } from '@/stores/app'
import { checkBackendHealth } from '@/api/client'
import {
  CircleCheck,
  CircleClose,
  Warning
} from '@element-plus/icons-vue'

const route = useRoute()
const connectionStore = useConnectionStore()
const appStore = useAppStore()

// 版本信息
const appVersion = ref('0.0.4')
const isDevVersion = ref(false)

const currentRouteTitle = computed(() => route.meta?.title || '首页')

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
    min-width: 200px;

    .version-badge {
      --wails-draggable: no-drag; /* logo 可点击，不拖动 */
      font-size: 12px;
      color: $text-color-secondary;
      font-weight: 500;
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

  .header-right-spacer {
    min-width: 200px;
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
