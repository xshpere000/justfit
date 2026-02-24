<template>
  <div class="tasks-page">
    <el-card body-style="height: 100%; display: flex; flex-direction: column; overflow: hidden;">
      <template #header>
        <div class="header-row">
          <span>任务中心</span>
          <el-button type="primary" size="small" @click="refreshList">刷新状态</el-button>
        </div>
      </template>

      <div class="task-list-container" v-if="taskStore.tasks.length > 0">
        <el-scrollbar>
          <div class="task-list">
             <div v-for="task in taskStore.tasks" :key="task.id" class="task-item">
                <div class="task-header">
                   <div class="task-title-row">
                     <span class="task-name">{{ task.name }}</span>
                     <el-tag :type="getStatusType(task.status)" size="small">{{ getStatusLabel(task.status) }}</el-tag>
                   </div>
                   <div class="task-actions-top">
                      <el-button link type="danger" size="small" @click="taskStore.deleteTask(task.id)"><el-icon><Delete /></el-icon></el-button>
                   </div>
                </div>
                <div class="task-meta">
                   <span class="meta-item"><el-icon><Monitor /></el-icon> {{ task.platform || '未知' }}</span>
                   <span class="meta-item"><el-icon><Connection /></el-icon> {{ task.connectionName || '-' }}</span>
                   <span class="meta-item"><el-icon><Clock /></el-icon> {{ formatDate(task.created_at) }}</span>
                </div>
                <div class="task-progress" v-if="task.status === 'running'">
                   <div class="progress-label">进度 {{ task.progress }}%</div>
                   <el-progress :percentage="task.progress" :status="task.status === 'failed' ? 'exception' : ''" :stroke-width="8" striped striped-flow />
                </div>
                <div class="error-msg" v-if="task.error">
                   <el-alert :title="task.error" type="error" :closable="false" show-icon />
                </div>
             </div>
          </div>
        </el-scrollbar>
      </div>

      <el-empty v-else description="暂无任务记录" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useTaskStore } from '@/stores/task'
import { Monitor, Connection, Clock, Delete } from '@element-plus/icons-vue'

const taskStore = useTaskStore()

// 初始化时从后端同步任务
taskStore.syncTasksFromBackend()

function refreshList() {
  taskStore.syncTasksFromBackend()
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getStatusType(status: string) {
  switch(status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    case 'cancelled': return 'info'
    default: return 'warning'
  }
}

function getStatusLabel(status: string) {
    const map: Record<string, string> = {
        'pending': '等待中',
        'running': '进行中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消',
        'paused': '暂停'
    }
    return map[status] || status
}
</script>

<style scoped lang="scss">
.tasks-page {
  height: 100%;
  padding: 20px;
  overflow: hidden;
  box-sizing: border-box;

  :deep(.el-card) {
    height: 100%;
    display: flex;
    flex-direction: column;
    border: none;

    .el-card__header {
        padding: 16px 20px;
        border-bottom: 1px solid #f0f2f5;
    }
    .el-card__body {
        padding: 0;
    }
  }

  .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 600;
  }

  .task-list-container {
    flex: 1;
    overflow: hidden;
    height: 100%;
    background: #f5f7fa;
    padding: 20px;
  }

  .task-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-width: 1000px;
      margin: 0 auto;
  }

  .task-item {
      padding: 20px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      transition: all 0.3s;
      border-left: 4px solid transparent;

      &:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.08);
          transform: translateY(-1px);
      }
  }

  .task-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
  }

  .task-title-row {
      display: flex;
      align-items: center;
      gap: 12px;

      .task-name {
          font-weight: 600;
          font-size: 16px;
          color: #303133;
      }
  }

  .task-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 24px;
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px dashed #ebeef5;

      .meta-item {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #606266;
          font-size: 13px;

          .el-icon { font-size: 14px; color: #909399; }
      }
  }

  .task-progress {
      background: #f9fafc;
      padding: 12px;
      border-radius: 4px;

      .progress-label {
          font-size: 12px;
          color: #606266;
          margin-bottom: 6px;
          display: flex;
          justify-content: space-between;
      }
  }

  .error-msg {
      margin-top: 12px;
  }
}
</style>
