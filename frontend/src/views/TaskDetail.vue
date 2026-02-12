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
            <el-table :data="analysisData.zombie" stripe v-loading="analysisLoading.zombie">
              <el-table-column prop="vm_name" label="虚拟机" min-width="180" />
              <el-table-column prop="datacenter" label="数据中心" min-width="140" />
              <el-table-column prop="cpu_usage" label="CPU使用率" width="120">
                <template #default="{ row }">{{ row.cpu_usage }}%</template>
              </el-table-column>
              <el-table-column prop="memory_usage" label="内存使用率" width="120">
                <template #default="{ row }">{{ row.memory_usage }}%</template>
              </el-table-column>
              <el-table-column prop="confidence" label="置信度" width="100">
                <template #default="{ row }">{{ row.confidence }}%</template>
              </el-table-column>
              <el-table-column prop="recommendation" label="建议" min-width="220" show-overflow-tooltip />
            </el-table>
            <el-empty v-if="!analysisLoading.zombie && analysisData.zombie.length === 0" description="暂无分析结果" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" :loading="analysisLoading.zombie" @click="runAnalysis('zombie')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Right Size" name="rightsize">
          <div class="analysis-content" v-if="task.analysisResults?.rightsize">
            <el-table :data="analysisData.rightsize" stripe v-loading="analysisLoading.rightsize">
              <el-table-column prop="vm_name" label="虚拟机" min-width="180" />
              <el-table-column prop="datacenter" label="数据中心" min-width="140" />
              <el-table-column prop="current_cpu" label="当前CPU" width="110" />
              <el-table-column prop="recommended_cpu" label="建议CPU" width="110" />
              <el-table-column prop="current_memory_mb" label="当前内存" width="130">
                <template #default="{ row }">{{ formatMemory(row.current_memory_mb) }}</template>
              </el-table-column>
              <el-table-column prop="recommended_memory_mb" label="建议内存" width="130">
                <template #default="{ row }">{{ formatMemory(row.recommended_memory_mb) }}</template>
              </el-table-column>
              <el-table-column prop="estimated_saving" label="预计节省" min-width="120" />
            </el-table>
            <el-empty v-if="!analysisLoading.rightsize && analysisData.rightsize.length === 0" description="暂无分析结果" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" :loading="analysisLoading.rightsize" @click="runAnalysis('rightsize')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="潮汐检测" name="tidal">
          <div class="analysis-content" v-if="task.analysisResults?.tidal">
            <el-table :data="analysisData.tidal" stripe v-loading="analysisLoading.tidal">
              <el-table-column prop="vm_name" label="虚拟机" min-width="180" />
              <el-table-column prop="pattern" label="模式" width="120" />
              <el-table-column prop="stability_score" label="稳定性" width="100" />
              <el-table-column label="高峰时段" min-width="160">
                <template #default="{ row }">{{ (row.peak_hours || []).join(', ') || '-' }}</template>
              </el-table-column>
              <el-table-column label="高峰日期" min-width="160">
                <template #default="{ row }">{{ (row.peak_days || []).join(', ') || '-' }}</template>
              </el-table-column>
              <el-table-column prop="recommendation" label="建议" min-width="220" show-overflow-tooltip />
            </el-table>
            <el-empty v-if="!analysisLoading.tidal && analysisData.tidal.length === 0" description="暂无分析结果" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" :loading="analysisLoading.tidal" @click="runAnalysis('tidal')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="健康评分" name="health">
          <div class="analysis-content" v-if="task.analysisResults?.health">
            <el-card v-loading="analysisLoading.health">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="综合评分">{{ analysisData.health?.overall_score ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="健康等级">{{ analysisData.health?.health_level ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="资源均衡">{{ analysisData.health?.resource_balance ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="超配风险">{{ analysisData.health?.overcommit_risk ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="热点集中">{{ analysisData.health?.hotspot_concentration ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="虚机数量">{{ analysisData.health?.total_vms ?? '-' }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
            <el-empty v-if="!analysisLoading.health && !analysisData.health" description="暂无分析结果" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" :loading="analysisLoading.health" @click="runAnalysis('health')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="执行日志" name="logs">
          <div class="analysis-content">
            <div style="margin-bottom: 12px; display: flex; justify-content: flex-end;">
              <el-button size="small" :disabled="!task?.backendTaskId" @click="loadTaskLogs">
                刷新日志
              </el-button>
            </div>
            <el-empty v-if="!task?.backendTaskId" description="该任务没有后端任务ID，无法查询执行日志" />
            <el-table v-else :data="taskLogs" stripe v-loading="logsLoading">
              <el-table-column prop="timestamp" label="时间" width="180" />
              <el-table-column prop="level" label="级别" width="100" />
              <el-table-column prop="message" label="内容" min-width="300" show-overflow-tooltip />
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 任务失败状态 -->
    <div v-else-if="task?.status === 'failed'" class="failed-state">
      <el-result icon="error" title="任务执行失败" :sub-title="task.error">
        <template #extra>
          <el-button type="primary" :disabled="!task?.backendTaskId" @click="handleRetry">重试任务</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore, type Task } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as ConnectionAPI from '@/api/connection'
import { exportTaskReport } from '@/api/report'
import {
  Download,
  MoreFilled,
  Monitor,
  Clock,
  Check,
  TrendCharts,
  VideoPause,
  CloseBold,
  Coin,
  DataAnalysis,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const taskId = route.params.id as string

const activeTab = ref('overview')
const vmSearch = ref('')
const vmList = ref<any[]>([])
const vmListLoading = ref(false)
const taskLogs = ref<any[]>([])
const logsLoading = ref(false)
const pollTimer = ref<number | null>(null)
const pollTimeout = ref<number | null>(null)

const analysisLoading = reactive({
  zombie: false,
  rightsize: false,
  tidal: false,
  health: false
})

const analysisData = reactive<{
  zombie: any[]
  rightsize: any[]
  tidal: any[]
  health: any | null
}>({
  zombie: [],
  rightsize: [],
  tidal: [],
  health: null
})

const task = computed(() => taskStore.getTask(taskId))

const analyses = [
  { key: 'zombie', title: '僵尸 VM 检测', description: '识别长期低负载的虚拟机', icon: 'Monitor', color: 'orange' },
  { key: 'rightsize', title: 'Right Sizing', description: '资源配置优化建议', icon: 'TrendCharts', color: 'blue' },
  { key: 'tidal', title: '潮汐模式', description: '发现周期性规律', icon: 'Coin', color: 'green' },
  { key: 'health', title: '健康评分', description: '平台健康度评估', icon: 'DataAnalysis', color: 'purple' }
]

const completedAnalyses = computed(() => {
  const results = task.value?.analysisResults
  if (!results) return 0
  return Object.values(results).filter(v => v).length
})

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

  if (task.value.connectionId) {
    await loadVMList(task.value.connectionId)
  }

  if (task.value.backendTaskId) {
    await loadTaskLogs()
    await loadAnalysisResultFromBackend(task.value.backendTaskId)
    pollTaskStatus(task.value.backendTaskId)
  }
})

onUnmounted(() => {
  stopPolling()
})

async function loadVMList(connectionId: number) {
  vmListLoading.value = true
  try {
    vmList.value = await ConnectionAPI.listVMs(connectionId)
  } catch (error: any) {
    ElMessage.error('加载虚拟机列表失败: ' + (error.message || '未知错误'))
  } finally {
    vmListLoading.value = false
  }
}

function stopPolling() {
  if (pollTimer.value !== null) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  if (pollTimeout.value !== null) {
    clearTimeout(pollTimeout.value)
    pollTimeout.value = null
  }
}

function pollTaskStatus(backendTaskId: number) {
  stopPolling()

  pollTimer.value = window.setInterval(async () => {
    try {
      const taskInfo = await ConnectionAPI.getTask(backendTaskId)

      if (task.value) {
        task.value.status = taskInfo.status as any
        task.value.progress = taskInfo.progress
        task.value.error = taskInfo.error
        taskStore.saveTasksToStorage()

        if (taskInfo.status === 'completed') {
          stopPolling()
          if (task.value.connectionId) {
            await loadVMList(task.value.connectionId)
          }
          await loadTaskLogs()
          await loadAnalysisResultFromBackend(backendTaskId)
        } else if (taskInfo.status === 'failed') {
          stopPolling()
          await loadTaskLogs()
          ElMessage.error('任务执行失败: ' + (taskInfo.error || '未知错误'))
        }
      }
    } catch (error) {
      console.error('Failed to poll task status:', error)
    }
  }, 2000)

  pollTimeout.value = window.setTimeout(() => {
    stopPolling()
  }, 5 * 60 * 1000)
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('确定要取消此任务吗？', '确认取消', { type: 'warning' })

    if (task.value?.backendTaskId) {
      await ConnectionAPI.stopTask(task.value.backendTaskId)
    }

    taskStore.cancelTask(taskId)
    taskStore.saveTasksToStorage()
    ElMessage.success('任务已取消')
    router.push('/')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '取消任务失败')
    }
  }
}

async function handleRetry() {
  if (!task.value?.backendTaskId) {
    ElMessage.warning('该任务没有后端任务ID，无法重试')
    return
  }

  try {
    const newBackendTaskId = await ConnectionAPI.retryTask(task.value.backendTaskId)
    task.value.backendTaskId = newBackendTaskId
    task.value.status = 'pending'
    task.value.progress = 0
    task.value.error = ''
    taskStore.saveTasksToStorage()
    pollTaskStatus(newBackendTaskId)
    ElMessage.success('任务已提交重试')
  } catch (error: any) {
    ElMessage.error(error.message || '重试失败')
  }
}

async function loadTaskLogs() {
  if (!task.value?.backendTaskId) return

  logsLoading.value = true
  try {
    taskLogs.value = await ConnectionAPI.getTaskLogs(task.value.backendTaskId, 200)
  } catch (error: any) {
    ElMessage.error(error.message || '获取任务日志失败')
  } finally {
    logsLoading.value = false
  }
}

async function loadAnalysisResultFromBackend(backendTaskId: number) {
  try {
    const result = await ConnectionAPI.getAnalysisResult(backendTaskId)
    if (!result) return

    if (Array.isArray(result.zombie)) {
      analysisData.zombie = result.zombie
      taskStore.updateAnalysisResult(taskId, 'zombie', true)
    }
    if (Array.isArray(result.rightsize)) {
      analysisData.rightsize = result.rightsize
      taskStore.updateAnalysisResult(taskId, 'rightsize', true)
    }
    if (Array.isArray(result.tidal)) {
      analysisData.tidal = result.tidal
      taskStore.updateAnalysisResult(taskId, 'tidal', true)
    }
    if (result.health) {
      analysisData.health = result.health
      taskStore.updateAnalysisResult(taskId, 'health', true)
    }

    taskStore.saveTasksToStorage()
  } catch (error) {
    console.error('Failed to load analysis result from backend:', error)
  }
}

function getDefaultAnalysisConfig(type: string) {
  if (type === 'zombie') {
    return {
      analysis_days: 30,
      cpu_threshold: 5,
      memory_threshold: 10,
      min_confidence: 60
    }
  }
  if (type === 'rightsize') {
    return {
      analysis_days: 30,
      buffer_ratio: 0.2
    }
  }
  if (type === 'tidal') {
    return {
      analysis_days: 30,
      min_stability: 0.6
    }
  }
  return {}
}

async function runAnalysis(type: string) {
  if (!task.value?.connectionId) {
    ElMessage.warning('缺少连接信息，无法执行分析')
    return
  }

  const analysisType = type as 'zombie' | 'rightsize' | 'tidal' | 'health'
  analysisLoading[analysisType] = true

  try {
    if (type === 'zombie') {
      analysisData.zombie = await ConnectionAPI.detectZombieVMs(task.value.connectionId, getDefaultAnalysisConfig('zombie'))
    } else if (type === 'rightsize') {
      analysisData.rightsize = await ConnectionAPI.analyzeRightSize(task.value.connectionId, getDefaultAnalysisConfig('rightsize'))
    } else if (type === 'tidal') {
      analysisData.tidal = await ConnectionAPI.detectTidalPattern(task.value.connectionId, getDefaultAnalysisConfig('tidal'))
    } else if (type === 'health') {
      analysisData.health = await ConnectionAPI.analyzeHealthScore(task.value.connectionId)
    }

    taskStore.updateAnalysisResult(taskId, analysisType, true)
    taskStore.saveTasksToStorage()
    ElMessage.success('分析完成')
  } catch (error: any) {
    ElMessage.error(error.message || '分析执行失败')
  } finally {
    analysisLoading[analysisType] = false
  }
}

function buildReportTypes() {
  const result: string[] = []
  const flags = task.value?.analysisResults || {}

  if (flags.zombie) result.push('zombie')
  if (flags.rightsize) result.push('rightsize')
  if (flags.tidal) result.push('tidal')
  if (flags.health) result.push('health')

  if (result.length === 0) {
    result.push('zombie', 'rightsize', 'tidal', 'health')
  }

  return result
}

async function handleCommand(cmd: string) {
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除此任务吗？', '确认删除', { type: 'warning' })
      stopPolling()
      taskStore.deleteTask(taskId)
      taskStore.saveTasksToStorage()
      ElMessage.success('任务已删除')
      router.push('/')
    } catch {
      // 用户取消
    }
  }
}

async function exportReport() {
  if (!task.value?.connectionId) {
    ElMessage.warning('缺少连接信息，无法导出报告')
    return
  }

  try {
    ElMessage.info('正在生成后端报告...')
    const filepath = await exportTaskReport({
      taskId,
      connectionId: task.value.connectionId,
      reportTypes: buildReportTypes(),
      title: task.value.name
    })
    ElMessage.success('报告已导出: ' + filepath)
  } catch (error: any) {
    ElMessage.error('导出失败: ' + (error.message || '未知错误'))
  }
}

function getStatusType(status: string | undefined) {
  const typeMap: Record<string, string> = {
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
  return textMap[status || ''] || (status || '')
}

function formatMemory(mb: number): string {
  if (mb >= 1024) {
    return (mb / 1024).toFixed(1) + ' GB'
  }
  return mb + ' MB'
}

function formatDuration(taskData: Task | undefined): string {
  if (!taskData?.started_at || !taskData.ended_at) return '-'
  const start = new Date(taskData.started_at).getTime()
  const end = new Date(taskData.ended_at).getTime()
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
