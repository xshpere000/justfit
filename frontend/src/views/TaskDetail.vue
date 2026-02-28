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
    <div v-if="task?.status === 'running' || task?.status === 'paused' || task?.status === 'pending'"
      class="running-state">
      <el-card>
        <div class="progress-content">
          <div class="progress-info">
            <el-icon :size="48" class="progress-icon">
              <component :is="(task.status === 'running' || task.status === 'pending') ? 'Loading' : 'VideoPause'" />
            </el-icon>
            <div class="progress-text">
              <h3>{{ (task.status === 'running' || task.status === 'pending') ? '正在采集数据...' : '任务已暂停' }}</h3>
              <p>{{ task.currentStep || '初始化中...' }}</p>
            </div>
          </div>
          <div class="progress-bar">
            <el-progress :percentage="task.progress" :status="task.status === 'paused' ? 'exception' : undefined"
              :stroke-width="12" />
            <div class="progress-stats">
              <span>{{ task.collectedVMCount || 0 }} / {{ task.vmCount || 0 }} 台虚拟机</span>
              <span>{{ task.progress }}%</span>
            </div>
          </div>
          <div class="progress-actions">
            <el-button-group>
              <el-button @click="handleCancel">
                <el-icon>
                  <CloseBold />
                </el-icon>
                取消任务
              </el-button>
            </el-button-group>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 任务已完成状态 -->
    <div v-else-if="task?.status === 'completed'" class="completed-state">
      <!-- Tab 导航 -->
      <el-tabs v-model="activeTab" class="task-tabs">
        <el-tab-pane label="概览" name="overview">
          <div class="overview-content">
            <!-- 任务统计 -->
            <el-row :gutter="20" class="stats-row">
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32">
                    <Monitor />
                  </el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ task.vmCount }}</div>
                    <div class="stat-label">虚拟机数量</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32">
                    <Clock />
                  </el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ formatDuration(task) }}</div>
                    <div class="stat-label">采集耗时</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32">
                    <Check />
                  </el-icon>
                  <div class="stat-content">
                    <div class="stat-value">{{ completedAnalyses }}</div>
                    <div class="stat-label">已完成分析</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <el-icon class="stat-icon" :size="32">
                    <TrendCharts />
                  </el-icon>
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
                  <div class="analysis-card" :class="{ completed: task.analysisResults?.[analysis.key] }"
                    @click="runAnalysis(analysis.key)">
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
            <!-- 任务进行中提示 -->
            <div v-if="!task?.id" class="vm-list-placeholder">
              <el-empty description="任务执行中，虚拟机列表将在任务完成后显示">
                <template #image>
                  <el-icon :size="60" class="is-loading">
                    <Loading />
                  </el-icon>
                </template>
              </el-empty>
            </div>
            <!-- 虚拟机列表 -->
            <template v-else>
              <div class="table-toolbar">
                <el-input v-model="vmSearch" placeholder="搜索虚拟机" prefix-icon="Search" clearable style="width: 300px"
                  @input="handleVMSearch" />
                <div class="table-stats">
                  共 {{ vmTotal }} 台虚拟机
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="vmList" stripe :loading="vmListLoading" height="400">
                  <el-table-column prop="name" label="虚拟机名称" min-width="180" />
                  <el-table-column prop="cpuCount" label="CPU" width="100">
                    <template #default="{ row }">
                      {{ row.cpuCount > 0 ? row.cpuCount + ' 核' : '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="memoryGb" label="内存" width="120">
                    <template #default="{ row }">
                      {{ row.memoryGb > 0 ? row.memoryGb + ' GB' : '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="powerState" label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getPowerStateType(row.powerState)" size="small">
                        {{ getPowerStateText(row.powerState) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="datacenter" label="数据中心" width="150" />
                  <el-table-column prop="hostIp" label="主机IP" width="150" />
                </el-table>
              </div>
              <div class="table-pagination">
                <el-pagination v-model:current-page="vmCurrentPage" v-model:page-size="vmPageSize"
                  :page-sizes="[20, 50, 100, 200]" :total="vmTotal" layout="total, sizes, prev, pager, next, jumper"
                  @current-change="handleVMPageChange" @size-change="handleVMSizeChange" />
              </div>
            </template>
          </div>
        </el-tab-pane>

        <el-tab-pane label="僵尸VM" name="zombie">
          <div class="analysis-content" v-if="task?.analysisResults?.zombie">
            <div class="analysis-toolbar">
              <el-input
                v-model="zombieSearch"
                placeholder="搜索虚拟机"
                clearable
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            <div class="table-wrapper" :style="{ height: listTableHeight + 'px' }">
              <el-table :data="pagedZombieData" stripe v-loading="analysisLoading.zombie" :height="listTableHeight" class="detail-table">
                <el-table-column prop="vmName" label="虚拟机" min-width="180" />
                <el-table-column prop="datacenter" label="数据中心" min-width="140" />
                <el-table-column prop="cpuUsage" label="CPU使用率" width="120">
                  <template #default="{ row }">{{ row.cpuUsage.toFixed(1) }}%</template>
                </el-table-column>
                <el-table-column prop="memoryUsage" label="内存使用率" width="120">
                  <template #default="{ row }">{{ row.memoryUsage.toFixed(1) }}%</template>
                </el-table-column>
                <el-table-column prop="confidence" label="置信度" width="100">
                  <template #default="{ row }">{{ row.confidence.toFixed(0) }}%</template>
                </el-table-column>
                <el-table-column prop="recommendation" label="建议" min-width="220" show-overflow-tooltip />
              </el-table>
            </div>
            <div class="logs-pagination" v-if="filteredZombieData.length > 0">
              <span class="logs-total">
                共 {{ filteredZombieData.length }} 条
              </span>
              <el-pagination
                v-model:current-page="zombieCurrentPage"
                v-model:page-size="analysisPageSize"
                :page-sizes="logsPageSizes"
                :total="filteredZombieData.length"
                :layout="logsPaginationLayout"
                :small="isCompactWindow"
              />
            </div>
            <el-empty v-if="!analysisLoading.zombie && filteredZombieData.length === 0" description="暂无分析结果" />
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
          <div class="analysis-content" v-if="task?.analysisResults?.rightsize">
            <div class="analysis-toolbar">
              <el-input
                v-model="rightsizeSearch"
                placeholder="搜索虚拟机"
                clearable
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            <div class="table-wrapper" :style="{ height: listTableHeight + 'px' }">
              <el-table :data="pagedRightsizeData" stripe v-loading="analysisLoading.rightsize" :height="listTableHeight" class="detail-table">
                <el-table-column prop="vmName" label="虚拟机" min-width="180" />
                <el-table-column prop="datacenter" label="数据中心" min-width="140" />
                <el-table-column prop="currentCpu" label="当前CPU" width="110" />
                <el-table-column prop="recommendedCpu" label="建议CPU" width="110" />
                <el-table-column prop="currentMemoryMb" label="当前内存" width="130">
                  <template #default="{ row }">{{ formatMemory(row.currentMemoryMb) }}</template>
                </el-table-column>
                <el-table-column prop="recommendedMemoryMb" label="建议内存" width="130">
                  <template #default="{ row }">{{ formatMemory(row.recommendedMemoryMb) }}</template>
                </el-table-column>
                <el-table-column prop="estimatedSaving" label="预计节省" min-width="120" />
              </el-table>
            </div>
            <div class="logs-pagination" v-if="filteredRightsizeData.length > 0">
              <span class="logs-total">
                共 {{ filteredRightsizeData.length }} 条
              </span>
              <el-pagination
                v-model:current-page="rightsizeCurrentPage"
                v-model:page-size="analysisPageSize"
                :page-sizes="logsPageSizes"
                :total="filteredRightsizeData.length"
                :layout="logsPaginationLayout"
                :small="isCompactWindow"
              />
            </div>
            <el-empty v-if="!analysisLoading.rightsize && filteredRightsizeData.length === 0" description="暂无分析结果" />
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
          <div class="analysis-content" v-if="task?.analysisResults?.tidal">
            <div class="analysis-toolbar">
              <el-input
                v-model="tidalSearch"
                placeholder="搜索虚拟机"
                clearable
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            <div class="table-wrapper" :style="{ height: listTableHeight + 'px' }">
              <el-table :data="pagedTidalData" stripe v-loading="analysisLoading.tidal" :height="listTableHeight" class="detail-table">
                <el-table-column prop="vmName" label="虚拟机" min-width="180" />
                <el-table-column prop="pattern" label="模式" width="120" />
                <el-table-column prop="stabilityScore" label="稳定性" width="100">
                  <template #default="{ row }">{{ row.stabilityScore.toFixed(0) }}%</template>
                </el-table-column>
                <el-table-column label="高峰时段" min-width="160">
                  <template #default="{ row }">{{ (row.peakHours || []).join(', ') || '-' }}</template>
                </el-table-column>
                <el-table-column label="高峰日期" min-width="160">
                  <template #default="{ row }">{{ (row.peakDays || []).join(', ') || '-' }}</template>
                </el-table-column>
                <el-table-column prop="recommendation" label="建议" min-width="220" show-overflow-tooltip />
              </el-table>
            </div>
            <div class="logs-pagination" v-if="filteredTidalData.length > 0">
              <span class="logs-total">
                共 {{ filteredTidalData.length }} 条
              </span>
              <el-pagination
                v-model:current-page="tidalCurrentPage"
                v-model:page-size="analysisPageSize"
                :page-sizes="logsPageSizes"
                :total="filteredTidalData.length"
                :layout="logsPaginationLayout"
                :small="isCompactWindow"
              />
            </div>
            <el-empty v-if="!analysisLoading.tidal && filteredTidalData.length === 0" description="暂无分析结果" />
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
          <div class="analysis-content" v-if="task?.analysisResults?.health">
            <el-card v-loading="analysisLoading.health">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="综合评分">
                  {{ analysisData.health?.overallScore !== undefined ? analysisData.health.overallScore.toFixed(0) + '%'
                  : '-'
                  }}
                </el-descriptions-item>
                <el-descriptions-item label="健康等级">{{ analysisData.health?.healthLevel ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="资源均衡">
                  {{ analysisData.health?.resourceBalance !== undefined ? analysisData.health.resourceBalance.toFixed(0)
                  + '%' :
                  '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="超配风险">
                  {{ analysisData.health?.overcommitRisk !== undefined ? analysisData.health.overcommitRisk.toFixed(0) +
                  '%' :
                  '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="热点集中">
                  {{ analysisData.health?.hotspotConcentration !== undefined ?
                    analysisData.health.hotspotConcentration.toFixed(0) + '%' : '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="虚机数量">{{ analysisData.health?.vmCount ?? '-' }}</el-descriptions-item>
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

        <el-tab-pane label="评估模式" name="analysisMode">
          <AnalysisModeTab v-if="task?.id" :task-id="task.id" :task-status="task.status" />
          <div v-else class="analysis-placeholder">
            <el-empty description="任务未完成，无法配置评估模式" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="分析报告" name="reports">
          <div class="reports-content">
            <!-- 导出按钮组 -->
            <div class="export-section">
              <el-card>
                <div class="export-header">
                  <div>
                    <h3>生成报告</h3>
                    <p style="color: var(--el-text-color-secondary); margin-top: 4px;">
                      根据本任务的分析结果生成报告文件
                    </p>
                  </div>
                  <el-space>
                    <el-button type="primary" size="large" @click="exportReport('xlsx')" :loading="exporting.xlsx">
                      <el-icon>
                        <DocumentCopy />
                      </el-icon>
                      Excel 数据表
                    </el-button>
                    <el-button type="success" size="large" @click="exportReport('pdf')" :loading="exporting.pdf">
                      <el-icon>
                        <Notebook />
                      </el-icon>
                      PDF 分析报告
                    </el-button>
                  </el-space>
                </div>

                <!-- 报告说明 -->
                <el-divider />
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="Excel 数据表">
                    包含所有采集数据和分析结果的详细表格，支持数据筛选和排序
                  </el-descriptions-item>
                  <el-descriptions-item label="PDF 分析报告">
                    可视化报告，包含图表和统计信息，适合阅读和分享
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </div>

            <!-- 历史报告列表 -->
            <div class="report-history" style="margin-top: 20px;">
              <h4>历史报告</h4>
              <el-card v-loading="reportsLoading">
                <el-table v-if="reportHistory.length > 0" :data="reportHistory" stripe>
                  <el-table-column prop="title" label="报告名称" min-width="200" />
                  <el-table-column prop="format" label="格式" width="100">
                    <template #default="{ row }">
                      <el-tag :type="row.format === 'xlsx' ? 'primary' : 'success'" size="small">
                        {{ row.format.toUpperCase() }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="createdAt" label="生成时间" width="180" />
                  <el-table-column prop="fileSize" label="文件大小" width="120">
                    <template #default="{ row }">
                      {{ formatFileSize(row.fileSize) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="180" align="center">
                    <template #default="{ row }">
                      <el-button size="small" @click="downloadReport(row)">
                        <el-icon>
                          <Download />
                        </el-icon> 下载
                      </el-button>
                      <el-button size="small" type="danger" @click="deleteReport(row)">
                        <el-icon>
                          <Delete />
                        </el-icon>
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-else description="暂无历史报告，点击上方按钮生成报告" />
              </el-card>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="执行日志" name="logs">
          <div class="analysis-content">
            <!-- 工具栏：搜索和刷新 -->
            <div class="logs-toolbar">
              <el-input
                v-model="logsSearchText"
                placeholder="搜索日志内容..."
                clearable
                class="search-input"
                @input="onLogsSearchChange"
              >
                <template #prefix>
                  <el-icon>
                    <Search />
                  </el-icon>
                </template>
              </el-input>
              <div class="logs-actions">
                <el-button size="small" :disabled="!task?.id" @click="manualRefreshLogs" :loading="logsLoading">
                  刷新日志
                </el-button>
              </div>
            </div>

            <el-empty v-if="!task?.id" description="该任务没有后端任务ID，无法查询执行日志" />

            <!-- 日志表格区域 -->
            <div v-else class="logs-content">
              <div class="table-wrapper" :style="{ height: listTableHeight + 'px' }">
                <el-table
                  :data="paginatedLogs"
                  stripe
                  v-loading="logsLoading"
                  :height="listTableHeight"
                  class="detail-table"
                  :default-sort="{ prop: 'timestamp', order: 'descending' }"
                >
                  <el-table-column prop="timestamp" label="时间" width="180" sortable />
                  <el-table-column prop="level" label="级别" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getLogLevelType(row.level)" size="small">
                        {{ row.level }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="message" label="内容" min-width="400" show-overflow-tooltip />
                </el-table>
              </div>

              <!-- 分页 -->
              <div class="logs-pagination">
                <span class="logs-total">
                  共 {{ logsTotal }} 条
                </span>
                <el-pagination
                  v-model:current-page="logsCurrentPage"
                  v-model:page-size="logsPageSize"
                  :page-sizes="logsPageSizes"
                  :total="logsTotal"
                  :layout="logsPaginationLayout"
                  :small="isCompactWindow"
                />
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 任务失败状态 -->
    <div v-else-if="task?.status === 'failed'" class="failed-state">
      <el-result icon="error" title="任务执行失败" :sub-title="task.error">
        <template #extra>
          <el-button type="primary" :disabled="!task?.id" @click="handleRetry">重试任务</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore, type Task } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as ConnectionAPI from '@/api/connection'
import { exportTaskReport } from '@/api/report'
import * as App from '../../wailsjs/go/main/App'
import AnalysisModeTab from './AnalysisModeTab.vue'
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
  CircleClose,
  Loading,
  Search,
  DocumentCopy,
  Notebook,
  View,
  Delete
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

// 使用 computed 确保 taskId 随路由变化而更新
const taskId = computed(() => route.params.id as string)

const activeTab = ref('overview')
const vmSearch = ref('')
const zombieSearch = ref('')
const rightsizeSearch = ref('')
const tidalSearch = ref('')
const vmList = ref<any[]>([])
const vmListLoading = ref(false)
const vmTotal = ref(0)
const vmCurrentPage = ref(1)
const vmPageSize = ref(50)
const zombieCurrentPage = ref(1)
const rightsizeCurrentPage = ref(1)
const tidalCurrentPage = ref(1)
const analysisPageSize = ref(20)
const taskLogs = ref<any[]>([])
const allLogs = ref<any[]>([])  // 存储所有日志（用于过滤）
const logsLoading = ref(false)
const logsTotal = ref(0)
const logsCurrentPage = ref(1)
const logsPageSize = ref(30)
const logsSearchText = ref('')
const windowHeight = ref(window.innerHeight)
const windowWidth = ref(window.innerWidth)
const pollTimer = ref<number | null>(null)
const pollTimeout = ref<number | null>(null)
let vmSearchTimer: number | null = null

// 报告相关状态
const exporting = reactive({
  xlsx: false,
  pdf: false
})
const reportHistory = ref<any[]>([])
const reportsLoading = ref(false)

const isCompactWindow = computed(() => windowHeight.value <= 700 || windowWidth.value <= 1100)
const listTableHeight = computed(() => (isCompactWindow.value ? 500 : 800))
const vmPaginationLayout = computed(() =>
  isCompactWindow.value ? 'sizes, prev, pager, next' : 'sizes, prev, pager, next, jumper'
)
const logsPaginationLayout = computed(() =>
  isCompactWindow.value ? 'sizes, prev, pager, next' : 'sizes, prev, pager, next, jumper'
)
const vmPageSizes = computed(() => (isCompactWindow.value ? [10, 20, 50, 100] : [20, 50, 100, 200]))
const logsPageSizes = computed(() => (isCompactWindow.value ? [10, 20, 30, 50] : [10, 15, 30, 50, 100]))

const analysisLoading = reactive({
  zombie: false,
  rightsize: false,
  tidal: false,
  health: false
})

// 本地状态：跟踪哪些分析已完成（用于控制 Tab 显示）
const hasAnalysisResults = reactive({
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

const task = computed(() => taskStore.getTask(taskId.value))

// 调试：监听 task 变化
watch(task, (newTask) => {
  console.log('[TaskDetail] task changed:', newTask)
  console.log('[TaskDetail] task.analysisResults:', newTask?.analysisResults)
}, { immediate: true, deep: true })

// 分析项类型定义
interface AnalysisItem {
  key: 'zombie' | 'rightsize' | 'tidal' | 'health'
  title: string
  description: string
  icon: string
  color: string
}

const analyses: AnalysisItem[] = [
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

function matchByKeyword(row: any, keyword: string, fields: string[]) {
  if (!keyword) return true
  const q = keyword.toLowerCase().trim()
  return fields.some((field) => String(row?.[field] ?? '').toLowerCase().includes(q))
}

const filteredZombieData = computed(() => {
  return analysisData.zombie.filter((row) => matchByKeyword(row, zombieSearch.value, ['vmName', 'datacenter', 'recommendation']))
})

const filteredRightsizeData = computed(() => {
  return analysisData.rightsize.filter((row) => matchByKeyword(row, rightsizeSearch.value, ['vmName', 'datacenter', 'estimatedSaving']))
})

const filteredTidalData = computed(() => {
  return analysisData.tidal.filter((row) => matchByKeyword(row, tidalSearch.value, ['vmName', 'pattern', 'recommendation']))
})

const pagedZombieData = computed(() => {
  const start = (zombieCurrentPage.value - 1) * analysisPageSize.value
  return filteredZombieData.value.slice(start, start + analysisPageSize.value)
})

const pagedRightsizeData = computed(() => {
  const start = (rightsizeCurrentPage.value - 1) * analysisPageSize.value
  return filteredRightsizeData.value.slice(start, start + analysisPageSize.value)
})

const pagedTidalData = computed(() => {
  const start = (tidalCurrentPage.value - 1) * analysisPageSize.value
  return filteredTidalData.value.slice(start, start + analysisPageSize.value)
})

// 初始化任务数据
async function initTaskData() {
  // 重置状态
  stopPolling()
  activeTab.value = 'overview'
  vmSearch.value = ''
  zombieSearch.value = ''
  rightsizeSearch.value = ''
  tidalSearch.value = ''
  vmList.value = []
  vmTotal.value = 0
  vmCurrentPage.value = 1
  zombieCurrentPage.value = 1
  rightsizeCurrentPage.value = 1
  tidalCurrentPage.value = 1
  taskLogs.value = []
  allLogs.value = []
  analysisData.zombie = []
  analysisData.rightsize = []
  analysisData.tidal = []
  analysisData.health = null

  // 如果没有有效的 taskId，不执行后续操作
  if (!taskId.value) {
    console.log('[TaskDetail] 无效的 taskId')
    return
  }

  // 详细日志：输出任务信息用于诊断
  console.log('[TaskDetail] 初始化任务详情, taskId:', taskId.value)
  console.log('[TaskDetail] task.value:', task.value)

  if (!task.value) {
    ElMessage.error('任务不存在')
    router.push('/')
    return
  }

  console.log('[TaskDetail] 任务详情:', {
    id: task.value.id,
    connectionId: task.value.connectionId,
    status: task.value.status,
    selectedVMs: task.value.selectedVMs?.length
  })

  // 始终从后端同步最新数据，确保显示的是最新状态
  // 因为用户可能在任务列表停留了一段时间，此时任务状态可能已经变化
  console.log('[TaskDetail] 从后端同步最新任务数据')
  await syncTaskFromBackend()

  // 只有在任务已完成或有后端任务ID时才加载虚拟机列表
  // 任务进行中时，虚拟机列表会在任务完成后通过快照获取
  if (task.value.id) {
    console.log('[TaskDetail] 有id，加载VM列表:', task.value.id)
    await loadVMList()
  } else {
    console.log('[TaskDetail] 没有id，无法加载VM列表')
  }

  if (task.value.id) {
    await loadTaskLogs()
    await loadAnalysisResultFromBackend(task.value.id)
    pollTaskStatus(task.value.id)
    // 如果任务已完成，也加载报告历史
    if (task.value.status === 'completed') {
      await loadReportHistory()
    }
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)
  await initTaskData()
})

// 监听 taskId 变化，重新加载数据
watch(taskId, () => {
  initTaskData()
})

watch(zombieSearch, () => {
  zombieCurrentPage.value = 1
})

watch(rightsizeSearch, () => {
  rightsizeCurrentPage.value = 1
})

watch(tidalSearch, () => {
  tidalCurrentPage.value = 1
})

watch(analysisPageSize, () => {
  zombieCurrentPage.value = 1
  rightsizeCurrentPage.value = 1
  tidalCurrentPage.value = 1
})

// 监听标签页切换，刷新对应的数据
watch(activeTab, async (newTab) => {
  console.log('[TaskDetail] 切换标签页:', newTab)

  // 每次切换标签时，先同步一次最新的任务状态
  // 这样确保用户看到的数据是最新的
  if (task.value?.id) {
    try {
      const taskInfo = await ConnectionAPI.getTask(task.value.id)
      if (task.value) {
        task.value.status = taskInfo.status as any
        task.value.progress = taskInfo.progress
        task.value.error = taskInfo.error
        task.value.startedAt = taskInfo.startedAt
        task.value.completedAt = taskInfo.completedAt
      }
    } catch (error) {
      console.error('[TaskDetail] 同步任务状态失败:', error)
    }
  }

  // 根据切换到的标签页，刷新对应的数据
  switch (newTab) {
    case 'overview':
      console.log('[TaskDetail] 切换到概览标签')
      // 概览数据在 initTaskData 时已经加载
      break
    case 'vms':
      console.log('[TaskDetail] 切换到虚拟机标签')
      await loadVMList()
      break
    case 'logs':
      console.log('[TaskDetail] 切换到执行日志标签')
      await loadTaskLogs()  // 刷新日志
      break
    case 'analysis':
      console.log('[TaskDetail] 切换到分析结果标签')
      if (task.value?.id) {
        await loadAnalysisResultFromBackend(task.value.id)
      }
      break
    case 'reports':
      console.log('[TaskDetail] 切换到分析报告标签')
      // 报告列表不依赖 task.value.id，使用 taskId
      await loadReportHistory()
      break
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  stopPolling()
})

function handleWindowResize() {
  windowHeight.value = window.innerHeight
  windowWidth.value = window.innerWidth
}

async function loadVMList() {
  await loadTaskVMs()
}

async function loadTaskVMs() {
  if (!task.value?.id) {
    console.log('[TaskDetail] loadTaskVMs: 没有id')
    return
  }

  console.log('[TaskDetail] loadTaskVMs: 开始加载, id=', task.value.id)
  vmListLoading.value = true
  try {
    const offset = (vmCurrentPage.value - 1) * vmPageSize.value
    console.log('[TaskDetail] 调用 listTaskVMs, params:', {
      id: task.value.id,
      limit: vmPageSize.value,
      offset,
      keyword: vmSearch.value
    })
    const result = await ConnectionAPI.listTaskVMs(
      task.value.id,
      vmPageSize.value,
      offset,
      vmSearch.value
    )
    console.log('[TaskDetail] listTaskVMs 返回结果:', result)
    vmList.value = result.vms || []
    vmTotal.value = result.total || 0
    console.log('[TaskDetail] VM列表加载完成, 数量:', vmList.value.length, '总数:', vmTotal.value)
  } catch (error: any) {
    const errorMsg = error?.message || error?.toString() || '未知错误'
    console.error('[TaskDetail] 加载任务快照失败:', errorMsg)
    console.error('[TaskDetail] 错误详情:', error)

    // 如果任务快照不存在，尝试从连接的数据库加载
    if (task.value?.connectionId) {
      console.log('[TaskDetail] 快照不存在，尝试从connectionId加载虚拟机, connectionId=', task.value.connectionId)
      try {
        vmList.value = await ConnectionAPI.listVMs(task.value.connectionId)
        vmTotal.value = vmList.value.length
        console.log('[TaskDetail] 从connectionId加载VM成功, 数量:', vmList.value.length)
      } catch (e: any) {
        console.error('[TaskDetail] 从数据库加载虚拟机列表失败:', e)
        vmList.value = []
        vmTotal.value = 0
      }
    } else {
      console.log('[TaskDetail] 没有connectionId，无法加载虚拟机')
      vmList.value = []
      vmTotal.value = 0
    }
  } finally {
    vmListLoading.value = false
  }
}

function handleVMPageChange(page: number) {
  vmCurrentPage.value = page
  loadTaskVMs()
}

function handleVMSizeChange(size: number) {
  vmPageSize.value = size
  vmCurrentPage.value = 1
  loadTaskVMs()
}

function handleVMSearch() {
  vmCurrentPage.value = 1
  if (vmSearchTimer) {
    clearTimeout(vmSearchTimer)
  }
  vmSearchTimer = window.setTimeout(() => {
    loadTaskVMs()
  }, 300)
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

function pollTaskStatus(id: number) {
  console.log('[TaskDetail] pollTaskStatus 开始轮询任务状态, taskId:', id)
  stopPolling()

  let logRefreshCounter = 0  // 日志刷新计数器：任务运行中每 5 次轮询（10秒）刷新一次日志

  pollTimer.value = window.setInterval(async () => {
    try {
      const taskInfo = await ConnectionAPI.getTask(id)
      console.log('[TaskDetail] pollTaskStatus 轮询结果, taskId:', id, 'status:', taskInfo.status, 'progress:', taskInfo.progress)

      if (task.value) {
        task.value.status = taskInfo.status as any
        task.value.progress = taskInfo.progress
        task.value.error = taskInfo.error
        // 同步时间戳，用于计算耗时
        if (taskInfo.startedAt) {
          task.value.startedAt = taskInfo.startedAt
        }
        if (taskInfo.completedAt) {
          task.value.completedAt = taskInfo.completedAt
        }

        // 任务运行中时，每 5 次轮询刷新一次日志（每 10 秒）
        if (taskInfo.status === 'running') {
          logRefreshCounter++
          if (logRefreshCounter >= 5) {
            console.log('[TaskDetail] pollTaskStatus 自动刷新日志, taskId:', id)
            await loadTaskLogs()  // 静默刷新，不显示提示
            logRefreshCounter = 0
          }
        } else if (taskInfo.status === 'completed') {
          console.log('[TaskDetail] pollTaskStatus 任务完成, 停止轮询, taskId:', id)
          stopPolling()
          if (task.value.connectionId) {
            await loadVMList()
          }
          await loadTaskLogs()
          await loadAnalysisResultFromBackend(id)
        } else if (taskInfo.status === 'failed') {
          console.log('[TaskDetail] pollTaskStatus 任务失败, 停止轮询, taskId:', id, 'error:', taskInfo.error)
          stopPolling()
          await loadTaskLogs()
          ElMessage.error('任务执行失败: ' + (taskInfo.error || '未知错误'))
        }
      }
    } catch (error) {
      console.error('[TaskDetail] pollTaskStatus 轮询任务状态失败:', error)
    }
  }, 2000)

  pollTimeout.value = window.setTimeout(() => {
    console.log('[TaskDetail] pollTaskStatus 轮询超时, 停止轮询, taskId:', id)
    stopPolling()
  }, 5 * 60 * 1000)
}

async function handleCancel() {
  console.log('[TaskDetail] handleCancel 用户请求取消任务, taskId:', taskId.value)
  try {
    await ElMessageBox.confirm('确定要取消此任务吗？', '确认取消', { type: 'warning' })

    console.log('[TaskDetail] handleCancel 用户确认取消, 调用 store.cancelTask')
    await taskStore.cancelTask(taskId.value)
    ElMessage.success('任务已取消')
    console.log('[TaskDetail] handleCancel 取消成功, 返回首页')
    router.push('/')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '取消任务失败')
    }
  }
}

async function handleRetry() {
  console.log('[TaskDetail] handleRetry 用户请求重试任务, taskId:', task.value?.id)

  if (!task.value?.id) {
    console.warn('[TaskDetail] handleRetry 任务无效，无法重试')
    ElMessage.warning('该任务没有后端任务ID，无法重试')
    return
  }

  try {
    console.log('[TaskDetail] handleRetry 调用 retryTask API, taskId:', task.value.id)
    const newTaskId = await ConnectionAPI.retryTask(task.value.id)
    console.log('[TaskDetail] handleRetry 重试成功, newTaskId:', newTaskId)

    // 刷新任务列表
    await taskStore.syncTasksFromBackend()
    // 跳转到新任务页面
    router.push('/task/' + newTaskId)
    ElMessage.success('任务已提交重试')
  } catch (error: any) {
    ElMessage.error(error.message || '重试失败')
  }
}

// 加载日志（静默，不显示成功提示）
async function loadTaskLogs() {
  if (!task.value?.id) return

  logsLoading.value = true
  try {
    // 获取所有日志数据（后端 limit 参数较大，获取全部）
    const logs = await ConnectionAPI.getTaskLogs(task.value.id, 10000)
    allLogs.value = logs

    // 应用搜索过滤
    applyLogFilter()
  } catch (error: any) {
    ElMessage.error(error.message || '获取任务日志失败')
  } finally {
    logsLoading.value = false
  }
}

// 手动刷新日志（带成功提示）
async function manualRefreshLogs() {
  await loadTaskLogs()
  ElMessage.success(`刷新成功，共 ${logsTotal.value} 条记录`)
}

// 应用搜索过滤
function applyLogFilter() {
  let filteredLogs = allLogs.value

  if (logsSearchText.value) {
    const searchLower = logsSearchText.value.toLowerCase()
    filteredLogs = allLogs.value.filter((log: any) =>
      log.message?.toLowerCase().includes(searchLower) ||
      log.level?.toLowerCase().includes(searchLower)
    )
  }

  taskLogs.value = filteredLogs
  logsTotal.value = filteredLogs.length

  // 如果当前页超过总页数，重置到第一页
  const maxPage = Math.ceil(filteredLogs.length / logsPageSize.value) || 1
  if (logsCurrentPage.value > maxPage) {
    logsCurrentPage.value = 1
  }
}

// 分页后的日志数据
const paginatedLogs = computed(() => {
  const start = (logsCurrentPage.value - 1) * logsPageSize.value
  const end = start + logsPageSize.value
  return taskLogs.value.slice(start, end)
})

// 日志级别对应的 Tag 类型
function getLogLevelType(level: string) {
  const levelMap: Record<string, string> = {
    'error': 'danger',
    'warn': 'warning',
    'warning': 'warning',
    'info': 'info',
    'debug': '',
    'success': 'success',
    'system': 'info'
  }
  return levelMap[level] || ''
}

// 防抖搜索
function onLogsSearchChange() {
  if (vmSearchTimer) {
    clearTimeout(vmSearchTimer)
  }
  vmSearchTimer = window.setTimeout(() => {
    logsCurrentPage.value = 1 // 重置到第一页
    applyLogFilter()  // 只过滤，不重新请求
  }, 300)
}

async function loadAnalysisResultFromBackend(id: number) {
  console.log('[loadAnalysisResultFromBackend] 开始加载分析结果, id:', id)
  try {
    // 使用正确的 API: GetTaskAnalysisResult 而不是 GetAnalysisResult
    // GetTaskAnalysisResult 返回的是按 analysis_type 分组的结果
    const result = await ConnectionAPI.getTaskAnalysisResult(id, '')
    console.log('[loadAnalysisResultFromBackend] 获取到结果:', result)
    if (!result) {
      console.warn('[loadAnalysisResultFromBackend] 结果为空')
      return
    }
    console.log('[loadAnalysisResultFromBackend] 结果键:', Object.keys(result))

    // 后端 Result 字段命名: zombieVM, rightSize, tidal, healthScore
    // 后端数据格式: { count: number, results: [...] }
    // 需要转换为前端期望的格式

    if (result.zombieVM) {
      console.log('[loadAnalysisResultFromBackend] 找到 zombieVM 数据:', result.zombieVM)
      const zombieData = result.zombieVM as { count?: number; results?: any[] }
      if (Array.isArray(zombieData.results)) {
        analysisData.zombie = zombieData.results
        hasAnalysisResults.zombie = true
        console.log('[loadAnalysisResultFromBackend] zombie 结果加载完成, 数量:', zombieData.results.length)
      } else if (Array.isArray(result.zombieVM)) {
        // 兼容直接返回数组的情况
        analysisData.zombie = result.zombieVM
        hasAnalysisResults.zombie = true
        console.log('[loadAnalysisResultFromBackend] zombie 结果加载完成(数组), 数量:', result.zombieVM.length)
      } else {
        console.warn('[loadAnalysisResultFromBackend] zombieVM 数据格式异常:', typeof result.zombieVM)
      }
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 zombieVM 数据')
    }

    // right_size -> rightsize
    if (result.rightSize) {
      console.log('[loadAnalysisResultFromBackend] 找到 rightSize 数据:', result.rightSize)
      const rightSizeData = result.rightSize as { count?: number; results?: any[] }
      if (Array.isArray(rightSizeData.results)) {
        analysisData.rightsize = rightSizeData.results
        hasAnalysisResults.rightsize = true
        console.log('[loadAnalysisResultFromBackend] rightsize 结果加载完成, 数量:', rightSizeData.results.length)
      } else if (Array.isArray(result.rightSize)) {
        analysisData.rightsize = result.rightSize
        hasAnalysisResults.rightsize = true
        console.log('[loadAnalysisResultFromBackend] rightsize 结果加载完成(数组), 数量:', result.rightSize.length)
      } else {
        console.warn('[loadAnalysisResultFromBackend] rightSize 数据格式异常:', typeof result.rightSize)
      }
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 rightSize 数据')
    }

    // tidal
    if (result.tidal) {
      console.log('[loadAnalysisResultFromBackend] 找到 tidal 数据:', result.tidal)
      const tidalData = result.tidal as { count?: number; results?: any[] }
      if (Array.isArray(tidalData.results)) {
        analysisData.tidal = tidalData.results
        hasAnalysisResults.tidal = true
        console.log('[loadAnalysisResultFromBackend] tidal 结果加载完成, 数量:', tidalData.results.length)
      } else if (Array.isArray(result.tidal)) {
        analysisData.tidal = result.tidal
        hasAnalysisResults.tidal = true
        console.log('[loadAnalysisResultFromBackend] tidal 结果加载完成(数组), 数量:', result.tidal.length)
      } else {
        console.warn('[loadAnalysisResultFromBackend] tidal 数据格式异常:', typeof result.tidal)
      }
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 tidal 数据')
    }

    // health_score -> health
    if (result.healthScore) {
      console.log('[loadAnalysisResultFromBackend] 找到 healthScore 数据:', result.healthScore)
      analysisData.health = result.healthScore
      hasAnalysisResults.health = true
      console.log('[loadAnalysisResultFromBackend] health 结果加载完成')
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 healthScore 数据')
    }

  } catch (error) {
    console.error('[loadAnalysisResultFromBackend] 加载失败:', error)
  }
}

function getDefaultAnalysisConfig(type: string) {
  if (type === 'zombie') {
    return {
      analysisDays: 30,
      cpuThreshold: 5,
      memoryThreshold: 10,
      minConfidence: 60
    }
  }
  if (type === 'rightsize') {
    return {
      analysisDays: 30,
      bufferRatio: 0.2
    }
  }
  if (type === 'tidal') {
    return {
      analysisDays: 30,
      minStability: 0.6
    }
  }
  return {}
}

async function runAnalysis(type: string) {
  console.log('[runAnalysis] 开始执行分析:', type)

  // 检查是否有有效的评估任务ID
  const assessmentTaskId = task.value?.id
  if (!assessmentTaskId) {
    console.warn('[runAnalysis] 缺少评估任务ID (id)')
    ElMessage.warning('缺少评估任务信息，无法执行分析')
    return
  }

  const analysisType = type as 'zombie' | 'rightsize' | 'tidal' | 'health'
  analysisLoading[analysisType] = true

  try {
    const config = getDefaultAnalysisConfig(analysisType)

    // 前端类型映射到后端 analysis_type
    const typeMapping: Record<string, string> = {
      zombie: 'zombie',
      rightsize: 'rightsize',
      tidal: 'tidal',
      health: 'health'
    }
    const backendAnalysisType = typeMapping[analysisType]

    console.log('[runAnalysis] 创建分析子任务:', { assessmentTaskId, analysisType: backendAnalysisType, config })

    // 使用新 API：在评估任务下创建分析子任务
    const jobId = await ConnectionAPI.runAnalysisJob(
      assessmentTaskId,
      backendAnalysisType,
      config
    )
    console.log('[runAnalysis] 分析子任务已创建，jobId:', jobId)

    ElMessage.info('分析任务已创建，正在执行中...')

    // 轮询子任务状态直到完成
    let pollCount = 0
    const maxPolls = 300 // 最多轮询5分钟
    const pollInterval = setInterval(async () => {
      pollCount++
      try {
        console.log(`[runAnalysis] 轮询子任务状态 #${pollCount}, jobId:`, jobId)
        const jobStatus = await ConnectionAPI.getAnalysisJobStatus(jobId)
        console.log('[runAnalysis] 子任务状态:', jobStatus.status, 'progress:', jobStatus.progress, 'error:', jobStatus.error)

        if (jobStatus.status === 'completed') {
          clearInterval(pollInterval)
          analysisLoading[analysisType] = false
          console.log('[runAnalysis] 子任务完成，智能重试获取分析结果, assessmentTaskId:', assessmentTaskId)

          // 智能重试获取结果：等待数据库写入完成，最多重试 5 次
          const result = await fetchAnalysisResultWithRetry(assessmentTaskId, type)
          console.log('[runAnalysis] 最终分析结果:', result)
          console.log('[runAnalysis] 结果类型:', type, '结果键:', Object.keys(result))

          // 后端存储的是直接数组格式，不是 {count, results} 对象
          // 后端 Result 字段命名: zombieVM, rightSize, tidal, healthScore
          if (type === 'zombie') {
            // zombieVM 可能是数组或 {count, results} 格式
            if (result.zombieVM && Array.isArray(result.zombieVM)) {
              analysisData.zombie = result.zombieVM
            } else if (result.zombieVM && result.zombieVM.results && Array.isArray(result.zombieVM.results)) {
              analysisData.zombie = result.zombieVM.results
            } else {
              analysisData.zombie = []
            }
            // 无论是否有结果，只要分析完成就设置 Tab 显示状态
            hasAnalysisResults.zombie = true
            console.log('[runAnalysis] zombie 分析结果加载完成, 数量:', analysisData.zombie.length)
          } else if (type === 'rightsize') {
            // rightSize 可能是数组或 {count, results} 格式
            if (result.rightSize && Array.isArray(result.rightSize)) {
              analysisData.rightsize = result.rightSize
            } else if (result.rightSize && result.rightSize.results && Array.isArray(result.rightSize.results)) {
              analysisData.rightsize = result.rightSize.results
            } else {
              analysisData.rightsize = []
            }
            // 无论是否有结果，只要分析完成就设置 Tab 显示状态
            hasAnalysisResults.rightsize = true
            console.log('[runAnalysis] rightsize 分析结果加载完成, 数量:', analysisData.rightsize.length)
          } else if (type === 'tidal') {
            // tidal 可能是数组或 {count, results} 格式
            if (result.tidal && Array.isArray(result.tidal)) {
              analysisData.tidal = result.tidal
            } else if (result.tidal && result.tidal.results && Array.isArray(result.tidal.results)) {
              analysisData.tidal = result.tidal.results
            } else {
              analysisData.tidal = []
            }
            // 无论是否有结果，只要分析完成就设置 Tab 显示状态
            hasAnalysisResults.tidal = true
            console.log('[runAnalysis] tidal 分析结果加载完成, 数量:', analysisData.tidal.length)
          } else if (type === 'health') {
            analysisData.health = result.healthScore || null
            // 设置本地状态，控制 Tab 显示
            hasAnalysisResults.health = true
            console.log('[runAnalysis] health 分析结果加载完成:', analysisData.health)
          }

          console.log('[runAnalysis] analysisData.zombie.length:', analysisData.zombie.length)
          console.log('[runAnalysis] task.analysisResults:', task.value?.analysisResults)
          ElMessage.success('分析完成')
        } else if (jobStatus.status === 'failed') {
          clearInterval(pollInterval)
          analysisLoading[analysisType] = false
          console.error('[runAnalysis] 子任务失败:', jobStatus.error)
          ElMessage.error(jobStatus.error || '分析执行失败')
        } else if (pollCount >= maxPolls) {
          clearInterval(pollInterval)
          analysisLoading[analysisType] = false
          console.error('[runAnalysis] 轮询超时')
          ElMessage.error('分析执行超时')
        }
      } catch (e) {
        clearInterval(pollInterval)
        analysisLoading[analysisType] = false
        console.error('[runAnalysis] 轮询子任务状态失败:', e)
      }
    }, 1000)

  } catch (error: any) {
    console.error('[runAnalysis] 创建分析子任务失败:', error)
    ElMessage.error(error.message || '分析执行失败')
    analysisLoading[analysisType] = false
  }
}

/**
 * 智能重试获取分析结果
 * - 检查结果是否包含目标类型的数据
 * - 如果没有数据，等待 300ms 后重试
 * - 最多重试 5 次（总计 1.5 秒）
 * - 如果有数据则立即返回
 */
async function fetchAnalysisResultWithRetry(
  taskId: number,
  analysisType: string
): Promise<any> {
  const maxRetries = 5
  const retryDelay = 300

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const result = await ConnectionAPI.getTaskAnalysisResult(taskId, '')
    console.log(`[fetchAnalysisResultWithRetry] 第 ${attempt} 次尝试，检查 ${analysisType} 数据`)

    // 检查是否已有数据
    if (checkHasData(result, analysisType)) {
      console.log(`[fetchAnalysisResultWithRetry] 第 ${attempt} 次获取到数据`)
      return result
    }

    // 如果是最后一次尝试，直接返回当前结果
    if (attempt === maxRetries) {
      console.warn(`[fetchAnalysisResultWithRetry] 已重试 ${maxRetries} 次，仍未获取到 ${analysisType} 数据，返回当前结果`)
      return result
    }

    // 等待后重试
    console.log(`[fetchAnalysisResultWithRetry] 第 ${attempt} 次未获取到数据，${retryDelay}ms 后重试`)
    await new Promise(resolve => setTimeout(resolve, retryDelay))
  }

  // 理论上不会到这里，但 TypeScript 需要返回值
  return await ConnectionAPI.getTaskAnalysisResult(taskId, '')
}

/**
 * 检查分析结果是否包含指定类型的数据
 */
function checkHasData(result: any, analysisType: string): boolean {
  if (!result) return false

  switch (analysisType) {
    case 'zombie':
      // zombie 数据检查：zombieVM 是数组且长度 > 0
      return !!(result.zombieVM && Array.isArray(result.zombieVM) && result.zombieVM.length > 0)

    case 'rightsize':
      // rightsize 数据检查：rightSize 是数组且长度 > 0
      return !!(result.rightSize && Array.isArray(result.rightSize) && result.rightSize.length > 0)

    case 'tidal':
      // tidal 数据检查：tidal 是数组且长度 > 0
      return !!(result.tidal && Array.isArray(result.tidal) && result.tidal.length > 0)

    case 'health':
      // health 数据检查：healthScore 存在
      return !!result.healthScore

    default:
      return false
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
      taskStore.deleteTask(taskId.value)
      ElMessage.success('任务已删除')
      router.push('/')
    } catch {
      // 用户取消
    }
  }
}

async function exportReport(format: string = 'xlsx') {
  if (!task.value?.connectionId) {
    ElMessage.warning('缺少连接信息，无法导出报告')
    return
  }

  try {
    exporting[format as keyof typeof exporting] = true
    ElMessage.info(`正在生成${format === 'xlsx' ? 'Excel' : 'PDF'}报告...`)

    await exportTaskReport({
      taskId: taskId.value,
      connectionId: task.value.connectionId,
      reportTypes: [format],
      title: task.value.name
    })

    ElMessage.success('报告已生成')
    // 刷新报告列表
    await loadReportHistory()
  } catch (error: any) {
    ElMessage.error('导出失败: ' + (error.message || '未知错误'))
  } finally {
    exporting[format as keyof typeof exporting] = false
  }
}

// 加载报告历史
async function loadReportHistory() {
  // 使用 taskId.value 而不是 task.value?.id，确保一致性
  if (!taskId.value) return

  try {
    reportsLoading.value = true
    console.log('[TaskDetail] 加载报告历史, taskId:', taskId.value)
    // taskId 是字符串，需要转换为数字
    const reports = await App.GetTaskReports(parseInt(taskId.value))
    console.log('[TaskDetail] 报告列表加载成功:', reports)
    reportHistory.value = reports
  } catch (error: any) {
    console.error('加载报告列表失败:', error)
    ElMessage.error('加载报告列表失败: ' + (error.message || '未知错误'))
  } finally {
    reportsLoading.value = false
  }
}

// 下载报告
async function downloadReport(report: any) {
  try {
    // 调用后端保存对话框 API
    const savedPath = await App.SaveReportAs(report.id)

    if (savedPath) {
      ElMessage.success('报告已保存到: ' + savedPath)
    } else {
      ElMessage.info('已取消保存')
    }
  } catch (error: any) {
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  }
}

// 删除报告
async function deleteReport(report: any) {
  try {
    await ElMessageBox.confirm('确定要删除此报告吗？此操作无法撤销。', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })

    await App.DeleteReport(report.id)
    ElMessage.success('报告已删除')

    // 刷新列表
    await loadReportHistory()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
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

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(i > 0 ? 1 : 0) + ' ' + sizes[i]
}

function formatDuration(taskData: Task | undefined): string {
  if (!taskData?.startedAt) return '-'
  // 任务进行中时不显示耗时，避免实时计算导致持续增长
  if (taskData.status === 'pending' || taskData.status === 'running') {
    return '进行中...'
  }
  if (!taskData.completedAt) return '-'
  const start = new Date(taskData.startedAt).getTime()
  const end = new Date(taskData.completedAt).getTime()
  const duration = end - start
  const seconds = Math.floor(duration / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    const mins = minutes % 60
    return hours + '小时' + (mins > 0 ? mins + '分钟' : '')
  }
  if (minutes > 0) {
    const secs = seconds % 60
    return minutes + '分钟' + (secs > 0 ? secs + '秒' : '')
  }
  return seconds + '秒'
}

// 从后端同步任务信息
async function syncTaskFromBackend() {
  try {
    console.log('[TaskDetail] 从后端获取任务列表')
    // 显式传递所有参数，包括 status 参数
    const backendTasks = await ConnectionAPI.listTasks('', 100, 0)
    console.log('[TaskDetail] 后端任务列表:', backendTasks)

    // 尝试匹配任务：通过前端任务的 created_at 时间或名称匹配
    if (task.value && backendTasks.length > 0) {
      // 按时间排序，找到最接近的前端任务
      const frontendTime = new Date(task.value.createdAt || 0).getTime()
      console.log('[TaskDetail] 前端任务创建时间:', frontendTime, task.value.createdAt)

      // 查找最近创建的后端任务（前后2分钟内）
      const matchedBackendTask = backendTasks.find((bt: any) => {
        if (!bt.createdAt) return false
        const backendTime = new Date(bt.createdAt).getTime()
        const timeDiff = Math.abs(backendTime - frontendTime)
        return timeDiff < 2 * 60 * 1000 // 2分钟内
      })

      if (matchedBackendTask) {
        console.log('[TaskDetail] 匹配到后端任务:', matchedBackendTask)
        task.value.id = matchedBackendTask.id
      } else {
        console.log('[TaskDetail] 未找到匹配的后端任务')
        // 列出所有后端任务供调试
        backendTasks.forEach((bt: any) => {
          console.log('[TaskDetail] 后端任务:', bt.id, bt.name, bt.createdAt, bt.status)
        })
      }
    }
  } catch (e: any) {
    console.error('[TaskDetail] 同步后端任务失败:', e)
  }
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
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  padding: $spacing-xl;
  box-sizing: border-box;
  overflow: hidden;
}

.completed-state {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.task-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;

  :deep(.el-tabs__content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.el-tab-pane) {
    height: 100%;
    min-height: 0;
  }
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
        from {
          transform: rotate(0deg);
        }

        to {
          transform: rotate(360deg);
        }
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
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .vm-list-placeholder {
    padding: 60px 0;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .table-toolbar {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin-bottom: 12px;
    gap: $spacing-sm;

    .search-input {
      width: 300px;
      max-width: 100%;
    }

  }

  .table-wrapper {
    border: 1px solid $border-color-light;
    border-radius: 8px;
    overflow: hidden;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: $spacing-md;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;

    :deep(.el-pagination) {
      justify-content: flex-end;
      flex-wrap: wrap;
      row-gap: 6px;
    }

    .logs-total {
      color: var(--el-text-color-secondary);
      font-size: 13px;
    }
  }
}

.analysis-content {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .table-wrapper {
    border: 1px solid $border-color-light;
    border-radius: 8px;
    overflow: hidden;
  }

  :deep(.el-table) {
    border: none;
  }

  :deep(.el-table th) {
    padding: 8px 0;
  }

  :deep(.el-table td) {
    padding: 7px 0;
  }

  .placeholder {
    padding: $spacing-xl;
    text-align: center;
    color: $text-color-secondary;
  }

  .analysis-toolbar {
    margin-bottom: 12px;

    .search-input {
      width: 300px;
      max-width: 100%;
    }
  }

  .logs-toolbar {
    margin-bottom: 12px;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: $spacing-sm;

    .search-input {
      width: 300px;
      max-width: 100%;
    }

    .logs-actions {
      margin-left: auto;
      display: inline-flex;
      align-items: center;
    }
  }

  .logs-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: $spacing-md;
    flex-wrap: wrap;
    gap: 8px;

    :deep(.el-pagination) {
      justify-content: flex-end;
      flex-wrap: wrap;
      row-gap: 6px;
    }
  }

  .logs-pagination {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;

    :deep(.el-pagination) {
      justify-content: flex-end;
      flex-wrap: wrap;
      row-gap: 6px;
    }

    .logs-total {
      color: var(--el-text-color-secondary);
      font-size: 13px;
    }
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

@media (max-width: 1024px), (max-height: 640px) {
  .task-detail-page {
    padding: $spacing-md;
    gap: $spacing-md;
  }

  .task-header {
    .header-left .task-title h1 {
      font-size: 18px;
      margin-bottom: 0;
    }
  }

  .vms-content {
    .table-toolbar {
      flex-wrap: wrap;
      align-items: flex-start;

      .search-input {
        width: 300px;
        max-width: 100%;
      }
    }

    .table-pagination {
      :deep(.el-pagination__total) {
        margin-right: 0;
      }
    }
  }

  .analysis-content {
    .logs-toolbar {
      flex-wrap: wrap;
      align-items: flex-start;

      .search-input {
        width: 300px;
        max-width: 100%;
      }
    }
  }
}
</style>
