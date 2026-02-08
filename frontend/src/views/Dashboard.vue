<template>
  <div class="dashboard-page">
    <!-- KPI 卡片 -->
    <el-row :gutter="20" class="kpi-row">
      <el-col :span="6">
        <el-card class="kpi-card kpi-card--health">
          <div class="kpi-icon">
            <el-icon :size="32"><TrendCharts /></el-icon>
          </div>
          <div class="kpi-content">
            <div class="kpi-value">{{ healthScore }}</div>
            <div class="kpi-label">健康评分</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card kpi-card--warning">
          <div class="kpi-icon">
            <el-icon :size="32"><Monitor /></el-icon>
          </div>
          <div class="kpi-content">
            <div class="kpi-value">{{ zombieCount }}</div>
            <div class="kpi-label">僵尸 VM</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card kpi-card--success">
          <div class="kpi-icon">
            <el-icon :size="32"><Coin /></el-icon>
          </div>
          <div class="kpi-content">
            <div class="kpi-value">{{ savings }}%</div>
            <div class="kpi-label">可节省资源</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card kpi-card--info">
          <div class="kpi-icon">
            <el-icon :size="32"><DataAnalysis /></el-icon>
          </div>
          <div class="kpi-content">
            <div class="kpi-value">{{ totalVMs }}</div>
            <div class="kpi-label">虚拟机总数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 连接状态 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>平台连接</span>
          <el-button type="primary" link @click="goToConnections">
            管理连接
          </el-button>
        </div>
      </template>

      <el-table :data="connectionStore.connections" size="small" stripe>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="platform" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">
              {{ PLATFORM_LABELS[row.platform] || row.platform }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机地址" min-width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="getConnectionStatusType(row.status)"
              size="small"
            >
              {{ getConnectionStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync" label="最后连接" width="160">
          <template #default="{ row }">
            {{ row.last_sync ? formatDateTime(row.last_sync) : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="connectionStore.connections.length === 0"
        description="暂无连接"
        :image-size="80"
      />
    </el-card>

    <!-- 快捷操作 -->
    <el-card class="section-card">
      <template #header>
        <span>快捷操作</span>
      </template>

      <el-row :gutter="16">
        <el-col :span="6">
          <div class="action-card" @click="goToConnections">
            <el-icon class="action-icon"><Connection /></el-icon>
            <span class="action-label">添加连接</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="action-card" @click="goToCollection">
            <el-icon class="action-icon"><Download /></el-icon>
            <span class="action-label">数据采集</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="action-card" @click="goToAnalysis('zombie')">
            <el-icon class="action-icon"><Monitor /></el-icon>
            <span class="action-label">僵尸 VM 检测</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="action-card" @click="goToAnalysis('health')">
            <el-icon class="action-icon"><DataAnalysis /></el-icon>
            <span class="action-label">健康评分</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConnectionStore } from '@/stores/connection'
import { PLATFORM_LABELS } from '@/utils/constants'
import {
  formatDateTime,
  getConnectionStatusType,
  getConnectionStatusText
} from '@/utils/format'
import {
  TrendCharts,
  Monitor,
  Coin,
  DataAnalysis,
  Connection,
  Download
} from '@element-plus/icons-vue'

// @ts-ignore
import { GetDashboardStats } from '../../wailsjs/go/main/App'

const router = useRouter()
const connectionStore = useConnectionStore()

// KPI 数据
const healthScore = ref(0)
const zombieCount = ref(0)
const savings = ref('¥0')
const totalVMs = ref(0)

onMounted(async () => {
  await connectionStore.fetchConnections()
  loadStats()
})

async function loadStats() {
    try {
        const stats = await GetDashboardStats()
        healthScore.value = stats.health_score || 0
        zombieCount.value = stats.zombie_count || 0
        savings.value = stats.total_savings || '¥0'
        totalVMs.value = stats.total_vms || 0
    } catch (e) {
        console.error("Failed to load dashboard stats", e)
    }
}

function goToConnections() {
  router.push('/connections')
}

function goToCollection() {
  router.push('/collection')
}

function goToAnalysis(type: string) {
  router.push(`/analysis/${type}`)
}
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;

  .kpi-row {
    .kpi-card {
      display: flex;
      align-items: center;
      gap: $spacing-md;
      padding: $spacing-lg;

      .kpi-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 60px;
        height: 60px;
        border-radius: $border-radius-large;
        background: rgba(64, 158, 255, 0.1);
        color: $primary-color;
      }

      .kpi-card--health .kpi-icon {
        background: rgba($success-color, 0.1);
        color: $success-color;
      }

      .kpi-card--warning .kpi-icon {
        background: rgba($warning-color, 0.1);
        color: $warning-color;
      }

      .kpi-card--success .kpi-icon {
        background: rgba($primary-color, 0.1);
        color: $primary-color;
      }

      .kpi-card--info .kpi-icon {
        background: rgba($info-color, 0.1);
        color: $info-color;
      }

      .kpi-content {
        flex: 1;

        .kpi-value {
          font-size: 28px;
          font-weight: 600;
          line-height: 1.2;
        }

        .kpi-label {
          font-size: $font-size-small;
          color: $text-color-secondary;
        }
      }
    }
  }

  .section-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .action-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-lg;
    background: #fff;
    border: 1px solid $border-color-light;
    border-radius: $border-radius-base;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      border-color: $primary-color;
      box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
      transform: translateY(-2px);

      .action-icon {
        color: $primary-color;
      }
    }

    .action-icon {
      font-size: 32px;
      color: $text-color-secondary;
      transition: color 0.3s;
    }

    .action-label {
      font-size: $font-size-base;
      color: $text-color-regular;
    }
  }
}
</style>
