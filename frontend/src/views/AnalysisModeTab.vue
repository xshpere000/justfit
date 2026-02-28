<template>
  <div class="analysis-mode-content">
    <!-- 模式选择区域 -->
    <el-card class="mode-selection-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">评估模式配置</span>
          <el-tag v-if="currentMode.mode" :type="getModeTagType(currentMode.mode)" size="large">
            {{ currentMode.modeName }}
          </el-tag>
        </div>
      </template>

      <!-- 模式选择下拉列表 -->
      <div class="mode-selector">
        <el-form-item label="选择评估模式">
          <el-select
            v-model="selectedMode"
            placeholder="请选择评估模式"
            size="large"
            style="width: 100%"
            :disabled="isTaskRunning"
            @change="handleModeChange"
          >
            <el-option
              v-for="mode in availableModes"
              :key="mode.mode"
              :label="mode.name"
              :value="mode.mode"
            >
              <div class="mode-option-item">
                <span class="mode-name">{{ mode.name }}</span>
                <span class="mode-desc">{{ mode.description }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </div>

      <!-- 模式说明 -->
      <div class="mode-description" v-if="selectedModeInfo">
        <el-icon class="desc-icon"><InfoFilled /></el-icon>
        <div class="desc-content">
          <div class="desc-title">{{ selectedModeInfo.name }}</div>
          <div class="desc-text">{{ selectedModeInfo.description }}</div>
          <div class="desc-hint" v-if="selectedMode !== 'custom'">
            <el-icon><Lock /></el-icon>
            内置模式参数已优化，仅供查看。如需自定义参数，请选择"自定义模式"
          </div>
          <div class="desc-hint" v-else>
            <el-icon><Edit /></el-icon>
            自定义模式允许您手动调整各项参数
          </div>
        </div>
      </div>

      <!-- 参数配置区域（滚动） -->
      <div class="config-section" v-if="modeConfig">
        <div class="config-section-header">
          <h4>参数配置</h4>
          <el-tag size="small" :type="selectedMode === 'custom' ? 'warning' : 'info'">
            {{ selectedMode === 'custom' ? '可编辑' : '只读' }}
          </el-tag>
        </div>

        <div class="config-scroll-area">
          <!-- 僵尸 VM 检测 -->
          <div class="config-group">
            <div class="config-group-header">
              <el-icon><Monitor /></el-icon>
              <span>僵尸 VM 检测</span>
            </div>

            <div class="param-list">
              <ParamSlider
                label="分析天数"
                v-model="modeConfig.zombieVM.analysisDays"
                :min="1"
                :max="90"
                :unit="'天'"
                :disabled="selectedMode !== 'custom'"
                :description="'分析过去N天的使用数据'"
              />
              <ParamSlider
                label="CPU 阈值"
                v-model="modeConfig.zombieVM.cpuThreshold"
                :min="0"
                :max="100"
                :unit="'%'"
                :step="0.5"
                :disabled="selectedMode !== 'custom'"
                :description="'CPU使用率低于此值视为低使用'"
              />
              <ParamSlider
                label="内存阈值"
                v-model="modeConfig.zombieVM.memoryThreshold"
                :min="0"
                :max="100"
                :unit="'%'"
                :step="0.5"
                :disabled="selectedMode !== 'custom'"
                :description="'内存使用率低于此值视为低使用'"
              />
              <ParamSlider
                label="I/O 阈值"
                v-model="modeConfig.zombieVM.ioThreshold"
                :min="0"
                :max="1000"
                :step="10"
                :disabled="selectedMode !== 'custom'"
                :description="'I/O使用率低于此值视为低使用'"
              />
              <ParamSlider
                label="网络阈值"
                v-model="modeConfig.zombieVM.networkThreshold"
                :min="0"
                :max="1000"
                :step="10"
                :disabled="selectedMode !== 'custom'"
                :description="'网络使用率低于此值视为低使用'"
              />
              <ParamSlider
                label="最小置信度"
                v-model="modeConfig.zombieVM.minConfidence"
                :min="0"
                :max="100"
                :unit="'%'"
                :step="5"
                :disabled="selectedMode !== 'custom'"
                :description="'判断为僵尸VM的最低置信度要求'"
              />
            </div>
          </div>

          <!-- Right Size 分析 -->
          <div class="config-group">
            <div class="config-group-header">
              <el-icon><TrendCharts /></el-icon>
              <span>Right Size 分析</span>
            </div>

            <div class="param-list">
              <ParamSlider
                label="分析天数"
                v-model="modeConfig.rightSize.analysisDays"
                :min="1"
                :max="30"
                :unit="'天'"
                :disabled="selectedMode !== 'custom'"
                :description="'分析过去N天的使用数据'"
              />
              <ParamSlider
                label="缓冲比例"
                v-model="modeConfig.rightSize.bufferRatio"
                :min="1.0"
                :max="2.0"
                :step="0.05"
                :disabled="selectedMode !== 'custom'"
                :description="'资源配置时的缓冲倍数'"
              />
              <ParamSlider
                label="P95 阈值"
                v-model="modeConfig.rightSize.p95Threshold"
                :min="50"
                :max="99"
                :unit="'%'"
                :disabled="selectedMode !== 'custom'"
                :description="'使用P95百分位数作为资源使用参考'"
              />
              <ParamSlider
                label="小幅调整阈值"
                v-model="modeConfig.rightSize.smallMargin"
                :min="0"
                :max="1"
                :step="0.05"
                :disabled="selectedMode !== 'custom'"
                :description="'资源配置调整幅度小于此值视为小幅调整'"
              />
              <ParamSlider
                label="大幅调整阈值"
                v-model="modeConfig.rightSize.largeMargin"
                :min="0"
                :max="1"
                :step="0.05"
                :disabled="selectedMode !== 'custom'"
                :description="'资源配置调整幅度大于此值视为大幅调整'"
              />
            </div>
          </div>

          <!-- 潮汐模式检测 -->
          <div class="config-group">
            <div class="config-group-header">
              <el-icon><Clock /></el-icon>
              <span>潮汐模式检测</span>
            </div>

            <div class="param-list">
              <ParamSlider
                label="分析天数"
                v-model="modeConfig.tidal.analysisDays"
                :min="1"
                :max="90"
                :unit="'天'"
                :disabled="selectedMode !== 'custom'"
                :description="'分析过去N天的使用数据'"
              />
              <ParamSlider
                label="最小稳定性"
                v-model="modeConfig.tidal.minStability"
                :min="0"
                :max="100"
                :unit="'分'"
                :step="5"
                :disabled="selectedMode !== 'custom'"
                :description="'模式稳定性的最低评分要求'"
              />
              <ParamSlider
                label="最小变化幅度"
                v-model="modeConfig.tidal.minVariation"
                :min="0"
                :max="100"
                :unit="'%'"
                :step="5"
                :disabled="selectedMode !== 'custom'"
                :description="'峰值与谷值的最小差异百分比'"
              />
            </div>
          </div>

          <!-- 健康评分 -->
          <div class="config-group">
            <div class="config-group-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>健康评分</span>
            </div>

            <div class="param-list">
              <ParamSlider
                label="资源均衡度权重"
                v-model="modeConfig.health.resourceBalanceWeight"
                :min="0"
                :max="1"
                :step="0.05"
                :disabled="selectedMode !== 'custom'"
                :description="'资源分配均衡性的权重占比'"
              />
              <ParamSlider
                label="超配风险权重"
                v-model="modeConfig.health.overcommitRiskWeight"
                :min="0"
                :max="1"
                :step="0.05"
                :disabled="selectedMode !== 'custom'"
                :description="'资源超分配风险的权重占比'"
              />
              <ParamSlider
                label="热点集中度权重"
                v-model="modeConfig.health.hotspotWeight"
                :min="0"
                :max="1"
                :step="0.05"
                :disabled="selectedMode !== 'custom'"
                :description="'热点负载集中度的权重占比'"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button
          type="primary"
          size="large"
          :disabled="!hasChanges || isTaskRunning"
          :loading="saving"
          @click="handleSave"
        >
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
        <el-button
          size="large"
          :disabled="isTaskRunning"
          @click="handleReset"
        >
          <el-icon><RefreshLeft /></el-icon>
          重置为默认
        </el-button>
      </div>

      <!-- 提示信息 -->
      <el-alert
        v-if="isTaskRunning"
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 16px"
      >
        任务运行中无法修改评估模式，请等待任务完成后再试
      </el-alert>

      <el-alert
        v-else-if="selectedMode === 'custom'"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 16px"
      >
        自定义模式已启用，修改参数后请点击"保存配置"。修改后需要重新运行分析才能使用新配置
      </el-alert>

      <el-alert
        v-else
        type="success"
        :closable="false"
        show-icon
        style="margin-top: 16px"
      >
        当前使用 {{ currentMode.modeName }}，参数已优化，切换模式后请点击"保存配置"
      </el-alert>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  InfoFilled,
  Lock,
  Edit,
  Monitor,
  TrendCharts,
  Clock,
  DataAnalysis,
  Check,
  RefreshLeft
} from '@element-plus/icons-vue'
import * as App from '../../wailsjs/go/main/App'
import type { AnalysisModeResponse, AnalysisModeType, AnalysisConfig } from '@/types/v2'
import ParamSlider from './components/ParamSlider.vue'

const props = defineProps<{
  taskId: number
  taskStatus: string
}>()

// 当前模式
const currentMode = reactive<AnalysisModeResponse>({
  mode: 'safe',
  modeName: '安全模式',
  description: '',
  config: {},
  availableModes: []
})

// 选中的模式
const selectedMode = ref<AnalysisModeType>('safe')

// 模式配置
const modeConfig = ref<AnalysisConfig>({
  zombieVM: {
    analysisDays: 30,
    cpuThreshold: 5.0,
    memoryThreshold: 10.0,
    ioThreshold: 10.0,
    networkThreshold: 10.0,
    minConfidence: 80.0
  },
  rightSize: {
    analysisDays: 7,
    bufferRatio: 1.3,
    p95Threshold: 95.0,
    smallMargin: 0.4,
    largeMargin: 0.6
  },
  tidal: {
    analysisDays: 30,
    minStability: 70.0,
    minVariation: 40.0
  },
  health: {
    resourceBalanceWeight: 0.4,
    overcommitRiskWeight: 0.3,
    hotspotWeight: 0.3
  }
})

// 可用模式列表
const availableModes = computed(() => currentMode.availableModes || [])

// 选中的模式信息
const selectedModeInfo = computed(() => {
  return availableModes.value.find(m => m.mode === selectedMode.value)
})

// 保存状态
const saving = ref(false)

// 是否有变更
const hasChanges = computed(() => {
  return selectedMode.value !== currentMode.mode
})

// 任务是否运行中
const isTaskRunning = computed(() => {
  return props.taskStatus === 'running' || props.taskStatus === 'pending'
})

// 获取模式标签类型
function getModeTagType(mode: AnalysisModeType) {
  const typeMap: Record<AnalysisModeType, string> = {
    safe: 'success',
    saving: 'warning',
    aggressive: 'danger',
    custom: 'info'
  }
  return typeMap[mode] || 'info'
}

// 加载评估模式
async function loadAnalysisMode() {
  if (!props.taskId) return

  try {
    const result = await App.GetAnalysisMode(props.taskId)
    if (result) {
      Object.assign(currentMode, result)
      selectedMode.value = result.mode as AnalysisModeType

      // 加载配置
      if (result.config) {
        modeConfig.value = { ...result.config }
      }
    }
  } catch (error: any) {
    console.error('加载评估模式失败:', error)
    ElMessage.error('加载评估模式失败: ' + (error.message || '未知错误'))
  }
}

// 模式切换
function handleModeChange(mode: AnalysisModeType) {
  console.log('切换模式:', mode)

  // 根据选择的模式更新预设配置
  const presets = getModePresets()
  if (presets[mode]) {
    modeConfig.value = JSON.parse(JSON.stringify(presets[mode]))
  }
}

// 获取模式预设配置
function getModePresets() {
  return {
    safe: {
      zombieVM: {
        analysisDays: 30,
        cpuThreshold: 5.0,
        memoryThreshold: 10.0,
        ioThreshold: 10.0,
        networkThreshold: 10.0,
        minConfidence: 80.0
      },
      rightSize: {
        analysisDays: 7,
        bufferRatio: 1.3,
        p95Threshold: 95.0,
        smallMargin: 0.4,
        largeMargin: 0.6
      },
      tidal: {
        analysisDays: 30,
        minStability: 70.0,
        minVariation: 40.0
      },
      health: {
        resourceBalanceWeight: 0.4,
        overcommitRiskWeight: 0.3,
        hotspotWeight: 0.3
      }
    },
    saving: {
      zombieVM: {
        analysisDays: 14,
        cpuThreshold: 10.0,
        memoryThreshold: 20.0,
        ioThreshold: 20.0,
        networkThreshold: 20.0,
        minConfidence: 60.0
      },
      rightSize: {
        analysisDays: 7,
        bufferRatio: 1.2,
        p95Threshold: 90.0,
        smallMargin: 0.3,
        largeMargin: 0.5
      },
      tidal: {
        analysisDays: 21,
        minStability: 60.0,
        minVariation: 30.0
      },
      health: {
        resourceBalanceWeight: 0.4,
        overcommitRiskWeight: 0.3,
        hotspotWeight: 0.3
      }
    },
    aggressive: {
      zombieVM: {
        analysisDays: 7,
        cpuThreshold: 15.0,
        memoryThreshold: 30.0,
        ioThreshold: 30.0,
        networkThreshold: 30.0,
        minConfidence: 50.0
      },
      rightSize: {
        analysisDays: 5,
        bufferRatio: 1.1,
        p95Threshold: 85.0,
        smallMargin: 0.2,
        largeMargin: 0.4
      },
      tidal: {
        analysisDays: 14,
        minStability: 50.0,
        minVariation: 20.0
      },
      health: {
        resourceBalanceWeight: 0.3,
        overcommitRiskWeight: 0.3,
        hotspotWeight: 0.4
      }
    },
    custom: {
      zombieVM: {
        analysisDays: 14,
        cpuThreshold: 10.0,
        memoryThreshold: 20.0,
        ioThreshold: 20.0,
        networkThreshold: 20.0,
        minConfidence: 60.0
      },
      rightSize: {
        analysisDays: 7,
        bufferRatio: 1.2,
        p95Threshold: 90.0,
        smallMargin: 0.3,
        largeMargin: 0.5
      },
      tidal: {
        analysisDays: 21,
        minStability: 60.0,
        minVariation: 30.0
      },
      health: {
        resourceBalanceWeight: 0.4,
        overcommitRiskWeight: 0.3,
        hotspotWeight: 0.3
      }
    }
  }
}

// 保存配置
async function handleSave() {
  if (!props.taskId) return

  saving.value = true
  try {
    const configJSON = selectedMode.value === 'custom'
      ? JSON.stringify(modeConfig.value)
      : ''

    await App.SetAnalysisMode(props.taskId, selectedMode.value, configJSON)

    // 更新当前模式
    currentMode.mode = selectedMode.value
    const modeInfo = availableModes.value.find(m => m.mode === selectedMode.value)
    if (modeInfo) {
      currentMode.modeName = modeInfo.name
      currentMode.description = modeInfo.description
    }

    ElMessage.success('评估模式已更新')
    await loadAnalysisMode()
  } catch (error: any) {
    console.error('保存评估模式失败:', error)
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

// 重置为默认
async function handleReset() {
  if (!props.taskId) return

  try {
    await ElMessageBox.confirm(
      '确定要重置为默认的安全模式吗？',
      '确认重置',
      { type: 'warning' }
    )

    await App.SetAnalysisMode(props.taskId, 'safe', '')
    selectedMode.value = 'safe'
    handleModeChange('safe')
    await loadAnalysisMode()
    ElMessage.success('已重置为安全模式')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('重置失败:', error)
      ElMessage.error('重置失败: ' + (error.message || '未知错误'))
    }
  }
}

// 监听任务 ID 变化
watch(() => props.taskId, () => {
  loadAnalysisMode()
}, { immediate: true })

onMounted(() => {
  loadAnalysisMode()
})
</script>

<style scoped lang="scss">
.analysis-mode-content {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  box-sizing: border-box;

  .mode-selection-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .card-title {
        font-size: 18px;
        font-weight: 600;
      }
    }

    .mode-selector {
      margin-bottom: 20px;

      :deep(.el-form-item) {
        margin-bottom: 0;
      }

      .mode-option-item {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .mode-name {
          font-weight: 600;
          color: var(--el-text-color-primary);
        }

        .mode-desc {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
    }

    .mode-description {
      display: flex;
      gap: 12px;
      padding: 16px;
      background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
      border-radius: 8px;
      margin-bottom: 24px;

      .desc-icon {
        color: var(--el-color-primary);
        font-size: 24px;
        flex-shrink: 0;
      }

      .desc-content {
        flex: 1;

        .desc-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin-bottom: 8px;
        }

        .desc-text {
          font-size: 14px;
          color: var(--el-text-color-regular);
          line-height: 1.6;
          margin-bottom: 8px;
        }

        .desc-hint {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: var(--el-color-warning);
          background: rgba(var(--el-color-warning-rgb), 0.1);
          padding: 8px 12px;
          border-radius: 6px;
        }
      }
    }

    .config-section {
      margin-bottom: 24px;

      .config-section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;

        h4 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }

      .config-scroll-area {
        max-height: 600px;
        overflow-y: auto;
        padding-right: 8px;

        &::-webkit-scrollbar {
          width: 8px;
        }

        &::-webkit-scrollbar-track {
          background: var(--el-fill-color-lighter);
          border-radius: 4px;
        }

        &::-webkit-scrollbar-thumb {
          background: var(--el-border-color-darker);
          border-radius: 4px;

          &:hover {
            background: var(--el-border-color-dark);
          }
        }

        .config-group {
          margin-bottom: 24px;
          padding: 16px;
          background: var(--el-fill-color-blank);
          border: 1px solid var(--el-border-color-lighter);
          border-radius: 8px;

          &:last-child {
            margin-bottom: 0;
          }

          .config-group-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 15px;
            font-weight: 600;
            color: var(--el-text-color-primary);
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--el-border-color-lighter);

            .el-icon {
              color: var(--el-color-primary);
            }
          }

          .param-list {
            display: flex;
            flex-direction: column;
            gap: 16px;
          }
        }
      }
    }

    .action-buttons {
      display: flex;
      gap: 12px;
      padding-top: 16px;
      border-top: 1px solid var(--el-border-color-lighter);
    }
  }
}

@media (max-width: 768px) {
  .analysis-mode-content {
    padding: 16px;

    .config-scroll-area {
      max-height: 400px !important;
    }
  }
}
</style>
