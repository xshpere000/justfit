<template>
  <div
    class="task-card"
    :class="[`status--${task.status}`, platformClass]"
    @click="$emit('click', task)"
  >
    <!-- 顶部：平台标识和操作菜单 -->
    <div class="card-header">
      <div class="platform-badge" :class="platformClass">
        <el-icon><component :is="platformIcon" /></el-icon>
        <span>{{ platformLabel }}</span>
      </div>
      <div class="task-actions" @click.stop>
        <el-dropdown trigger="click" @command="handleCommand">
          <el-icon class="more-icon"><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <!-- 取消任务 - 仅运行中/等待中 -->
              <el-dropdown-item
                v-if="['running', 'pending'].includes(task.status)"
                command="cancel"
                :icon="CircleClose"
              >
                取消任务
              </el-dropdown-item>
              <!-- 重试任务 - 仅失败状态 -->
              <el-dropdown-item
                v-if="task.status === 'failed'"
                command="retry"
                :icon="Refresh"
              >
                重试任务
              </el-dropdown-item>
              <!-- 删除任务 - 分隔线 -->
              <el-dropdown-item
                command="delete"
                :icon="Delete"
                divided
              >
                删除任务
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 中部：任务信息 -->
    <div class="card-body">
      <h3 class="task-name" :title="task.name">{{ task.name }}</h3>
      <div class="task-meta">
        <div class="meta-item">
          <el-icon><Connection /></el-icon>
          <span>{{ displayHost }}</span>
        </div>
        <div class="meta-item">
          <el-icon><Clock /></el-icon>
          <span>{{ formattedTime }}</span>
        </div>
      </div>
      <!-- 运行中显示当前步骤 -->
      <div v-if="task.status === 'running' && task.currentStep" class="current-step">
        <el-icon class="is-loading step-icon"><Loading /></el-icon>
        <span class="step-text">{{ task.currentStep }}</span>
      </div>
    </div>

    <!-- 底部：状态信息 -->
    <div class="card-footer">
      <!-- 运行中/等待中 -->
      <template v-if="['running', 'pending'].includes(task.status)">
        <div class="progress-section">
          <div class="progress-header">
            <span class="status-label">
              <el-icon v-if="task.status === 'running'" class="is-loading">
                <Loading />
              </el-icon>
              {{ statusLabel }}
            </span>
            <span class="progress-value">{{ task.progress }}%</span>
          </div>
          <el-progress
            :percentage="task.progress"
            :show-text="false"
            :stroke-width="6"
            :color="progressColor"
          />
        </div>
        <!-- 采集进度 -->
        <div v-if="showCollectionProgress" class="collection-progress">
          <span class="progress-text">正在采集虚拟机数据...</span>
        </div>
      </template>

      <!-- 已完成 -->
      <template v-else-if="task.status === 'completed'">
        <div class="completed-section">
          <div class="result-stats">
            <div class="stat-item">
              <span class="stat-label">虚拟机</span>
              <span class="stat-value">{{ task.selectedVMCount || 0 }}</span>
            </div>
            <el-divider direction="vertical" />
            <div class="stat-item">
              <span class="stat-label">已完成分析</span>
              <span class="stat-value">{{ completedAnalysesCount }}/{{ totalAnalysesCount }}</span>
            </div>
          </div>
          <div class="completed-badge">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>已完成</span>
          </div>
        </div>
      </template>

      <!-- 失败 -->
      <template v-else-if="task.status === 'failed'">
        <div class="failed-section">
          <el-tag type="danger" effect="plain" size="small">
            <el-icon><CircleCloseFilled /></el-icon>
            执行失败
          </el-tag>
          <span v-if="task.error" class="error-message" :title="task.error">
            {{ truncatedError }}
          </span>
        </div>
      </template>

      <!-- 已取消 -->
      <template v-else-if="task.status === 'cancelled'">
        <div class="cancelled-section">
          <el-tag type="info" effect="plain" size="small">
            <el-icon><CircleClose /></el-icon>
            已取消
          </el-tag>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  MoreFilled,
  Connection,
  Clock,
  Loading,
  CircleCheckFilled,
  CircleCloseFilled,
  CircleClose,
  Refresh,
  Delete,
  Monitor,
  Platform
} from '@element-plus/icons-vue'
import type { Task, TaskStatus } from '@/api/task'

interface Props {
  task: Task
}

interface Emits {
  (e: 'click', task: Task): void
  (e: 'command', command: string, task: Task): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 平台相关
const platformClass = computed(() => {
  const platform = props.task.platform?.toLowerCase() || ''
  if (platform.includes('vcenter') || platform === 'vmware') {
    return 'platform-vcenter'
  }
  return 'platform-uis'
})

const platformLabel = computed(() => {
  const platform = props.task.platform?.toLowerCase() || ''
  if (platform.includes('vcenter') || platform === 'vmware') {
    return 'vCenter'
  }
  return 'H3C UIS'
})

const platformIcon = computed(() => {
  return platformClass.value === 'platform-vcenter' ? Monitor : Platform
})

// 显示用的主机地址（优先使用 connectionHost，回退到 connectionName）
const displayHost = computed(() => {
  return props.task.connectionHost || props.task.connectionName || '未知连接'
})

// 时间格式化
const formattedTime = computed(() => {
  const timeKey = props.task.completedAt || props.task.startedAt || props.task.createdAt
  if (!timeKey) return '-'
  const date = new Date(timeKey)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days > 7) {
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}-${day}`
  } else if (days > 0) {
    return `${days}天前`
  } else if (diff > 3600000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}小时前`
  } else if (diff > 60000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes}分钟前`
  }
  return '刚刚'
})

// 状态标签
const statusLabel = computed(() => {
  const labels: Record<TaskStatus, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '执行失败',
    cancelled: '已取消'
  }
  return labels[props.task.status] || props.task.status
})

// 进度条颜色
const progressColor = computed(() => {
  if (props.task.status === 'pending') {
    return '#e6a23c'
  }
  return '#409eff'
})

// 是否显示采集进度
const showCollectionProgress = computed(() => {
  return (
    props.task.status === 'running' &&
    props.task.collectedVMCount !== undefined &&
    props.task.selectedVMCount !== undefined &&
    props.task.selectedVMCount > 0
  )
})

// 完成的分析数量
const completedAnalysesCount = computed(() => {
  if (!props.task.analysisResults) return 0
  return Object.values(props.task.analysisResults).filter(v => v).length
})

// 总分析数量
const totalAnalysesCount = computed(() => {
  if (!props.task.analysisResults) return 3
  return Object.keys(props.task.analysisResults).length
})

// 错误信息截断
const truncatedError = computed(() => {
  if (!props.task.error) return ''
  const error = props.task.error
  return error.length > 30 ? error.substring(0, 30) + '...' : error
})

// 处理命令
function handleCommand(command: string) {
  emit('command', command, props.task)
}
</script>

<style scoped lang="scss">
.task-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  padding: 16px;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 180px;
  overflow: hidden;

  // 状态边框颜色
  &.status--running {
    border-color: #409eff;
    box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.1);
  }
  &.status--pending {
    border-color: #e6a23c;
    box-shadow: 0 0 0 1px rgba(230, 162, 60, 0.1);
  }
  &.status--completed {
    border-color: #67c23a;
    box-shadow: 0 0 0 1px rgba(103, 194, 58, 0.1);
  }
  &.status--failed {
    border-color: #f56c6c;
    box-shadow: 0 0 0 1px rgba(245, 108, 108, 0.1);
  }
  &.status--cancelled {
    border-color: #909399;
  }

  // 平台标识背景色
  &.platform-vcenter .platform-badge {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    color: #2e7d32;
  }
  &.platform-uis .platform-badge {
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    color: #1565c0;
  }

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);

    .more-icon {
      opacity: 1;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .platform-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 600;
      letter-spacing: 0.3px;
    }

    .more-icon {
      color: #909399;
      font-size: 16px;
      padding: 4px;
      border-radius: 6px;
      opacity: 0.6;
      transition: all 0.2s;

      &:hover {
        color: #409eff;
        background: #ecf5ff;
        opacity: 1;
      }
    }
  }

  .card-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;

    .task-name {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      line-height: 1.4;
    }

    .task-meta {
      display: flex;
      flex-direction: column;
      gap: 6px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #606266;

        .el-icon {
          font-size: 13px;
          color: #909399;
        }
      }
    }

    .current-step {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 4px;
      padding: 6px 10px;
      background: #f0f9ff;
      border-radius: 6px;
      font-size: 12px;
      color: #409eff;

      .step-icon {
        font-size: 13px;
      }

      .step-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .card-footer {
    padding-top: 12px;
    border-top: 1px solid #f2f6fc;

    .progress-section {
      .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .status-label {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          color: #606266;
          font-weight: 500;

          .el-icon {
            font-size: 13px;
            color: #409eff;
          }
        }

        .progress-value {
          font-size: 14px;
          font-weight: 700;
          color: #409eff;
        }
      }

      :deep(.el-progress-bar__outer) {
        border-radius: 999px;
      }

      :deep(.el-progress-bar__inner) {
        border-radius: 999px;
      }
    }

    .collection-progress {
      margin-top: 8px;
      text-align: center;

      .progress-text {
        font-size: 11px;
        color: #909399;
      }
    }

    .completed-section {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .result-stats {
        display: flex;
        align-items: center;
        gap: 12px;

        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: flex-start;

          .stat-label {
            font-size: 10px;
            color: #909399;
            line-height: 1.2;
            margin-bottom: 2px;
          }

          .stat-value {
            font-size: 14px;
            font-weight: 700;
            color: #303133;
            line-height: 1.2;
          }
        }
      }

      .completed-badge {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        font-weight: 600;
        color: #67c23a;

        .el-icon {
          font-size: 16px;
        }
      }
    }

    .failed-section {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .error-message {
        font-size: 11px;
        color: #f56c6c;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .cancelled-section {
      text-align: center;
    }
  }
}
</style>
