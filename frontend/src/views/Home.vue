<template>
  <div class="home-page">
    <!-- 顶部 Banner 轮播 -->
    <div class="banner-section">
      <el-carousel :interval="5000" trigger="click" height="180px" arrow="always">
        <el-carousel-item v-for="feature in features" :key="feature.title">
          <div class="banner-item" :class="'banner--' + feature.color">
            <div class="banner-content">
              <div class="banner-text">
                <div class="banner-tag">核心功能</div>
                <h1 class="banner-title">{{ feature.title }}</h1>
                <p class="banner-desc">{{ feature.description }}</p>
                <el-button type="primary" round class="banner-btn" size="small" @click="startNewTask">立即体验</el-button>
              </div>
              <div class="banner-icon-bg">
                <el-icon><component :is="feature.icon" /></el-icon>
              </div>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
    </div>

    <!-- 任务管理区域 -->
    <div class="tasks-section">
      <div class="task-toolbar">
        <div class="toolbar-left">
          <h2 class="section-title">任务管理</h2>
          <el-input
            v-model="searchQuery"
            placeholder="搜索任务名称或连接..."
            :prefix-icon="Search"
            clearable
            class="search-input"
          />
        </div>
        <div class="toolbar-right">
             <el-radio-group v-model="filterStatus" class="status-filter">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="running">进行中</el-radio-button>
                <el-radio-button value="completed">已完成</el-radio-button>
              </el-radio-group>
            <el-button type="primary" class="create-btn" @click="startNewTask">
              <el-icon><Plus /></el-icon>新建任务
            </el-button>
        </div>
      </div>

      <div class="task-grid-container">
        <template v-if="filteredTasks.length > 0">
          <el-scrollbar class="task-scrollbar">
            <div class="task-grid">
            <div
              v-for="task in pagedTasks"
              :key="task.id"
              class="task-card"
              :class="'status--' + task.status"
              @click="openTask(task)"
            >
              <div class="card-header">
                <div class="platform-badge" :class="task.platform">
                  {{ task.platform === 'vcenter' ? 'vCenter' : 'UIS' }}
                </div>
                <div class="task-actions" @click.stop>
                   <el-dropdown trigger="click" @command="(cmd: string) => handleTaskCommand(cmd, task)">
                    <el-icon class="more-icon"><MoreFilled /></el-icon>
                    <template #dropdown>
                      <el-dropdown-menu>
                         <el-dropdown-item v-if="['running', 'pending'].includes(task.status)" command="pause">暂停任务</el-dropdown-item>
                         <el-dropdown-item v-if="task.status === 'paused'" command="resume">继续任务</el-dropdown-item>
                         <el-dropdown-item v-if="['running', 'paused', 'pending'].includes(task.status)" command="cancel" divided>取消任务</el-dropdown-item>
                         <el-dropdown-item command="delete" divided>删除任务</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>

              <div class="card-body">
                <h3 class="task-name" :title="task.name">{{ task.name }}</h3>
                <div class="task-connection">
                  <el-icon><Connection /></el-icon>
                  <span>{{ task.connectionName }}</span>
                  <span class="connection-host" v-if="task.host">({{ task.host }})</span>
                </div>
                <div class="task-time">
                  <el-icon><Clock /></el-icon>
                  <span>{{ formatTime(task.createdAt) }}</span>
                </div>
              </div>

              <div class="card-footer">
                <!-- 运行中/Pending/Paused -->
                <div v-if="['running', 'pending', 'paused'].includes(task.status)" class="status-running">
                   <div class="progress-info">
                      <span class="status-text">
                        <el-icon class="is-loading" v-if="task.status === 'running'"><Loading /></el-icon>
                        {{ getStatusText(task.status) }}
                      </span>
                      <span class="vm-info" v-if="task.vmCount">
                        {{ task.collectedVMCount || 0 }}/{{ task.vmCount }} VM
                      </span>
                      <span class="progress-val">{{ task.progress }}%</span>
                   </div>
                   <el-progress :percentage="task.progress" :show-text="false" :stroke-width="4" :status="task.status === 'paused' ? 'warning' : ''" />
                </div>

                <!-- 已完成 -->
                <div v-else-if="task.status === 'completed'" class="status-completed">
                   <div class="result-stat">
                      <div class="stat-item">
                        <span class="label">虚拟机</span>
                        <span class="val">{{ task.vmCount }}</span>
                      </div>
                      <el-divider direction="vertical" />
                       <div class="stat-item">
                        <span class="label">分析项</span>
                        <span class="val">{{ completedAnalyses(task.analysisResults) }}</span>
                      </div>
                   </div>
                   <div class="completed-tag">
                      <el-icon><CircleCheckFilled /></el-icon> 已完成
                   </div>
                </div>

                <!-- 失败/取消 -->
                <div v-else class="status-other">
                   <el-tag :type="task.status === 'failed' ? 'danger' : 'info'" effect="plain">
                      {{ getStatusText(task.status) }}
                   </el-tag>
                </div>
              </div>
            </div>
            </div>
          </el-scrollbar>

          <div class="task-pagination">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="filteredTasks.length"
              layout="total, prev, pager, next"
              background
              small
            />
          </div>
        </template>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <el-empty description="没有找到相关任务" :image-size="120" />
          <el-button type="primary" plain @click="startNewTask" v-if="tasks.length === 0">创建一个新任务</el-button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore, type Task } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Plus,
  MoreFilled,
  Connection,
  Clock,
  Loading,
  CircleCheckFilled,
  TrendCharts,
  Coin,
  FirstAidKit,
  Monitor
} from '@element-plus/icons-vue'

const router = useRouter()
const taskStore = useTaskStore()

const searchQuery = ref('')
const filterStatus = ref<'all' | 'running' | 'completed'>('all')
const currentPage = ref(1)
const pageSize = ref(8)

const features = [
  {
    icon: 'Monitor',
    title: '僵尸虚机检测',
    description: '通过智能算法识别长期低负载、长期关机或无流量的僵尸虚拟机，释放闲置资源。',
    color: 'orange'
  },
  {
    icon: 'TrendCharts',
    title: '资源规格优化 (RightSizing)',
    description: '基于历史负载数据，精准分析虚拟机资源配置合理性，建议升降配方案。',
    color: 'blue'
  },
  {
    icon: 'Coin',
    title: '潮汐模式分析',
    description: '挖掘业务资源使用的周期性规律（日/周/月），助力错峰调度与弹性伸缩。',
    color: 'purple'
  },
  {
    icon: 'FirstAidKit',
    title: '云平台健康体检',
    description: '全方位评估计算、存储、网络资源的健康状态，识别潜在风险点。',
    color: 'green'
  }
]

onMounted(async () => {
  console.log('[Home.vue] onMounted 初始化开始')

  // 从后端同步任务数据
  try {
    await taskStore.syncTasksFromBackend()
    console.log('[Home.vue] 任务列表同步成功, 任务数量:', taskStore.tasks.length)
    console.log('[Home.vue] 任务详情:', taskStore.tasks.map(t => ({
      id: t.id,
      name: t.name,
      vmCount: t.vmCount,
      status: t.status,
      progress: t.progress
    })))
  } catch (error) {
    console.error('[Home.vue] 任务列表同步失败:', error)
  }
})

const tasks = computed(() => {
  const result = taskStore.tasks
  // 添加日志检查computed值
  console.log('[Home.vue] tasks computed 被调用, 任务数量:', result.length)
  return result
})

const filteredTasks = computed(() => {
  let result = tasks.value

  // 1. 状态筛选
  if (filterStatus.value === 'running') {
    result = result.filter(t => ['running', 'paused', 'pending'].includes(t.status))
  } else if (filterStatus.value === 'completed') {
    result = result.filter(t => t.status === 'completed')
  }

  // 2. 搜索筛选
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(q) ||
      (t.connectionName && t.connectionName.toLowerCase().includes(q))
    )
  }

  // 3. 排序 (最新的在前)
  return [...result].sort((a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime())
})

const pagedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredTasks.value.slice(start, end)
})

watch([searchQuery, filterStatus], () => {
  currentPage.value = 1
})

watch(filteredTasks, (list) => {
  const maxPage = Math.max(1, Math.ceil(list.length / pageSize.value))
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage
  }
})

function formatTime(isoString: string | undefined): string {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return (date.getMonth() + 1) + '-' + date.getDate() + ' ' + date.getHours().toString().padStart(2, '0') + ':' + date.getMinutes().toString().padStart(2, '0')
}

function getStatusText(status: string) {
  const map: any = {
    pending: '等待中',
    running: '运行中',
    paused: '已暂停',
    completed: '成功',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status] || status
}

function completedAnalyses(results: any) {
  if (!results) return 0
  return Object.values(results).filter(v => v).length
}

function startNewTask() {
  if (taskStore.hasRunningTasks) {
    ElMessageBox.confirm(
      '当前有正在运行的任务，是否继续创建新任务？这可能会影响性能。',
      '提示',
      { type: 'warning', confirmButtonText: '继续', cancelButtonText: '取消' }
    ).then(() => router.push('/wizard')).catch(() => {})
  } else {
    router.push('/wizard')
  }
}

function openTask(task: Task) {
  // 如果是 completed / running / pending / paused 都可以进详情
  router.push('/task/' + task.id)
}

async function handleTaskCommand(cmd: string, task: Task) {
  console.log('[Home.vue] handleTaskCommand 被调用, command:', cmd, 'taskId:', task.id, 'taskName:', task.name)

  switch (cmd) {
    case 'pause':
      console.log('[Home.vue] 暂停任务, taskId:', task.id)
      await taskStore.pauseTask(task.id)
      break
    case 'resume':
      console.log('[Home.vue] 恢复任务, taskId:', task.id)
      await taskStore.resumeTask(task.id)
      break
    case 'cancel':
      ElMessageBox.confirm('确定取消该任务吗？', '提示', { type: 'warning' })
        .then(async () => {
          console.log('[Home.vue] 用户确认取消任务, taskId:', task.id)
          await taskStore.cancelTask(task.id)
        })
        .catch(() => console.log('[Home.vue] 用户取消取消任务操作'))
      break
    case 'delete':
      ElMessageBox.confirm('确定删除该任务记录吗？', '提示', { type: 'warning' })
        .then(async () => {
          console.log('[Home.vue] 用户确认删除任务, taskId:', task.id)
          await taskStore.deleteTask(task.id)
        })
        .catch(() => console.log('[Home.vue] 用户取消删除任务操作'))
      break
  }
}
</script>

<style scoped lang="scss">
.home-page {
  height: 100%;
  padding: 0;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
  overflow: hidden;
}

/* 顶部 Banner 区域 */
.banner-section {
  flex: 0 0 auto;

  :deep(.el-carousel__indicators) {
    bottom: 20px;
  }

  :deep(.el-carousel__button) {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .banner-item {
    height: 100%;
    position: relative;
    overflow: hidden;
    background-size: cover;
    background-position: center;

    // 不同主题色背景
    &.banner--orange { background: linear-gradient(120deg, #1c2438 0%, #3e2820 100%); }
    &.banner--blue   { background: linear-gradient(120deg, #1c2438 0%, #1e3a5f 100%); }
    &.banner--purple { background: linear-gradient(120deg, #1c2438 0%, #382046 100%); }
    &.banner--green  { background: linear-gradient(120deg, #1c2438 0%, #1e4238 100%); }

    .banner-content {
      height: 100%;
      max-width: 1366px; // 保持内容在合理宽度
      margin: 0 auto;
      padding: 0 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: white;
    }

    .banner-text {
      flex: 1;
      z-index: 2;
      padding-left: 36px;

      .banner-tag {
        display: inline-block;
        padding: 2px 8px;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(4px);
        border-radius: 4px;
        font-size: 12px;
        margin-bottom: 8px;
        letter-spacing: 1px;
      }

      .banner-title {
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 8px 0;
        letter-spacing: 1px;
      }

      .banner-desc {
        font-size: 13px;
        line-height: 1.5;
        opacity: 0.8;
        max-width: 600px;
        margin-bottom: 16px;
      }

      .banner-btn {
        padding: 8px 24px;
        font-weight: 600;
      }
    }

    .banner-icon-bg {
      font-size: 180px;
      opacity: 0.1;
      position: absolute;
      right: 100px;
      bottom: -40px;
      transform: rotate(-15deg);
      z-index: 1;
      color: white;
    }
  }
}

/* 任务管理区域 */
.tasks-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  max-width: 1366px; // 缩小最大宽度以适应更小的屏幕
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
  overflow: hidden;

  .task-toolbar {
    flex: 0 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
        margin: 0;
      }

      .search-input {
        width: 240px;
      }
    }

    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 16px;

      .create-btn {
        padding: 8px 20px;
      }
    }
  }

  .task-grid-container {
    flex: 1;
    min-height: 0; // 确保 Grid 在 Flex 中正确滚动
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .task-scrollbar {
      flex: 1;
      min-height: 0;
    }

    :deep(.el-scrollbar) {
      height: 100%;

      .el-scrollbar__view {
        min-height: auto;
      }
    }

    .task-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 12px;
      padding-bottom: 14px;
      padding-right: 10px;
    }

    .task-card {
      background: white;
      border-radius: 10px;
      border: 1px solid #ebeef5;
      padding: 14px;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 10px;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
        border-color: #c6e2ff;
      }

      &.status--running { border-left: 4px solid #409EFF; }
      &.status--completed { border-left: 4px solid #67C23A; }
      &.status--failed { border-left: 4px solid #F56C6C; }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .platform-badge {
            font-size: 11px;
            padding: 2px 7px;
            border-radius: 999px;
            background: #f0f2f5;
            color: #909399;
            font-weight: 600;

            &.vcenter { background: #e1f3d8; color: #67c23a; }
            &.h3c { background: #d9ecff; color: #409eff; }
        }

        .more-icon {
            color: #909399;
            transform: rotate(90deg);
            padding: 3px;
            font-size: 14px;
            &:hover { color: #409eff; background: #ecf5ff; border-radius: 4px; }
        }
      }

      .card-body {
        flex: 1;

        .task-name {
            margin: 0 0 8px 0;
            font-size: 15px;
            font-weight: 600;
            color: #303133;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .task-connection, .task-time {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #606266;
            margin-bottom: 4px;

            .el-icon {
              font-size: 12px;
              color: #909399;
            }
        }

        .connection-host {
          color: #909399;
        }
      }

      .card-footer {
        padding-top: 10px;
        border-top: 1px solid #f2f6fc;

        .status-running {
            .progress-info {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                margin-bottom: 4px;
                color: #606266;

                .status-text {
                  display: inline-flex;
                  align-items: center;
                  gap: 4px;
                }

                .vm-info {
                  color: #909399;
                }
            }

            .progress-val {
                font-weight: bold;
                color: #409eff;
            }
        }

        .status-completed {
            display: flex;
            justify-content: space-between;
            align-items: center;

            .result-stat {
                display: flex;
                align-items: center;
                gap: 10px;

                .stat-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    .label { font-size: 10px; color: #909399; line-height: 1.2; }
                    .val { font-size: 13px; font-weight: 600; color: #303133; line-height: 1.2; }
                }
            }

            .completed-tag {
                font-size: 12px;
                color: #67c23a;
                display: flex;
                align-items: center;
                gap: 4px;
            }
        }

        .status-other {
          :deep(.el-tag) {
            font-size: 11px;
            padding: 0 7px;
            height: 22px;
            line-height: 20px;
          }
        }
      }
    }

    .task-pagination {
      flex: 0 0 auto;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #ebeef5;
      display: flex;
      justify-content: flex-end;
    }
  }
}

.empty-state {
    padding: 60px 0;
    text-align: center;
}
</style>
