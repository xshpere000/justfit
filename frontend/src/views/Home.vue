<template>
  <div class="home-page">
    <!-- 顶部 Banner 轮播 -->
    <HomeBanner @start-task="startNewTask" />

    <!-- 任务管理区域 -->
    <div class="tasks-section">
      <!-- 工具栏 -->
      <div class="task-toolbar">
        <div class="toolbar-left">
          <h2 class="section-title">任务管理</h2>
          <el-input
            v-model="searchQuery"
            placeholder="搜索任务名称或连接..."
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <div class="toolbar-right">
          <el-segmented v-model="filterStatus" :options="statusOptions" class="status-filter" />
          <el-button type="primary" class="create-btn" @click="startNewTask">
            <el-icon><Plus /></el-icon>
            <span>新建任务</span>
          </el-button>
        </div>
      </div>

      <!-- 任务网格 -->
      <div class="task-grid-container">
        <template v-if="filteredTasks.length > 0">
          <el-scrollbar class="task-scrollbar">
            <div class="task-grid">
              <TaskCard
                v-for="task in pagedTasks"
                :key="task.id"
                :task="task"
                @click="openTask"
                @command="handleTaskCommand"
              />
            </div>
          </el-scrollbar>

          <!-- 分页 -->
          <div v-if="totalPages > 1" class="task-pagination">
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
          <el-empty :description="emptyDescription" :image-size="120">
            <el-button v-if="taskStore.tasks.length === 0" type="primary" @click="startNewTask">
              创建第一个任务
            </el-button>
          </el-empty>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { retryTask } from '@/api/task'
import type { Task, TaskStatus } from '@/api/task'
import HomeBanner from '@/components/HomeBanner.vue'
import TaskCard from '@/components/TaskCard.vue'

const router = useRouter()
const taskStore = useTaskStore()

// 状态筛选选项
const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'running' },
  { label: '已完成', value: 'completed' }
]

// 查询和筛选状态
const searchQuery = ref('')
const filterStatus = ref<string>('all')
const currentPage = ref(1)
const pageSize = ref(8)

// 计算总页数
const totalPages = computed(() => Math.ceil(filteredTasks.value.length / pageSize.value))

// 初始化
onMounted(() => {
  console.log('[Home.vue] 首页挂载，启动轮询')
  taskStore.startPolling()
})

// 组件卸载前停止轮询（避免与 TaskDetail 的轮询冲突）
onBeforeUnmount(() => {
  console.log('[Home.vue] onBeforeUnmount: 停止轮询')
  taskStore.stopPolling()
})

// 组件卸载时的额外清理
onUnmounted(() => {
  console.log('[Home.vue] 首页卸载')
})

// 监听任务列表变化
watch(
  () => taskStore.tasks,
  (newTasks) => {
    console.log('[Home.vue] 任务列表更新，数量:', newTasks.length)
  },
  { deep: true }
)

// 筛选后的任务列表
const filteredTasks = computed(() => {
  let result = taskStore.tasks

  // 状态筛选
  if (filterStatus.value === 'running') {
    result = result.filter((t) => ['running', 'pending'].includes(t.status))
  } else if (filterStatus.value === 'completed') {
    result = result.filter((t) => t.status === 'completed')
  }

  // 搜索筛选
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter((t) => {
      const nameMatch = t.name.toLowerCase().includes(q)
      const hostMatch = t.connectionHost?.toLowerCase().includes(q)
      const connMatch = t.connectionName?.toLowerCase().includes(q)
      return nameMatch || hostMatch || connMatch
    })
  }

  // 按创建时间排序（最新的在前）
  return [...result].sort(
    (a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime()
  )
})

// 分页后的任务列表
const pagedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredTasks.value.slice(start, end)
})

// 空状态描述
const emptyDescription = computed(() => {
  if (taskStore.tasks.length === 0) {
    return '暂无任务，创建一个新任务开始吧'
  }
  if (filteredTasks.value.length === 0) {
    return '没有找到符合条件的任务'
  }
  return '暂无任务'
})

// 搜索或筛选变化时重置页码
watch([searchQuery, filterStatus], () => {
  currentPage.value = 1
})

// 确保页码不超过最大值
watch(filteredTasks, (list) => {
  const maxPage = Math.max(1, Math.ceil(list.length / pageSize.value))
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage
  }
})

// 创建新任务
function startNewTask() {
  if (taskStore.hasRunningTasks) {
    ElMessageBox.confirm(
      '当前有正在运行的任务，是否继续创建新任务？这可能会影响性能。',
      '提示',
      { type: 'warning', confirmButtonText: '继续', cancelButtonText: '取消' }
    )
      .then(() => router.push('/wizard'))
      .catch(() => {})
  } else {
    router.push('/wizard')
  }
}

// 打开任务详情
function openTask(task: Task) {
  router.push('/task/' + task.id)
}

// 处理任务操作命令
async function handleTaskCommand(command: string, task: Task) {
  switch (command) {
    case 'cancel':
      await handleCancelTask(task)
      break

    case 'retry':
      await handleRetryTask(task)
      break

    case 'delete':
      await handleDeleteTask(task)
      break
  }
}

// 取消任务
async function handleCancelTask(task: Task) {
  try {
    await ElMessageBox.confirm('确定要取消该任务吗？取消后无法恢复。', '取消任务', {
      type: 'warning',
      confirmButtonText: '确定取消',
      cancelButtonText: '再想想'
    })
    await taskStore.cancelTask(task.id)
    ElMessage.success('任务已取消')
  } catch {
    // 用户取消
  }
}

// 重试任务
async function handleRetryTask(task: Task) {
  try {
    await ElMessageBox.confirm(
      '将使用相同配置创建一个新任务，是否继续？',
      '重试任务',
      {
        type: 'info',
        confirmButtonText: '确定重试',
        cancelButtonText: '取消'
      }
    )
    const newTaskId = await retryTask(task.id)
    ElMessage.success('已创建重试任务，即将跳转...')
    // 等待一下后跳转到新任务详情
    setTimeout(() => {
      router.push('/task/' + newTaskId)
    }, 500)
  } catch (error: unknown) {
    if (error !== 'cancel') {
      ElMessage.error(error instanceof Error ? error.message : '重试任务失败')
    }
  }
}

// 删除任务
async function handleDeleteTask(task: Task) {
  try {
    await ElMessageBox.confirm(
      '确定要删除该任务记录吗？此操作不可恢复。',
      '删除任务',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true
      }
    )
    await taskStore.deleteTask(task.id)
    ElMessage.success('任务已删除')
  } catch {
    // 用户取消
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

.tasks-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  max-width: 1440px;
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
    gap: 20px;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 16px;
      flex: 1;
      min-width: 0;

      .section-title {
        font-size: 20px;
        font-weight: 600;
        color: #303133;
        margin: 0;
        white-space: nowrap;
      }

      .search-input {
        width: 200px;

        :deep(.el-input__wrapper) {
          border-radius: 8px;
        }
      }
    }

    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-shrink: 0;

      .status-filter {
        :deep(.el-segmented) {
          --el-segmented-bg-color: #f5f7fa;
          --el-border-radius-base: 8px;
          padding: 2px;
        }

        :deep(.el-segmented__item) {
          border-radius: 6px;
        }
      }

      .create-btn {
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 500;

        span {
          margin-left: 4px;
        }
      }
    }
  }

  .task-grid-container {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: white;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);

    .task-scrollbar {
      flex: 1;
      min-height: 0;
    }

    :deep(.el-scrollbar) {
      height: 100%;
      padding-right: 4px;

      .el-scrollbar__view {
        min-height: auto;
      }
    }

    .task-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
      padding: 20px;
    }

    .task-pagination {
      flex: 0 0 auto;
      padding: 12px 20px;
      border-top: 1px solid #ebeef5;
      display: flex;
      justify-content: center;
      background: #fafbfc;
      border-radius: 0 0 12px 12px;

      :deep(.el-pagination) {
        .btn-prev,
        .btn-next,
        .el-pager li {
          border-radius: 6px;
          min-width: 32px;
          height: 32px;
          line-height: 30px;
        }

        .el-pager li.is-active {
          background: var(--el-color-primary);
        }
      }
    }
  }
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;

  :deep(.el-empty) {
    padding: 40px 0;
  }
}

// 响应式适配
@media (max-width: 1023px) {
  .tasks-section {
    padding: 16px;

    .task-toolbar {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;

      .toolbar-left {
        .search-input {
          width: 100%;
        }
      }

      .toolbar-right {
        justify-content: space-between;

        .status-filter {
          flex: 1;
        }

        .create-btn {
          flex: 0 0 auto;
        }
      }
    }

    .task-grid-container .task-grid {
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 12px;
      padding: 16px;
    }
  }
}

@media (max-width: 640px) {
  .tasks-section {
    padding: 12px;

    .task-grid-container .task-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>
