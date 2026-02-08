<template>
  <div class="zombie-analysis-page">
    <!-- 配置面板 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>检测配置</span>
          <el-button
            type="primary"
            :icon="'Search'"
            :loading="analyzing"
            :disabled="!canAnalyze"
            @click="handleAnalyze"
          >
            {{ analyzing ? '分析中...' : '开始检测' }}
          </el-button>
        </div>
      </template>

      <el-form :model="config" label-width="140px" label-position="left">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="选择连接">
              <el-select
                v-model="config.connection_id"
                placeholder="请选择连接"
                style="width: 100%"
              >
                <el-option
                  v-for="conn in connectionStore.activeConnections"
                  :key="conn.id"
                  :label="conn.name"
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="分析天数">
              <el-input-number
                v-model="config.analysis_days"
                :min="7"
                :max="90"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最小置信度">
              <el-slider
                v-model="config.min_confidence"
                :min="0"
                :max="1"
                :step="0.1"
                :show-tooltip="false"
              />
              <span class="form-tip">{{ (config.min_confidence * 100).toFixed(0) }}%</span>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="CPU 阈值 (%)">
              <el-input-number
                v-model="config.cpu_threshold"
                :min="0"
                :max="100"
                :step="1"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="内存阈值 (%)">
              <el-input-number
                v-model="config.memory_threshold"
                :min="0"
                :max="100"
                :step="1"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 结果汇总 -->
    <el-card v-if="results.length > 0" class="summary-card">
      <template #header>
        <span>检测结果汇总</span>
      </template>

      <el-row :gutter="20" class="summary-stats">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ results.length }}</div>
            <div class="stat-label">僵尸 VM 数量</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">
              {{ formatNumber(totalWastedCPU) }}
            </div>
            <div class="stat-label">浪费 CPU 核数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">
              {{ formatMemory(totalWastedMemory) }}
            </div>
            <div class="stat-label">浪费内存</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">
              {{ averageConfidence.toFixed(1) }}%
            </div>
            <div class="stat-label">平均置信度</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 结果列表 -->
    <el-card v-if="results.length > 0" class="results-card">
      <template #header>
        <div class="card-header">
          <span>检测结果详情</span>
          <el-button :icon="'Download'" @click="handleExport">
            导出结果
          </el-button>
        </div>
      </template>

      <el-table :data="results" stripe max-height="500">
        <el-table-column prop="vm_name" label="虚拟机名称" min-width="180" />
        <el-table-column prop="datacenter" label="数据中心" width="150" />
        <el-table-column prop="host" label="主机" width="150" />
        <el-table-column prop="cpu_count" label="CPU(核)" width="80" />
        <el-table-column prop="memory_mb" label="内存(MB)" width="100" />
        <el-table-column label="CPU 使用率" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="row.cpu_usage"
              :color="'#67C23A'"
              :show-text="false"
            />
            <span class="progress-text">{{ row.cpu_usage.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="内存使用率" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="row.memory_usage"
              :color="'#67C23A'"
              :show-text="false"
            />
            <span class="progress-text">{{ row.memory_usage.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <el-tag :type="getConfidenceType(row.confidence)">
              {{ (row.confidence * 100).toFixed(0) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="days_low_usage" label="低载天数" width="100" />
        <el-table-column label="建议操作" min-width="150">
          <template #default="{ row }">
            {{ row.recommendation }}
          </template>
        </el-table-column>
        <el-table-column type="expand" label="证据" width="60">
          <template #default="{ row }">
            <div class="evidence-content">
              <h4>检测证据:</h4>
              <ul>
                <li v-for="(item, index) in row.evidence" :key="index">
                  {{ item }}
                </li>
              </ul>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-card v-else-if="!analyzing && analyzed" class="empty-card">
      <el-empty description="未检测到僵尸虚拟机">
        <template #image>
          <el-icon :size="80" color="#909399">
            <CircleCheck />
          </el-icon>
        </template>
        <p class="empty-tip">当前配置下未发现僵尸虚拟机，或所有虚拟机都处于正常使用状态</p>
      </el-empty>
    </el-card>

    <!-- 提示状态 -->
    <el-card v-else class="empty-card">
      <el-empty description="请配置检测参数并开始分析">
        <template #image>
          <el-icon :size="80" color="#C0C4CC">
            <Monitor />
          </el-icon>
        </template>
        <p class="empty-tip">选择一个已连接的平台，配置检测参数后点击"开始检测"</p>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, CircleCheck } from '@element-plus/icons-vue'
import { useConnectionStore } from '@/stores/connection'
import { detectZombieVMs } from '@/api/analysis'
import type { ZombieVMConfig, ZombieVMResult } from '@/api/types'
import { formatMemory, formatNumber } from '@/utils/format'

const connectionStore = useConnectionStore()

const config = reactive<ZombieVMConfig>({
  analysis_days: 14,
  cpu_threshold: 5,
  memory_threshold: 10,
  min_confidence: 0.7
})

const analyzing = ref(false)
const analyzed = ref(false)
const results = ref<ZombieVMResult[]>([])

const canAnalyze = computed(() => {
  return config.connection_id && config.connection_id > 0 && !analyzing.value
})

const totalWastedCPU = computed(() => {
  return results.value.reduce((sum, r) => sum + r.cpu_count, 0)
})

const totalWastedMemory = computed(() => {
  return results.value.reduce((sum, r) => sum + r.memory_mb, 0)
})

const averageConfidence = computed(() => {
  if (results.value.length === 0) return 0
  return (
    (results.value.reduce((sum, r) => sum + r.confidence, 0) /
      results.value.length) *
    100
  )
})

async function handleAnalyze() {
  if (!config.connection_id) {
    ElMessage.warning('请选择连接')
    return
  }

  analyzing.value = true
  analyzed.value = false
  results.value = []

  try {
    const data = await detectZombieVMs(config.connection_id, config)
    results.value = data
    analyzed.value = true

    if (data.length > 0) {
      ElMessage.success(`检测完成，发现 ${data.length} 个僵尸虚拟机`)
    } else {
      ElMessage.info('未检测到僵尸虚拟机')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '检测失败')
  } finally {
    analyzing.value = false
  }
}

function getConfidenceType(confidence: number): string {
  if (confidence >= 0.8) return 'danger'
  if (confidence >= 0.6) return 'warning'
  return 'info'
}

function handleExport() {
  const data = JSON.stringify(results.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `zombie-vm-analysis-${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}
</script>

<style scoped lang="scss">
.zombie-analysis-page {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;

  .form-tip {
    font-size: $font-size-small;
    color: $text-color-secondary;
    margin-left: $spacing-sm;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .summary-card {
    .summary-stats {
      .stat-item {
        text-align: center;
        padding: $spacing-md;
        background: $background-color-base;
        border-radius: $border-radius-base;

        .stat-value {
          font-size: 24px;
          font-weight: 600;
          color: $primary-color;
          margin-bottom: $spacing-sm;
        }

        .stat-label {
          font-size: $font-size-small;
          color: $text-color-secondary;
        }
      }
    }
  }

  .progress-text {
    font-size: $font-size-small;
    margin-left: $spacing-sm;
  }

  .evidence-content {
    padding: $spacing-lg;

    h4 {
      margin: 0 0 $spacing-sm;
      font-size: $font-size-base;
    }

    ul {
      margin: 0;
      padding-left: $spacing-lg;

      li {
        margin-bottom: $spacing-xs;
        color: $text-color-regular;
      }
    }
  }

  .empty-card {
    .empty-tip {
      margin-top: $spacing-lg;
      color: $text-color-secondary;
    }
  }
}
</style>
