<template>
  <div class="rightsize-analysis-page">
    <!-- 配置面板 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>分析配置</span>
          <el-button
            type="primary"
            :icon="'Search'"
            :loading="analyzing"
            :disabled="!canAnalyze"
            @click="handleAnalyze"
          >
            {{ analyzing ? '分析中...' : '开始分析' }}
          </el-button>
        </div>
      </template>

      <el-form :model="config" label-width="140px" label-position="left">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="选择连接">
              <el-select
                v-model="config.connectionId"
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
                v-model="config.analysisDays"
                :min="7"
                :max="90"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="缓冲比例">
              <el-slider
                v-model="config.bufferRatio"
                :min="1.0"
                :max="2.0"
                :step="0.1"
                :show-tooltip="false"
              />
              <span class="form-tip">{{ config.bufferRatio.toFixed(1) }}x</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 结果汇总 -->
    <el-row v-if="results.length > 0" :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic title="需要调整的VM" :value="results.length" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic
            title="可节省 CPU"
            :value="totalSavedCPU"
            suffix="核"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic
            title="可节省内存"
            :value="totalSavedMemoryMB"
            suffix="MB"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic
            title="平均置信度"
            :value="averageConfidence"
            suffix="%"
            :precision="1"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 结果列表 -->
    <el-card v-if="results.length > 0" class="results-card">
      <template #header>
        <div class="card-header">
          <span>分析结果详情</span>
          <el-button :icon="'Download'" @click="handleExport">
            导出结果
          </el-button>
        </div>
      </template>

      <el-table :data="results" stripe max-height="500">
        <el-table-column prop="vmName" label="虚拟机名称" min-width="180" />
        <el-table-column prop="datacenter" label="数据中心" width="120" />
        <el-table-column label="当前配置" width="150">
          <template #default="{ row }">
            <div>{{ row.currentCpu }}核 / {{ row.currentMemoryMb }}MB</div>
          </template>
        </el-table-column>
        <el-table-column label="推荐配置" width="150">
          <template #default="{ row }">
            <div class="recommended">
              <span class="cpu-value">{{ row.recommendedCpu }}核</span>
              /
              <span class="mem-value">{{ row.recommendedMemoryMb }}MB</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="adjustmentType" label="调整类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getAdjustmentType(row.adjustmentType)">
              {{ getAdjustmentText(row.adjustmentType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="riskLevel" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskLevelType(row.riskLevel)">
              {{ row.riskLevel }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="estimatedSaving" label="预计节省" width="120" />
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="row.confidence"
              :color="'#409EFF'"
              :show-text="false"
            />
            <span class="progress-text">{{ row.confidence.toFixed(0) }}%</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-card v-else-if="!analyzing && analyzed" class="empty-card">
      <el-empty description="未发现需要调整的虚拟机">
        <template #image>
          <el-icon :size="80" color="#909399">
            <CircleCheck />
          </el-icon>
        </template>
        <p class="empty-tip">当前配置合理，未发现需要调整的虚拟机</p>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck } from '@element-plus/icons-vue'
import { useConnectionStore } from '@/stores/connection'
import * as AnalysisAPI from '@/api/connection'
import type { RightSizeConfig, RightSizeResult } from '@/api/connection'
import { getRiskLevelType } from '@/utils/format'

const connectionStore = useConnectionStore()

const config = reactive<RightSizeConfig>({
  connectionId: undefined,
  analysisDays: 30,
  bufferRatio: 1.2
})

const analyzing = ref(false)
const analyzed = ref(false)
const results = ref<RightSizeResult[]>([])

const canAnalyze = computed(() => {
  return config.connectionId && config.connectionId > 0 && !analyzing.value
})

const totalSavedCPU = computed(() => {
  return results.value.reduce((sum, r) => {
    return sum + (r.currentCpu - r.recommendedCpu)
  }, 0)
})

const totalSavedMemoryMB = computed(() => {
  return results.value.reduce((sum, r) => {
    return sum + (r.currentMemoryMb - r.recommendedMemoryMb)
  }, 0)
})

const averageConfidence = computed(() => {
  if (results.value.length === 0) return 0
  return (
    results.value.reduce((sum, r) => sum + r.confidence, 0) / results.value.length
  ) * 100
})

async function handleAnalyze() {
  if (!config.connectionId) {
    ElMessage.warning('请选择连接')
    return
  }

  analyzing.value = true
  analyzed.value = false
  results.value = []

  try {
    const data = await AnalysisAPI.analyzeRightSize(config.connectionId, config)
    results.value = data
    analyzed.value = true

    if (data.length > 0) {
      ElMessage.success('分析完成，发现 ' + data.length + ' 个需要调整的虚拟机')
    } else {
      ElMessage.info('未发现需要调整的虚拟机')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    analyzing.value = false
  }
}

function getAdjustmentType(type: string): string {
  if (type === 'downsize') return 'success'
  if (type === 'upsize') return 'warning'
  return 'info'
}

function getAdjustmentText(type: string): string {
  if (type === 'downsize') return '缩小配置'
  if (type === 'upsize') return '扩大配置'
  return '配置合理'
}

function handleExport() {
  const data = JSON.stringify(results.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'rightsize-analysis-' + Date.now() + '.json'
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}
</script>

<style scoped lang="scss">
.rightsize-analysis-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);

  .form-tip {
    font-size: var(--font-size-small);
    color: var(--text-color-secondary);
    margin-left: var(--spacing-sm);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .summary-row {
    .summary-card {
      text-align: center;
    }
  }

  .progress-text {
    font-size: var(--font-size-small);
    margin-left: var(--spacing-sm);
  }

  .recommended {
    .cpu-value {
      color: var(--success-color);
      font-weight: 600;
    }

    .mem-value {
      color: var(--primary-color);
      font-weight: 600;
    }
  }

  .empty-card {
    .empty-tip {
      margin-top: var(--spacing-lg);
      color: var(--text-color-secondary);
    }
  }
}
</style>
