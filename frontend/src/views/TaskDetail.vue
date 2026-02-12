<template>
  <div class="task-detail-page">
    <!-- 任务头部 -->
    <div class="task-header">
      <div class="header-left">
        <div class="task-title">
          <h1>{{ task?.name }}</h1>
          <el-tag :type="getStatusType(task?.status)" size="small">
            {{ getStatusText(task?.status) }}
          </el-tag>
        </div>
      </div>
      <div class="header-right">
        <el-button v-if="task?.status === 'completed'" type="success" @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
        <el-dropdown @command="handleCommand">
          <el-button :icon="MoreFilled" circle />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="delete" v-if="task?.status !== 'running'">
                删除任务
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 任务进行中状态 -->
    <div v-if="task?.status === 'running' || task?.status === 'paused' || task?.status === 'pending'" class="running-state">
      <el-card>
        <div class="progress-content">
          <div class="progress-info">
            <el-icon :size="48" class="progress-icon">
              <component :is="(task.status === 'running' || task.status === 'pending') ? 'Loading' : 'VideoPause'" />
            </el-icon>
            <div class="progress-text">
              <h3>{{ (task.status === 'running' || task.status === 'pending') ? '正在采集数据...' : '任务已暂停' }}</h3>
              <p>{{ task.current_step || '初始化中...' }}</p>
            </div>
          </div>
          <div class="progress-bar">
            <el-progress
              :percentage="task.progress"
              :status="task.status === 'paused' ? 'exception' : undefined"
              :stroke-width="12"
            />
            <div class="progress-stats">
              <span>{{ task.collectedVMs || 0 }} / {{ task.totalVMs || 0 }} 台虚拟机</span>
              <span>{{ task.progress }}%</span>
            </div>
          </div>
          <div class="progress-actions">
            <el-button-group>
              <el-button @click="handleCancel">
                <el-icon><CloseBold /></el-icon>
                取消任务
              </el-button>
            </el-button-group>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 任务已完成状态 -->
    <div v-else-if="task?.status === 'completed'">
      <!-- Tab 导航 -->
      <el-tabs v-model="activeTab" class="task-tabs">
        <el-tab-pane label="概览" name="overview">
          <div class="overview-content">
            <!-- 任务统计 -->
            <el-row :gutter="20" class="stats-row">
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32"><Monitor /></el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ task.totalVMs }}</div>
                    <div class="stat-label">虚拟机数量</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32"><Clock /></el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ formatDuration(task) }}</div>
                    <div class="stat-label">采集耗时</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32"><Check /></el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ completedAnalyses }}</div>
                    <div class="stat-label">已完成分析</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32"><TrendCharts /></el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ task.platform === 'vcenter' ? 'vSphere' : 'UIS' }}</div>
                    <div class="stat-label">平台类型</div>
                  </div>
                </div>
              </el-col>
            </el-row>

            <!-- 分析功能入口 -->
            <div class="analysis-grid">
              <h3 class="section-title">分析功能</h3>
              <el-row :gutter="16">
                <el-col :span="6" v-for="analysis in analyses" :key="analysis.key">
                  <div
                    class="analysis-card"
                    :class="{ completed: task.analysisResults?.[analysis.key] }"
                    @click="runAnalysis(analysis.key)"
                  >
                    <div class="analysis-icon" :class="'analysis-icon--' + analysis.color">
                      <el-icon :size="28">
                        <component :is="analysis.icon" />
                      </el-icon>
                    </div>
                    <h4 class="analysis-title">{{ analysis.title }}</h4>
                    <p class="analysis-desc">{{ analysis.description }}</p>
                    <div class="analysis-status">
                      <el-icon v-if="task.analysisResults?.[analysis.key]" class="status-icon">
                        <CircleCheck />
                      </el-icon>
                      <el-icon v-else class="status-icon pending">
                        <CircleClose />
                      </el-icon>
                      <span>{{ task.analysisResults?.[analysis.key] ? '已完成' : '未运行' }}</span>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="虚拟机列表" name="vms">
          <div class="vms-content">
            <div class="table-toolbar">
              <el-input
                v-model="vmSearch"
                placeholder="搜索虚拟机"
                prefix-icon="Search"
                clearable
                style="width: 300px"
              />
            </div>
            <el-table :data="filteredVMList" stripe :loading="vmListLoading" :default-expand-all="false">
              <el-table-column prop="name" label="虚拟机名称" min-width="180" />
              <el-table-column prop="cpu_count" label="CPU" width="100">
                <template #default="{ row }">
                  {{ row.cpu_count > 0 ? row.cpu_count + ' 核' : '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="memory_gb" label="内存" width="120">
                <template #default="{ row }">
                  {{ row.memory_gb > 0 ? row.memory_gb + ' GB' : '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="power_state" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getPowerStateType(row.power_state)" size="small">
                    {{ getPowerStateText(row.power_state) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="datacenter" label="数据中心" width="150" />
              <el-table-column prop="host_name" label="主机" width="150" />
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="僵尸VM" name="zombie">
          <div class="analysis-content" v-if="task.analysisResults?.zombie">
            <ZombieResult :task-id="task.id" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" @click="runAnalysis('zombie')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Right Size" name="rightsize">
          <div class="analysis-content" v-if="task.analysisResults?.rightsize">
            <RightSizeResult :task-id="task.id" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" @click="runAnalysis('rightsize')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="潮汐检测" name="tidal">
          <div class="analysis-content" v-if="task.analysisResults?.tidal">
            <TidalResult :task-id="task.id" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" @click="runAnalysis('tidal')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="健康评分" name="health">
          <div class="analysis-content" v-if="task.analysisResults?.health">
            <HealthResult :task-id="task.id" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" @click="runAnalysis('health')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 任务失败状态 -->
    <div v-else-if="task?.status === 'failed'" class="failed-state">
      <el-result icon="error" title="任务执行失败" :sub-title="task.error" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore, type Task } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as ConnectionAPI from '@/api/connection'
import type { VMListItem } from '@/api/connection'
import {
  Download,
  MoreFilled,
  Monitor,
  Clock,
  Check,
  TrendCharts,
  VideoPause,
  VideoPlay,
  CloseBold,
  Search,
  Warning,
  Coin,
  DataAnalysis,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

const activeTab = ref('overview')
const vmSearch = ref('')
const vmList = ref<VMListItem[]>([])
const vmListLoading = ref(false)

// 获取任务
const task = computed(() => taskStore.getTask(route.params.id as string))

// 分析功能配置
const analyses = [
  {
    key: 'zombie',
    title: '僵尸 VM 检测',
    description: '识别长期低负载的虚拟机',
    icon: 'Monitor',
    color: 'orange'
  },
  {
    key: 'rightsize',
    title: 'Right Sizing',
    description: '资源配置优化建议',
    icon: 'TrendCharts',
    color: 'blue'
  },
  {
    key: 'tidal',
    title: '潮汐模式',
    description: '发现周期性规律',
    icon: 'Coin',
    color: 'green'
  },
  {
    key: 'health',
    title: '健康评分',
    description: '平台健康度评估',
    icon: 'DataAnalysis',
    color: 'purple'
  }
]

// 完成的分析数量
const completedAnalyses = computed(() => {
  const results = task.value?.analysisResults
  if (!results) return 0
  return Object.values(results).filter(v => v).length
})

// 过滤后的虚拟机列表
const filteredVMList = computed(() => {
  if (!vmSearch.value) return vmList.value
  const keyword = vmSearch.value.toLowerCase()
  return vmList.value.filter(vm => vm.name.toLowerCase().includes(keyword))
})

onMounted(async () => {
  if (!task.value) {
    ElMessage.error('任务不存在')
    router.push('/')
    return
  }

  // 加载虚拟机列表数据
  if (task.value.connectionId) {
    await loadVMList(task.value.connectionId)
  }

  // 如果任务有后端任务ID，轮询状态
  if (task.value.backendTaskId) {
    pollTaskStatus(task.value.backendTaskId)
  }
})

// 加载虚拟机列表
async function loadVMList(connectionId: number) {
  vmListLoading.value = true
  try {
    vmList.value = await ConnectionAPI.listVMs(connectionId)
  } catch (error: any) {
    console.error('Failed to load VM list:', error)
    ElMessage.error('加载虚拟机列表失败: ' + (error.message || '未知错误'))
  } finally {
    vmListLoading.value = false
  }
}

// 轮询后端任务状态
function pollTaskStatus(backendTaskId: number) {
  const pollInterval = setInterval(async () => {
    try {
      const taskInfo = await ConnectionAPI.getTask(backendTaskId)

      if (task.value) {
        task.value.status = taskInfo.status as any
        task.value.progress = taskInfo.progress
        task.value.error = taskInfo.error

        if (taskInfo.status === 'completed') {
          clearInterval(pollInterval)
          // 加载最新的 VM 列表
          if (task.value.connectionId) {
            await loadVMList(task.value.connectionId)
          }
        } else if (taskInfo.status === 'failed') {
          clearInterval(pollInterval)
          ElMessage.error('任务执行失败: ' + (taskInfo.error || '未知错误'))
        }
      }
    } catch (e) {
      console.error('Failed to poll task status:', e)
    }
  }, 2000)

  // 5分钟后停止轮询
  setTimeout(() => {
    clearInterval(pollInterval)
  }, 5 * 60 * 1000)
}

function simulateProgress() {
  if (!task.value || task.value.status !== 'running') return

  const interval = setInterval(() => {
    if (!task.value || task.value.status !== 'running') {
      clearInterval(interval)
      return
    }

    const currentProgress = task.value.progress || 0
    if (currentProgress < 100) {
      // 模拟进度增长
      const increment = Math.floor(Math.random() * 5) + 1
      const newProgress = Math.min(currentProgress + increment, 100)

      const collected = Math.floor((newProgress / 100) * (task.value.totalVMs || 0))

      taskStore.updateTaskStatus(taskId, 'running', newProgress)

      // 更新已采集数量
      if (task.value) {
        task.value.collectedVMs = collected
      }
      taskStore.saveTasksToStorage()
    } else {
      taskStore.updateTaskStatus(taskId, 'completed', 100)
      taskStore.saveTasksToStorage()
      ElMessage.success('数据采集完成')
      clearInterval(interval)
    }
  }, 1000)
}

function goBack() {
  router.push('/')
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('确定要取消此任务吗？', '确认取消', {
      type: 'warning'
    })
    taskStore.cancelTask(taskId)
    taskStore.saveTasksToStorage()
    ElMessage.success('任务已取消')
    router.push('/')
  } catch {
    // 用户取消
  }
}

async function handleCommand(cmd: string) {
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除此任务吗？', '确认删除', {
        type: 'warning'
      })
      taskStore.deleteTask(taskId)
      taskStore.saveTasksToStorage()
      ElMessage.success('任务已删除')
      router.push('/')
    } catch {
      // 用户取消
    }
  }
}

function runAnalysis(type: string) {
  ElMessage.info('正在运行 ' + type + ' 分析...')
  // 模拟分析完成
  setTimeout(() => {
    taskStore.updateAnalysisResult(taskId, type as any, true)
    taskStore.saveTasksToStorage()
    ElMessage.success(type + ' 分析完成！')
  }, 2000)
}

async function exportReport() {
  if (!task.value) return

  try {
    ElMessage.info('正在生成 Excel 报告...')
    const filepath = await exportTaskReport(taskId)
    ElMessage.success('报告已导出: ' + filepath)
  } catch (error: any) {
    ElMessage.error('导出失败: ' + (error.message || '未知错误'))
  }
}

function getStatusType(status: string | undefined) {
  const typeMap: Record<string, any> = {
    pending: 'info',
    running: 'primary',
    paused: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return typeMap[status || ''] || 'info'
}

function getStatusText(status: string | undefined) {
  const textMap: Record<string, string> = {
    pending: '等待中',
    running: '进行中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return textMap[status || ''] || status
}

function formatMemory(mb: number): string {
  if (mb >= 1024) {
    return (mb / 1024).toFixed(1) + ' GB'
  }
  return mb + ' MB'
}

function formatDuration(task: Task | undefined): string {
  if (!task?.started_at || !task.ended_at) return '-'
  const start = new Date(task.started_at).getTime()
  const end = new Date(task.ended_at).getTime()
  const duration = end - start
  const minutes = Math.floor(duration / 60000)
  if (minutes < 60) return minutes + '分钟'
  const hours = Math.floor(minutes / 60)
  return hours + '小时' + (minutes % 60) + '分钟'
}

function getPowerStateType(state: string) {
  const typeMap: Record<string, string> = {
    poweredOn: 'success',
    poweredOff: 'info',
    suspended: 'warning'
  }
  return typeMap[state] || 'info'
}

function getPowerStateText(state: string) {
  const textMap: Record<string, string> = {
    poweredOn: '开机',
    poweredOff: '关机',
    suspended: '挂起'
  }
  return textMap[state] || state
}

// 占位组件
const ZombieResult = { template: '<div class="placeholder"><p>僵尸VM 分析结果将在此显示</p></div>' }
const RightSizeResult = { template: '<div class="placeholder"><p>Right Size 分析结果将在此显示</p></div>' }
const TidalResult = { template: '<div class="placeholder"><p>潮汐模式分析结果将在此显示</p></div>' }
const HealthResult = { template: '<div class="placeholder"><p>健康评分结果将在此显示</p></div>' }
</script>

<style scoped lang="scss">
.task-detail-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  padding: $spacing-xl;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;

    .task-title {
      h1 {
        font-size: 20px;
        font-weight: 600;
        margin: 0 0 $spacing-xs 0;
        display: flex;
        align-items: center;
        gap: $spacing-sm;
      }
    }
  }

  .header-right {
    display: flex;
    gap: $spacing-sm;
  }
}

.running-state {
  .progress-content {
    display: flex;
    flex-direction: column;
    gap: $spacing-xl;
    align-items: center;

    .progress-info {
      display: flex;
      align-items: center;
      gap: $spacing-xl;
      text-align: left;

      .progress-icon {
        color: $primary-color;
        animation: spin 1s linear infinite;
      }

      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      .progress-text {
        h3 {
          margin: 0 0 $spacing-xs 0;
          font-size: 18px;
        }

        p {
          margin: 0;
          color: $text-color-secondary;
        }
      }
    }

    .progress-bar {
      width: 100%;
      max-width: 500px;

      .progress-stats {
        display: flex;
        justify-content: space-between;
        margin-top: $spacing-sm;
        font-size: 14px;
        color: $text-color-secondary;
      }
    }
  }
}

.overview-content {
  .stats-row {
    margin-bottom: $spacing-xl;

    .stat-card {
      display: flex;
      align-items: center;
      gap: $spacing-md;
      padding: $spacing-lg;
      background: white;
      border-radius: 12px;
      border: 1px solid $border-color-light;

      .stat-icon {
        color: $primary-color;
      }

      .stat-content {
        .stat-value {
          font-size: 24px;
          font-weight: 600;
          color: $text-color-primary;
        }

        .stat-label {
          font-size: 13px;
          color: $text-color-secondary;
        }
      }
    }
  }

  .analysis-grid {
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: $text-color-primary;
      margin: 0 0 $spacing-lg 0;
    }

    .analysis-card {
      padding: $spacing-lg;
      background: white;
      border-radius: 12px;
      border: 1px solid $border-color-light;
      cursor: pointer;
      transition: all 0.3s;
      text-align: center;

      &:hover {
        border-color: $primary-color;
        box-shadow: 0 4px 20px rgba(64, 158, 255, 0.1);
      }

      &.completed {
        border-color: $success-color;
        background: rgba(103, 194, 58, 0.05);

        .analysis-status {
          color: $success-color;
        }
      }

      .analysis-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border-radius: 12px;
        margin-bottom: $spacing-md;

        &--orange {
          background: rgba(230, 162, 60, 0.1);
          color: $warning-color;
        }

        &--blue {
          background: rgba(64, 158, 255, 0.1);
          color: $primary-color;
        }

        &--green {
          background: rgba(103, 194, 58, 0.1);
          color: $success-color;
        }

        &--purple {
          background: rgba(245, 108, 108, 0.1);
          color: $danger-color;
        }
      }

      .analysis-title {
        font-size: 16px;
        font-weight: 600;
        color: $text-color-primary;
        margin: 0 0 $spacing-xs 0;
      }

      .analysis-desc {
        font-size: 13px;
        color: $text-color-secondary;
        margin: 0 0 $spacing-md 0;
      }

      .analysis-status {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: $spacing-xs;
        font-size: 13px;
        color: $text-color-secondary;

        .status-icon {
          font-size: 16px;

          &.pending {
            color: $info-color;
          }
        }
      }
    }
  }
}

.vms-content {
  .table-toolbar {
    margin-bottom: $spacing-md;
  }
}

.analysis-content {
  .placeholder {
    padding: $spacing-xl;
    text-align: center;
    color: $text-color-secondary;
  }
}

.analysis-placeholder {
  padding: $spacing-xl 0;
}

.failed-state {
  display: flex;
  justify-content: center;
  padding: $spacing-xl 0;
}
</style>
