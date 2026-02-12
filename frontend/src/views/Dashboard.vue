<template>
  <div class="dashboard-page">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card health-card">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="32" color="#67C23A">
                <CircleCheck />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.health_score }}</div>
              <div class="stat-label">平台健康评分</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card zombie-card">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="32" color="#F56C6C">
                <Warning />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.zombie_count }}</div>
              <div class="stat-label">僵尸 VM 数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card savings-card">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="32" color="#409EFF">
                <Coin />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_savings }}</div>
              <div class="stat-label">预计节省</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card vms-card">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon :size="32" color="#E6A23C">
                <Monitor />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_vms }}</div>
              <div class="stat-label">虚拟机总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 内容区域 -->
    <el-row :gutter="20" class="content-row">
      <!-- 左侧：连接状态 -->
      <el-col :span="12">
        <el-card class="content-card">
          <template #header>
            <div class="card-header">
              <span>连接状态</span>
              <el-button link type="primary" @click="refreshConnections">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          <div class="connection-list">
            <div
              v-for="conn in connectionStore.connections"
              :key="conn.id"
              class="connection-item"
            >
              <div class="conn-info">
                <el-icon
                  :size="20"
                  :color="getConnectionStatusColor(conn.status)"
                >
                  <Connection />
                </el-icon>
                <div class="conn-details">
                  <div class="conn-name">{{ conn.name }}</div>
                  <div class="conn-platform">
                    {{ conn.platform === 'vcenter' ? 'VMware vCenter' : 'H3C UIS' }}
                  </div>
                </div>
              </div>
              <el-tag :type="getConnectionStatusType(conn.status)" size="small">
                {{ getConnectionStatusText(conn.status) }}
              </el-tag>
            </div>
            <el-empty
              v-if="connectionStore.connections.length === 0"
              description="暂无连接"
              :image-size="60"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：最近活动 -->
      <el-col :span="12">
        <el-card class="content-card">
          <template #header>
            <div class="card-header">
              <span>最近任务</span>
              <el-button link type="primary" @click="$router.push('/tasks')">
                查看全部
              </el-button>
            </div>
          </template>
          <div class="task-list">
            <div
              v-for="task in recentTasks"
              :key="task.id"
              class="task-item"
            >
              <div class="task-info">
                <el-icon :size="20" :color="getTaskStatusColor(task.status)">
                  <component :is="getTaskIcon(task.status)" />
                </el-icon>
                <div class="task-details">
                  <div class="task-name">{{ task.name }}</div>
                  <div class="task-time">{{ formatDate(task.created_at) }}</div>
                </div>
              </div>
              <el-tag :type="getTaskStatusType(task.status)" size="small">
                {{ getTaskStatusText(task.status) }}
              </el-tag>
            </div>
            <el-empty
              v-if="recentTasks.length === 0"
              description="暂无最近任务"
              :image-size="60"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速操作 -->
    <el-row :gutter="20" class="quick-actions-row">
      <el-col :span="24">
        <el-card class="quick-actions-card">
          <template #header>
            <span>快速操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" :icon="'Plus'" @click="$router.push('/connections')">
              添加连接
            </el-button>
            <el-button type="success" :icon="'Search'" @click="$router.push('/analysis/zombie')">
              僵尸 VM 检测
            </el-button>
            <el-button type="warning" :icon="'Crop'" @click="$router.push('/analysis/rightsize')">
              Right Size 评估
            </el-button>
            <el-button type="info" :icon="'DataAnalysis'" @click="$router.push('/analysis/health')">
              平台健康分析
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  CircleCheck,
  Warning,
  Coin,
  Monitor,
  Connection,
  Refresh,
  SuccessFilled,
  Loading,
  CircleClose
} from '@element-plus/icons-vue'
import { useConnectionStore } from '@/stores/connection'
import { useTaskStore } from '@/stores/task'
import * as DashboardAPI from '@/api/connection'

const router = useRouter()
const connectionStore = useConnectionStore()
const taskStore = useTaskStore()

const stats = ref({
  health_score: 0,
  zombie_count: 0,
  total_savings: '¥0',
  total_vms: 0
})

const recentTasks = computed(() => {
  return taskStore.tasks.slice(0, 5)
})

onMounted(async () => {
  await Promise.all([
    connectionStore.fetchConnections(),
    taskStore.loadTasksFromStorage(),
    loadDashboardStats()
  ])
})

async function loadDashboardStats() {
  try {
    const data = await DashboardAPI.getStats()
    stats.value = data
  } catch (e) {
    console.error('Failed to load dashboard stats:', e)
  }
}

function refreshConnections() {
  connectionStore.fetchConnections()
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return days + '天前'
  if (hours > 0) return hours + '小时前'
  if (minutes > 0) return minutes + '分钟前'
  return '刚刚'
}

function getConnectionStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    connected: '#67C23A',
    disconnected: '#909399',
    error: '#F56C6C',
    connecting: '#E6A23C'
  }
  return colorMap[status] || '#909399'
}

function getConnectionStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    connected: 'success',
    disconnected: 'info',
    error: 'danger',
    connecting: 'warning'
  }
  return typeMap[status] || 'info'
}

function getConnectionStatusText(status: string): string {
  const textMap: Record<string, string> = {
    connected: '已连接',
    disconnected: '未连接',
    error: '连接失败',
    connecting: '连接中'
  }
  return textMap[status] || status
}

function getTaskStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    completed: '#67C23A',
    running: '#409EFF',
    failed: '#F56C6C',
    pending: '#E6A23C'
  }
  return colorMap[status] || '#909399'
}

function getTaskStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    completed: 'success',
    running: 'primary',
    failed: 'danger',
    pending: 'warning',
    cancelled: 'info'
  }
  return typeMap[status] || 'info'
}

function getTaskStatusText(status: string): string {
  const textMap: Record<string, string> = {
    completed: '已完成',
    running: '进行中',
    failed: '失败',
    pending: '等待中',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

function getTaskIcon(status: string) {
  const iconMap: Record<string, any> = {
    completed: SuccessFilled,
    running: Loading,
    failed: CircleClose
  }
  return iconMap[status] || SuccessFilled
}
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);

  .stats-row {
    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);

        .stat-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 56px;
          height: 56px;
          border-radius: var(--border-radius-base);
          background: var(--background-color-light);
        }

        .stat-info {
          flex: 1;

          .stat-value {
            font-size: 28px;
            font-weight: 600;
            line-height: 1.2;
          }

          .stat-label {
            font-size: var(--font-size-small);
            color: var(--text-color-secondary);
            margin-top: var(--spacing-xs);
          }
        }
      }
    }
  }

  .content-row {
    .content-card {
      height: 100%;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .connection-list,
      .task-list {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
        max-height: 300px;
        overflow-y: auto;

        .connection-item,
        .task-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--spacing-md);
          background: var(--background-color-base);
          border-radius: var(--border-radius-base);
          transition: background var(--transition-base);

          &:hover {
            background: var(--background-color-light);
          }

          .conn-info,
          .task-info {
            display: flex;
            align-items: center;
            gap: var(--spacing-md);

            .conn-details,
            .task-details {
              .conn-name,
              .task-name {
                font-weight: 500;
                margin-bottom: 2px;
              }

              .conn-platform,
              .task-time {
                font-size: var(--font-size-small);
                color: var(--text-color-secondary);
              }
            }
          }
        }
      }
    }
  }

  .quick-actions-card {
    .quick-actions {
      display: flex;
      gap: var(--spacing-md);
      flex-wrap: wrap;
    }
  }
}
</style>
