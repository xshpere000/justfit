<template>
  <div class="analysis-mode-content">
    <div class="analysis-mode-layout" v-if="modeConfig">
      <section class="params-panel">
        <div class="panel-header">
          <h3>参数配置</h3>
          <el-tag size="small" :type="selectedMode === 'custom' ? 'warning' : 'info'">
            {{ selectedMode === 'custom' ? '可编辑' : '只读' }}
          </el-tag>
        </div>

        <div class="config-scroll-area">
          <el-collapse v-model="collapseActiveNames" class="config-collapse">
            <el-collapse-item name="zombie">
              <template #title>
                <div class="config-group-header">
                  <el-icon><Monitor /></el-icon>
                  <span>僵尸 VM 检测</span>
                </div>
              </template>
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
            </el-collapse-item>

            <el-collapse-item name="rightSize">
              <template #title>
                <div class="config-group-header">
                  <el-icon><TrendCharts /></el-icon>
                  <span>Right Size 分析</span>
                </div>
              </template>
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
            </el-collapse-item>

            <el-collapse-item name="tidal">
              <template #title>
                <div class="config-group-header">
                  <el-icon><Clock /></el-icon>
                  <span>潮汐模式检测</span>
                </div>
              </template>
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
            </el-collapse-item>

            <el-collapse-item name="health">
              <template #title>
                <div class="config-group-header">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>健康评分</span>
                </div>
              </template>
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
            </el-collapse-item>
          </el-collapse>
        </div>
      </section>

      <aside class="control-panel">
        <div class="control-top">
          <div class="panel-header">
            <h3>评估模式配置</h3>
            <div v-if="currentMode.mode" style="display: flex; align-items: center; gap: 6px;">
              <span>当前模式：</span>
              <el-tag :type="getModeTagType(currentMode.mode)" size="small">
                {{ currentMode.modeName }}
              </el-tag>
            </div>
          </div>

          <div class="mode-selector">
            <el-form-item label="">
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
                />
              </el-select>
            </el-form-item>
          </div>

          <div class="mode-description" v-if="selectedModeInfo">
            <el-icon class="desc-icon"><InfoFilled /></el-icon>
            <div class="desc-content">
              <div class="desc-title">{{ selectedModeInfo.name }}</div>
              <div class="desc-text">{{ selectedModeInfo.description }}</div>
            </div>
          </div>
        </div>

        <div class="control-actions">
          <el-button
            size="large"
            :disabled="isTaskRunning || selectedMode !== 'custom'"
            @click="handleResetCustom"
          >
            <el-icon><RefreshLeft /></el-icon>
            重置自定义值
          </el-button>
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
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  InfoFilled,
  Monitor,
  TrendCharts,
  Clock,
  DataAnalysis,
  Check,
  RefreshLeft
} from '@element-plus/icons-vue'
import { getAnalysisMode, updateCustomMode } from '@/api/analysis'
import type { AnalysisModeResponse, AnalysisModeType, AnalysisConfig } from '@/types/v2'
import ParamSlider from './components/ParamSlider.vue'

type FullAnalysisConfig = {
  zombieVM: NonNullable<AnalysisConfig['zombieVM']>
  rightSize: NonNullable<AnalysisConfig['rightSize']>
  tidal: NonNullable<AnalysisConfig['tidal']>
  health: NonNullable<AnalysisConfig['health']>
}

const props = defineProps<{
  taskId: number
  taskStatus: string
}>()

const currentMode = reactive<AnalysisModeResponse>({
  mode: 'safe',
  modeName: '安全模式',
  description: '',
  config: {},
  availableModes: []
})

const selectedMode = ref<AnalysisModeType>('safe')
const originalMode = ref<AnalysisModeType>('safe')
const originalConfigText = ref('')
const collapseActiveNames = ref<string[]>([])

const modeConfig = ref<FullAnalysisConfig>({
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

const availableModes = computed(() => currentMode.availableModes.length > 0
  ? currentMode.availableModes
  : [
      { mode: 'safe', name: '安全模式', description: '保守的分析策略，误报率低' },
      { mode: 'saving', name: '节能模式', description: '平衡性能与节能' },
      { mode: 'aggressive', name: '激进模式', description: '最大化资源回收' },
      { mode: 'custom', name: '自定义模式', description: '用户自定义配置' }
    ]
)

const selectedModeInfo = computed(() => {
  return availableModes.value.find(m => m.mode === selectedMode.value)
})

const saving = ref(false)

const hasChanges = computed(() => {
  if (selectedMode.value !== originalMode.value) {
    return true
  }

  if (selectedMode.value !== 'custom') {
    return false
  }

  return serializeConfig(modeConfig.value) !== originalConfigText.value
})

const isTaskRunning = computed(() => {
  return props.taskStatus === 'running' || props.taskStatus === 'pending'
})

function getModeTagType(mode: AnalysisModeType) {
  const typeMap: Record<AnalysisModeType, string> = {
    safe: 'success',
    saving: 'warning',
    aggressive: 'danger',
    custom: 'info'
  }
  return typeMap[mode] || 'info'
}

function cloneConfig(config: AnalysisConfig | FullAnalysisConfig): FullAnalysisConfig {
  return JSON.parse(JSON.stringify(config)) as FullAnalysisConfig
}

function serializeConfig(config: FullAnalysisConfig): string {
  return JSON.stringify(config)
}

function getModePresets(): Record<AnalysisModeType, FullAnalysisConfig> {
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

async function loadAnalysisMode() {
  if (!props.taskId) {
    return
  }

  try {
    // 默认加载安全模式
    const mode = 'safe' as AnalysisModeType
    selectedMode.value = mode
    originalMode.value = mode

    const presets = getModePresets()
    modeConfig.value = cloneConfig(presets[mode] as AnalysisConfig)
    originalConfigText.value = serializeConfig(modeConfig.value)

    currentMode.mode = mode
    currentMode.modeName = mode === 'safe' ? '安全模式' : mode === 'saving' ? '节能模式' : mode === 'aggressive' ? '激进模式' : '自定义模式'
    currentMode.description = mode === 'safe' ? '保守的分析策略，误报率低' : mode === 'saving' ? '平衡性能与节能' : mode === 'aggressive' ? '最大化资源回收' : '用户自定义配置'

    // 设置可用的模式列表
    currentMode.availableModes = [
      { mode: 'safe', name: '安全模式', description: '保守的分析策略，误报率低' },
      { mode: 'saving', name: '节能模式', description: '平衡性能与节能' },
      { mode: 'aggressive', name: '激进模式', description: '最大化资源回收' },
      { mode: 'custom', name: '自定义模式', description: '用户自定义配置' }
    ]
  } catch (error: any) {
    console.error('加载评估模式失败:', error)
    ElMessage.error('加载评估模式失败: ' + (error.message || '未知错误'))
  }
}

function handleModeChange(mode: AnalysisModeType) {
  const presets = getModePresets()
  if (presets[mode]) {
    modeConfig.value = cloneConfig(presets[mode])
  }
}

async function handleSave() {
  if (!props.taskId) {
    return
  }

  saving.value = true
  try {
    const configJSON = selectedMode.value === 'custom'
      ? JSON.stringify(modeConfig.value)
      : ''

    await updateCustomMode(modeConfig.value)

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

async function handleResetCustom() {
  if (selectedMode.value !== 'custom') {
    return
  }

  try {
    await ElMessageBox.confirm(
      '确定要重置当前自定义参数为默认值吗？',
      '确认重置',
      { type: 'warning' }
    )

    modeConfig.value = cloneConfig(getModePresets().custom)
    ElMessage.success('自定义参数已重置，请点击保存配置')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('重置失败:', error)
      ElMessage.error('重置失败: ' + (error.message || '未知错误'))
    }
  }
}

watch(
  () => props.taskId,
  () => {
    loadAnalysisMode()
  },
  { immediate: true }
)

onMounted(() => {
  loadAnalysisMode()
})
</script>

<style scoped lang="scss">
.analysis-mode-content {
  height: 100%;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;

  .analysis-mode-layout {
    height: 100%;
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(0, 6fr) minmax(340px, 4fr);
    gap: 16px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--el-border-color-lighter);
    padding-bottom: 12px;
    margin-bottom: 12px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .params-panel {
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 16px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    background: var(--el-fill-color-blank);

    .config-scroll-area {
      min-height: 0;
      overflow-y: auto;
      padding-right: 6px;

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
    }
  }

  .control-panel {
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    background: var(--el-fill-color-blank);

    .control-top {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .mode-selector {
      :deep(.el-form-item) {
        margin-bottom: 0;
      }
    }

    .mode-description {
      display: flex;
      gap: 10px;
      padding: 12px;
      background: var(--el-fill-color-light);
      border-radius: 8px;

      .desc-icon {
        color: var(--el-color-primary);
        font-size: 20px;
        flex-shrink: 0;
      }

      .desc-content {
        flex: 1;

        .desc-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          margin-bottom: 6px;
        }

        .desc-text {
          font-size: 13px;
          color: var(--el-text-color-regular);
          line-height: 1.6;
        }
      }
    }

    .control-actions {
      margin-top: auto;
      padding-top: 12px;
      border-top: 1px solid var(--el-border-color-lighter);
      display: flex;
      flex-direction: row;
      justify-content: space-between;
      gap: 10px;

      .el-button {
        width: 136px;
        margin-left: 0;
      }
    }
  }

  .config-collapse {
    border-top: none;
    border-bottom: none;

    :deep(.el-collapse-item) {
      border: 1px solid var(--el-border-color-lighter);
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
    }

    :deep(.el-collapse-item__header) {
      height: auto;
      line-height: normal;
      padding: 12px 14px;
      background: var(--el-fill-color-blank);
      border-bottom: none;
    }

    :deep(.el-collapse-item__wrap) {
      border-bottom: none;
    }

    :deep(.el-collapse-item__content) {
      padding: 0 14px 14px;
    }

    .config-group-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 600;
      color: var(--el-text-color-primary);

      .el-icon {
        color: var(--el-color-primary);
      }
    }

    .param-list {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding-top: 8px;
    }
  }
}

@media (max-width: 960px) {
  .analysis-mode-content {
    .analysis-mode-layout {
      grid-template-columns: 1fr;
    }

    .control-panel {
      .control-actions {
        margin-top: 0;
      }
    }
  }
}
</style>
