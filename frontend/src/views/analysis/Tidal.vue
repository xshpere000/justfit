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
                :min="14"
                :max="90"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最小稳定性">
              <el-slider
                v-model="config.min_stability"
                :min="0"
                :max="1"
                :step="0.1"
                :show-tooltip="false"
              />
              <span class="form-tip">{{ (config.min_stability * 100).toFixed(0) }}%</span>
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
        <el-table-column prop="vm_name" label="虚拟机名称" min-width="180" />
        <el-table-column prop="datacenter" label="数据中心" width="150" />
        <el-table-column prop="pattern" label="周期模式" width="120">
          <template #default="{ row }">
            <el-tag :type="row.pattern === 'daily' ? 'primary' : 'success'">
              {{ row.pattern === 'daily' ? '日周期' : '周周期' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stability_score" label="稳定性" width="120">
          <template #default="{ row }">
            <el-progress
              :percentage="row.stability_score * 100"
              :color="getStabilityColor(row.stability_score)"
              :show-text="false"
            />
            <span class="progress-text">{{ (row.stability_score * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="高峰时段" width="180">
          <template #default="{ row }">
            <div v-if="row.pattern === 'daily'">
              <el-tag
                v-for="hour in row.peak_hours.slice(0, 3)"
                :key="hour"
                size="small"
                style="margin-right: 4px"
              >
                {{ hour }}:00
              </el-tag>
            </div>
            <div v-else>
              <el-tag
                v-for="day in row.peak_days.slice(0, 3)"
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
        <el-table-column prop="estimated_saving" label="预计节省" width="120" />
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
import { detectTidalPattern } from '@/api/analysis'
import type { TidalConfig, TidalResult } from '@/api/types'

const connectionStore = useConnectionStore()

const config = reactive<TidalConfig>({
  analysis_days: 30,
  min_stability: 0.7
})

const analyzing = ref(false)
const analyzed = ref(false)
const results = ref<TidalResult[]>([])

const canAnalyze = computed(() => {
  return config.connection_id && config.connection_id > 0 && !analyzing.value
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
    results.value.reduce((sum, r) => sum + r.stability_score, 0) /
    results.value.length
  ) * 100
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
    const data = await detectTidalPattern(config.connection_id, config)
    results.value = data
    analyzed.value = true

    if (data.length > 0) {
      ElMessage.success(`检测完成，发现 ${data.length} 个潮汐模式虚拟机`)
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
  if (score >= 0.8) return '#67C23A'
  if (score >= 0.6) return '#409EFF'
  return '#E6A23C'
}
</script>

<style scoped lang="scss">
.tidal-analysis-page {
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

  .summary-row {
    .summary-card {
      text-align: center;
    }
  }

  .progress-text {
    font-size: $font-size-small;
    margin-left: $spacing-sm;
  }

  .empty-card {
    .empty-tip {
      margin-top: $spacing-lg;
      color: $text-color-secondary;
    }
  }
}
</style>
