<template>
  <div class="tidal-analysis-page">
    <!-- 配置面板 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>潮汐检测配置</span>
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
                :min="14"
                :max="90"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最小稳定性">
              <el-slider
                v-model="config.minStability"
                :min="0"
                :max="1"
                :step="0.1"
                :show-tooltip="false"
              />
              <span class="form-tip">{{ (config.minStability * 100).toFixed(0) }}%</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 结果汇总 -->
    <el-row v-if="results.length > 0" :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic title="发现潮汐模式" :value="results.length" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic
            title="日周期模式"
            :value="dailyPatternCount"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic
            title="周周期模式"
            :value="weeklyPatternCount"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <el-statistic
            title="平均稳定性"
            :value="averageStability"
            suffix="%"
            :precision="1"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 结果列表 -->
    <el-card v-if="results.length > 0" class="results-card">
      <template #header>
        <span>检测详情</span>
      </template>

      <el-table :data="results" stripe max-height="500">
        <el-table-column prop="vmName" label="虚拟机名称" min-width="180" />
        <el-table-column prop="datacenter" label="数据中心" width="150" />
        <el-table-column prop="pattern" label="周期模式" width="120">
          <template #default="{ row }">
            <el-tag :type="row.pattern === 'daily' ? 'primary' : 'success'">
              {{ row.pattern === 'daily' ? '日周期' : '周周期' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stabilityScore" label="稳定性" width="120">
          <template #default="{ row }">
            <el-progress
              :percentage="row.stabilityScore"
              :color="getStabilityColor(row.stabilityScore)"
              :show-text="false"
            />
            <span class="progress-text">{{ row.stabilityScore.toFixed(0) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="高峰时段" width="180">
          <template #default="{ row }">
            <div v-if="row.pattern === 'daily'">
              <el-tag
                v-for="hour in row.peakHours.slice(0, 3)"
                :key="hour"
                size="small"
                style="margin-right: 4px"
              >
                {{ hour }}:00
              </el-tag>
            </div>
            <div v-else>
              <el-tag
                v-for="day in row.peakDays.slice(0, 3)"
                :key="day"
                size="small"
                style="margin-right: 4px"
              >
                {{ ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][day - 1] }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="recommendation" label="建议操作" min-width="200" />
        <el-table-column prop="estimatedSaving" label="预计节省" width="120" />
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-card v-else-if="!analyzing && analyzed" class="empty-card">
      <el-empty description="未检测到潮汐模式">
        <template #image>
          <el-icon :size="80" color="#909399">
            <CircleCheck />
          </el-icon>
        </template>
        <p class="empty-tip">当前虚拟机未呈现明显的潮汐负载模式</p>
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
import type { TidalConfig, TidalResult } from '@/api/connection'

const connectionStore = useConnectionStore()

const config = reactive<TidalConfig>({
  connectionId: undefined,
  analysisDays: 30,
  minStability: 0.7
})

const analyzing = ref(false)
const analyzed = ref(false)
const results = ref<TidalResult[]>([])

const canAnalyze = computed(() => {
  return config.connectionId && config.connectionId > 0 && !analyzing.value
})

const dailyPatternCount = computed(() => {
  return results.value.filter(r => r.pattern === 'daily').length
})

const weeklyPatternCount = computed(() => {
  return results.value.filter(r => r.pattern === 'weekly').length
})

const averageStability = computed(() => {
  if (results.value.length === 0) return 0
  return (
    results.value.reduce((sum, r) => sum + r.stabilityScore, 0) /
    results.value.length
  )
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
    const data = await AnalysisAPI.detectTidalPattern(config.connectionId, config)
    results.value = data
    analyzed.value = true

    if (data.length > 0) {
      ElMessage.success('检测完成，发现 ' + data.length + ' 个潮汐模式虚拟机')
    } else {
      ElMessage.info('未检测到潮汐模式')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '检测失败')
  } finally {
    analyzing.value = false
  }
}

function getStabilityColor(score: number): string {
  if (score >= 80) return '#67C23A'
  if (score >= 60) return '#409EFF'
  return '#E6A23C'
}
</script>

<style scoped lang="scss">
.tidal-analysis-page {
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

  .empty-card {
    .empty-tip {
      margin-top: var(--spacing-lg);
      color: var(--text-color-secondary);
    }
  }
}
</style>
