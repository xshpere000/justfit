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
            <!-- 闲置检测 -->
            <el-collapse-item name="idle">
              <template #title>
                <div class="config-group-header">
                  <el-icon><Monitor /></el-icon>
                  <span>闲置检测</span>
                </div>
              </template>
              <div class="param-list">
                <ParamSlider
                  label="分析天数"
                  v-model="modeConfig.idle.days"
                  :min="7"
                  :max="90"
                  :unit="'天'"
                  :disabled="selectedMode !== 'custom'"
                  :description="'分析过去N天的指标数据，最少7天（与最短采集周期一致），最多90天'"
                />
                <ParamSlider
                  label="CPU 阈值"
                  v-model="modeConfig.idle.cpuThreshold"
                  :min="1"
                  :max="50"
                  :unit="'%'"
                  :step="0.5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'开机VM的CPU P95低于此值视为低使用，建议范围5%~20%'"
                />
                <ParamSlider
                  label="内存阈值"
                  v-model="modeConfig.idle.memoryThreshold"
                  :min="1"
                  :max="60"
                  :unit="'%'"
                  :step="0.5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'开机VM的内存P95低于此值视为低使用，建议范围10%~30%'"
                />
                <ParamSlider
                  label="最小置信度"
                  v-model="modeConfig.idle.minConfidence"
                  :min="20"
                  :max="100"
                  :unit="'%'"
                  :step="5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'低于此置信度的结果不输出，越高越严格（越少结果）'"
                />
              </div>
            </el-collapse-item>

            <!-- 资源配置优化 -->
            <el-collapse-item name="rightsize">
              <template #title>
                <div class="config-group-header">
                  <el-icon><TrendCharts /></el-icon>
                  <span>资源配置优化</span>
                </div>
              </template>
              <div class="param-list">
                <ParamSlider
                  label="分析天数"
                  v-model="modeConfig.resource.rightsize.days"
                  :min="7"
                  :max="90"
                  :unit="'天'"
                  :disabled="selectedMode !== 'custom'"
                  :description="'分析过去N天的指标数据，最少7天（天级数据需至少7个点），最多90天'"
                />
                <ParamSlider
                  label="CPU 缓冲比例"
                  v-model="modeConfig.resource.rightsize.cpuBufferPercent"
                  :min="5"
                  :max="80"
                  :unit="'%'"
                  :step="5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'推荐值在P95基础上额外保留的CPU余量，防止突发峰值，建议10%~30%'"
                />
                <ParamSlider
                  label="内存缓冲比例"
                  v-model="modeConfig.resource.rightsize.memoryBufferPercent"
                  :min="5"
                  :max="80"
                  :unit="'%'"
                  :step="5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'推荐值在P95基础上额外保留的内存余量，防止突发峰值，建议10%~30%'"
                />
                <ParamSlider
                  label="最小置信度"
                  v-model="modeConfig.resource.rightsize.minConfidence"
                  :min="20"
                  :max="100"
                  :unit="'%'"
                  :step="5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'低于此置信度的优化建议不输出，越高越严格，数据点越多置信度越高'"
                />
              </div>
            </el-collapse-item>

            <!-- 使用模式分析 -->
            <el-collapse-item name="usagePattern">
              <template #title>
                <div class="config-group-header">
                  <el-icon><Clock /></el-icon>
                  <span>使用模式分析</span>
                </div>
              </template>
              <div class="param-list">
                <ParamSlider
                  label="变异系数阈值"
                  v-model="modeConfig.resource.usagePattern.cvThreshold"
                  :min="0.2"
                  :max="0.8"
                  :step="0.05"
                  :disabled="selectedMode !== 'custom'"
                  :description="'CPU使用波动的变异系数（标准差/均值）须超过此阈值才判为潮汐，越低越宽松'"
                />
                <ParamSlider
                  label="峰谷比阈值"
                  v-model="modeConfig.resource.usagePattern.peakValleyRatio"
                  :min="2.0"
                  :max="10.0"
                  :step="0.5"
                  :disabled="selectedMode !== 'custom'"
                  :description="'峰值与谷值的最小差异倍数须超过此值才判为潮汐，越低越宽松'"
                />
              </div>
            </el-collapse-item>

            <!-- 健康评分 -->
            <el-collapse-item name="health">
              <template #title>
                <div class="config-group-header">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>健康评分</span>
                </div>
              </template>
              <div class="param-list">
                <ParamSlider
                  label="超配阈值"
                  v-model="modeConfig.health.overcommitThreshold"
                  :min="1.0"
                  :max="4.0"
                  :step="0.1"
                  :disabled="selectedMode !== 'custom'"
                  :description="'集群vCPU/pCPU比例超过此值视为超配，如1.5表示超过150%时警告'"
                />
                <ParamSlider
                  label="热点阈值"
                  v-model="modeConfig.health.hotspotThreshold"
                  :min="2"
                  :max="20"
                  :step="1"
                  :disabled="selectedMode !== 'custom'"
                  :description="'每个物理CPU核心承载的VM数量上限，超过则视为热点主机，建议5~10'"
                />
                <ParamSlider
                  label="均衡阈值"
                  v-model="modeConfig.health.balanceThreshold"
                  :min="0.2"
                  :max="1.0"
                  :step="0.05"
                  :disabled="selectedMode !== 'custom'"
                  :description="'主机间负载分布的变异系数上限，超过则视为不均衡，越低要求越宽松'"
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
import { getAnalysisMode, updateTaskCustomConfig } from '@/api/analysis'
import { getTaskDetail } from '@/api/task'
import type { AnalysisModeResponse, AnalysisModeType, AnalysisModeConfig } from '@/api/analysis'
import ParamSlider from './components/ParamSlider.vue'

const props = defineProps<{
  taskId: number
  taskStatus: string
}>()

const currentMode = reactive<AnalysisModeResponse>({
  mode: 'safe',
  modeName: '安全模式',
  description: '',
  config: {
    idle: {
      days: 30,
      cpuThreshold: 5.0,
      memoryThreshold: 10.0,
      minConfidence: 80.0
    },
    resource: {
      rightsize: {
        days: 30,
        cpuBufferPercent: 30.0,
        memoryBufferPercent: 30.0,
        minConfidence: 70.0
      },
      usagePattern: {
        cvThreshold: 0.3,
        peakValleyRatio: 2.0
      }
    },
    health: {
      overcommitThreshold: 1.2,
      hotspotThreshold: 5.0,
      balanceThreshold: 0.5
    }
  },
  availableModes: []
})

const selectedMode = ref<AnalysisModeType>('safe')
const originalMode = ref<AnalysisModeType>('safe')
const originalConfigText = ref('')
const collapseActiveNames = ref<string[]>(['idle', 'rightsize', 'usagePattern', 'health'])

const modeConfig = ref<AnalysisModeConfig>({
  idle: {
    days: 30,
    cpuThreshold: 5.0,
    memoryThreshold: 10.0,
    minConfidence: 80.0
  },
  resource: {
    rightsize: {
      days: 30,
      cpuBufferPercent: 30.0,
      memoryBufferPercent: 30.0,
      minConfidence: 70.0
    },
    usagePattern: {
      cvThreshold: 0.3,
      peakValleyRatio: 2.0
    }
  },
  health: {
    overcommitThreshold: 1.2,
    hotspotThreshold: 5.0,
    balanceThreshold: 0.5
  }
})

const availableModes = computed(() => currentMode.availableModes.length > 0
  ? currentMode.availableModes
  : [
      { mode: 'safe', name: '安全模式', description: '保守阈值，适合生产环境' },
      { mode: 'saving', name: '节省模式', description: '平衡阈值，推荐默认' },
      { mode: 'aggressive', name: '激进模式', description: '最大化发现问题' },
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

function cloneConfig(config: AnalysisModeConfig): AnalysisModeConfig {
  return JSON.parse(JSON.stringify(config)) as AnalysisModeConfig
}

function serializeConfig(config: AnalysisModeConfig): string {
  return JSON.stringify(config)
}

function getModePresets(): Record<AnalysisModeType, AnalysisModeConfig> {
  return {
    safe: {
      idle: {
        days: 30,
        cpuThreshold: 5.0,
        memoryThreshold: 10.0,
        minConfidence: 80.0
      },
      resource: {
        rightsize: {
          days: 30,
          cpuBufferPercent: 30.0,
          memoryBufferPercent: 30.0,
          minConfidence: 70.0
        },
        usagePattern: {
          cvThreshold: 0.3,
          peakValleyRatio: 2.0
        }
      },
      health: {
        overcommitThreshold: 1.2,
        hotspotThreshold: 5.0,
        balanceThreshold: 0.5
      }
    },
    saving: {
      idle: {
        days: 14,
        cpuThreshold: 10.0,
        memoryThreshold: 20.0,
        minConfidence: 60.0
      },
      resource: {
        rightsize: {
          days: 14,
          cpuBufferPercent: 20.0,
          memoryBufferPercent: 20.0,
          minConfidence: 60.0
        },
        usagePattern: {
          cvThreshold: 0.4,
          peakValleyRatio: 2.5
        }
      },
      health: {
        overcommitThreshold: 1.5,
        hotspotThreshold: 7.0,
        balanceThreshold: 0.6
      }
    },
    aggressive: {
      idle: {
        days: 7,
        cpuThreshold: 15.0,
        memoryThreshold: 25.0,
        minConfidence: 50.0
      },
      resource: {
        rightsize: {
          days: 7,
          cpuBufferPercent: 10.0,
          memoryBufferPercent: 10.0,
          minConfidence: 50.0
        },
        usagePattern: {
          cvThreshold: 0.5,
          peakValleyRatio: 3.0
        }
      },
      health: {
        overcommitThreshold: 2.0,
        hotspotThreshold: 10.0,
        balanceThreshold: 0.7
      }
    },
    custom: {
      idle: {
        days: 14,
        cpuThreshold: 10.0,
        memoryThreshold: 20.0,
        minConfidence: 60.0
      },
      resource: {
        rightsize: {
          days: 14,
          cpuBufferPercent: 20.0,
          memoryBufferPercent: 20.0,
          minConfidence: 60.0
        },
        usagePattern: {
          cvThreshold: 0.4,
          peakValleyRatio: 2.5
        }
      },
      health: {
        overcommitThreshold: 1.5,
        hotspotThreshold: 7.0,
        balanceThreshold: 0.6
      }
    }
  }
}

async function loadAnalysisMode() {
  if (!props.taskId) {
    return
  }

  try {
    // 获取任务详情以读取保存的配置
    const task = await getTaskDetail(props.taskId)
    const taskMode = task.config?.mode as AnalysisModeType || 'saving'
    const customConfig = task.config?.customConfig as Record<string, unknown> || {}

    selectedMode.value = taskMode
    originalMode.value = taskMode

    const presets = getModePresets()

    // 如果是 custom 模式且有自定义配置，合并基础配置和自定义配置
    if (taskMode === 'custom' && Object.keys(customConfig).length > 0) {
      const baseMode = (task.config?.baseMode as AnalysisModeType) || 'saving'
      const baseConfig = presets[baseMode]

      // 深度合并自定义配置到基础配置
      modeConfig.value = {
        idle: { ...baseConfig.idle, ...(customConfig.idle as object || {}) },
        resource: {
          rightsize: { ...baseConfig.resource.rightsize, ...(customConfig.resource?.rightsize as object || {}) },
          usagePattern: { ...baseConfig.resource.usagePattern, ...(customConfig.resource?.usagePattern as object || {}) }
        },
        health: { ...baseConfig.health, ...(customConfig.health as object || {}) }
      }
    } else {
      // 使用预设配置
      modeConfig.value = cloneConfig(presets[taskMode])
    }

    originalConfigText.value = serializeConfig(modeConfig.value)

    currentMode.mode = taskMode
    currentMode.modeName = taskMode === 'safe' ? '安全模式' : taskMode === 'saving' ? '节省模式' : taskMode === 'aggressive' ? '激进模式' : '自定义模式'
    currentMode.description = taskMode === 'safe' ? '保守阈值，适合生产环境' : taskMode === 'saving' ? '平衡阈值，推荐默认' : taskMode === 'aggressive' ? '最大化发现问题' : '用户自定义配置'
    currentMode.config = modeConfig.value

    // 设置可用的模式列表
    currentMode.availableModes = [
      { mode: 'safe', name: '安全模式', description: '保守阈值，适合生产环境' },
      { mode: 'saving', name: '节省模式', description: '平衡阈值，推荐默认' },
      { mode: 'aggressive', name: '激进模式', description: '最大化发现问题' },
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
    // 保存自定义配置到任务
    await updateTaskCustomConfig(props.taskId, 'idle', modeConfig.value.idle)
    await updateTaskCustomConfig(props.taskId, 'resource', modeConfig.value.resource)
    await updateTaskCustomConfig(props.taskId, 'health', modeConfig.value.health)

    currentMode.mode = selectedMode.value
    const modeInfo = availableModes.value.find(m => m.mode === selectedMode.value)
    if (modeInfo) {
      currentMode.modeName = modeInfo.name
      currentMode.description = modeInfo.description
    }

    ElMessage.success('评估模式已更新')
    originalMode.value = selectedMode.value
    originalConfigText.value = serializeConfig(modeConfig.value)
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
