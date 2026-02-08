<template>
  <div class="health-analysis-page">
    <!-- 配置面板 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>平台健康度分析</span>
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

      <el-form label-width="140px" label-position="left">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="选择连接">
              <el-select
                v-model="selectedConnectionId"
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
        </el-row>
      </el-form>
    </el-card>

    <!-- 健康评分结果 -->
    <div v-if="result" class="health-result">
      <!-- 评分卡片 -->
      <el-row :gutter="20" class="score-row">
        <el-col :span="8">
          <el-card class="score-card-main">
            <div class="score-circle">
              <el-progress
                type="circle"
                :percentage="result.overall_score"
                :color="getHealthColor(result.overall_score)"
                :width="140"
              >
                <template #default="{ percentage }">
                  <span class="score-value">{{ percentage }}</span>
                  <span class="score-label">分</span>
                </template>
              </el-progress>
            </div>
            <div class="health-level">
              <el-tag :type="getHealthLevelType(result.health_level)" size="large">
                {{ getHealthLevelText(result.health_level) }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card class="metrics-card">
            <template #header>
              <span>详细指标</span>
            </template>
            <el-row :gutter="16">
              <el-col :span="8">
                <div class="metric-item">
                  <span class="metric-label">资源均衡度</span>
                  <el-progress
                    :percentage="result.resource_balance * 100"
                    :color="'#409EFF'"
                    :show-text="false"
                  />
                  <span class="metric-value">{{ (result.resource_balance * 100).toFixed(0) }}%</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric-item">
                  <span class="metric-label">超配风险</span>
                  <el-progress
                    :percentage="result.overcommit_risk * 100"
                    :color="getRiskColor(result.overcommit_risk)"
                    :show-text="false"
                  />
                  <span class="metric-value">{{ (result.overcommit_risk * 100).toFixed(0) }}%</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric-item">
                  <span class="metric-label">热点集中度</span>
                  <el-progress
                    :percentage="result.hotspot_concentration * 100"
                    :color="getHotspotColor(result.hotspot_concentration)"
                    :show-text="false"
                  />
                  <span class="metric-value">{{ (result.hotspot_concentration * 100).toFixed(0) }}%</span>
                </div>
              </el-col>
            </el-row>
            <el-divider />
            <el-row :gutter="16">
              <el-col :span="8">
                <el-statistic title="集群总数" :value="result.total_clusters" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="主机总数" :value="result.total_hosts" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="虚拟机总数" :value="result.total_vms" />
              </el-col>
            </el-row>
          </el-card>
        </el-col>
      </el-row>

      <!-- 风险与建议 -->
      <el-row :gutter="20" class="suggestions-row">
        <el-col :span="12">
          <el-card class="suggestions-card">
            <template #header>
              <span class="card-title-risk">
                <el-icon><Warning /></el-icon>
                风险项
              </span>
            </template>
            <ul v-if="result.risk_items.length > 0" class="suggestion-list">
              <li v-for="(item, index) in result.risk_items" :key="index">
                {{ item }}
              </li>
            </ul>
            <el-empty v-else description="暂无风险项" :image-size="60" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="suggestions-card">
            <template #header>
              <span class="card-title-suggestion">
                <el-icon><CircleCheck /></el-icon>
                优化建议
              </span>
            </template>
            <ul v-if="result.recommendations.length > 0" class="suggestion-list">
              <li v-for="(item, index) in result.recommendations" :key="index">
                {{ item }}
              </li>
            </ul>
            <el-empty v-else description="暂无建议" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning, CircleCheck } from '@element-plus/icons-vue'
import { useConnectionStore } from '@/stores/connection'
import { analyzeHealthScore } from '@/api/analysis'
import type { HealthScoreResult } from '@/api/types'

const connectionStore = useConnectionStore()
const selectedConnectionId = ref<number>(0)
const analyzing = ref(false)
const result = ref<HealthScoreResult | null>(null)

const canAnalyze = computed(() => {
  return selectedConnectionId.value > 0 && !analyzing.value
})

async function handleAnalyze() {
  if (!selectedConnectionId.value) {
    ElMessage.warning('请选择连接')
    return
  }

  analyzing.value = true
  result.value = null

  try {
    const data = await analyzeHealthScore(selectedConnectionId.value)
    result.value = data
    ElMessage.success('健康度分析完成')
  } catch (error: any) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    analyzing.value = false
  }
}

function getHealthColor(score: number): string {
  if (score >= 90) return '#67C23A'
  if (score >= 75) return '#409EFF'
  if (score >= 60) return '#E6A23C'
  return '#F56C6C'
}

function getHealthLevelType(level: string): string {
  if (level === 'excellent' || level === 'good') return 'success'
  if (level === 'fair') return 'warning'
  return 'danger'
}

function getHealthLevelText(level: string): string {
  const levelMap: Record<string, string> = {
    excellent: '优秀',
    good: '良好',
    fair: '一般',
    poor: '较差'
  }
  return levelMap[level] || level
}

function getRiskColor(risk: number): string {
  if (risk > 0.7) return '#F56C6C'
  if (risk > 0.4) return '#E6A23C'
  return '#67C23A'
}

function getHotspotColor(hotspot: number): string {
  if (hotspot > 0.6) return '#F56C6C'
  if (hotspot > 0.3) return '#E6A23C'
  return '#67C23A'
}
</script>

<style scoped lang="scss">
.health-analysis-page {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .health-result {
    .score-row {
      .score-card-main {
        text-align: center;

        .score-circle {
          display: flex;
          justify-content: center;
          margin-bottom: $spacing-lg;

          .score-value {
            font-size: 42px;
            font-weight: 600;
            color: $text-color-primary;
          }

          .score-label {
            font-size: $font-size-base;
            color: $text-color-secondary;
          }
        }

        .health-level {
          :deep(.el-tag) {
            font-size: 18px;
            padding: 8px 16px;
            height: auto;
          }
        }
      }

      .metrics-card {
        .metric-item {
          margin-bottom: $spacing-lg;

          .metric-label {
            display: block;
            margin-bottom: $spacing-sm;
            font-size: $font-size-small;
            color: $text-color-secondary;
          }

          .metric-value {
            float: right;
            font-weight: 600;
          }
        }
      }
    }

    .suggestions-row {
      .suggestions-card {
        height: 100%;

        .card-title-risk,
        .card-title-suggestion {
          display: flex;
          align-items: center;
          gap: $spacing-sm;
          font-weight: 600;
        }

        .card-title-risk {
          color: $warning-color;
        }

        .card-title-suggestion {
          color: $success-color;
        }

        .suggestion-list {
          margin: 0;
          padding-left: $spacing-lg;

          li {
            margin-bottom: $spacing-md;
            line-height: 1.6;

            &:last-child {
              margin-bottom: 0;
            }
          }
        }
      }
    }
  }
}
</style>
