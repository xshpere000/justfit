<template>
  <div class="param-slider" :class="{ 'is-disabled': disabled }">
    <div class="param-header">
      <div class="param-info">
        <span class="param-label">{{ label }}</span>
        <span class="param-value">
          {{ displayValue }}{{ unit }}
        </span>
      </div>
      <el-button
        v-if="!disabled"
        text
        size="small"
        @click="resetValue"
      >
        <el-icon><RefreshLeft /></el-icon>
        重置
      </el-button>
    </div>

    <el-slider
      :model-value="modelValue"
      @update:model-value="handleUpdate"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      :show-tooltip="true"
      :format-tooltip="formatTooltip"
    />

    <div class="param-range" v-if="!disabled">
      <span class="range-min">{{ min }}{{ unit }}</span>
      <span class="range-desc" v-if="description">{{ description }}</span>
      <span class="range-max">{{ max }}{{ unit }}</span>
    </div>

    <div class="param-description" v-else-if="description">
      <el-icon><InfoFilled /></el-icon>
      {{ description }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { InfoFilled, RefreshLeft } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: number
    min: number
    max: number
    unit?: string
    step?: number
    disabled?: boolean
    description?: string
  }>(),
  {
    unit: '',
    step: 1,
    disabled: false,
    description: ''
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const displayValue = computed(() => {
  if (Number.isInteger(props.modelValue)) {
    return props.modelValue
  }
  return props.modelValue.toFixed(2)
})

function handleUpdate(value: number) {
  emit('update:modelValue', value)
}

function formatTooltip(value: number): string {
  return `${value}${props.unit}`
}

function resetValue() {
  // 重置为默认值（中间值）
  const defaultValue = (props.min + props.max) / 2
  emit('update:modelValue', defaultValue)
}
</script>

<style scoped lang="scss">
.param-slider {
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  transition: all 0.3s;

  &:hover {
    background: var(--el-fill-color-light);
  }

  &.is-disabled {
    opacity: 0.7;
  }

  .param-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .param-info {
      display: flex;
      align-items: baseline;
      gap: 8px;

      .param-label {
        font-size: 14px;
        font-weight: 500;
        color: var(--el-text-color-primary);
      }

      .param-value {
        font-size: 16px;
        font-weight: 600;
        color: var(--el-color-primary);
        font-family: 'Consolas', 'Monaco', monospace;
      }
    }

    .el-button {
      padding: 4px 8px;
      font-size: 12px;
    }
  }

  .param-range {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 8px;
    font-size: 12px;
    color: var(--el-text-color-secondary);

    .range-desc {
      flex: 1;
      text-align: center;
      padding: 0 12px;
    }
  }

  .param-description {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    padding: 6px 12px;
    background: var(--el-fill-color-blank);
    border-radius: 4px;

    .el-icon {
      color: var(--el-color-info);
      font-size: 14px;
    }
  }

  :deep(.el-slider__runway) {
    height: 6px;
  }

  :deep(.el-slider__button) {
    width: 16px;
    height: 16px;
  }
}
</style>
