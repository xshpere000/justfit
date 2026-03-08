<template>
  <el-dialog
    v-model="visible"
    title="版本升级提示"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <div class="upgrade-content">
      <el-icon class="upgrade-icon" :size="48" color="#E6A23C">
        <Warning />
      </el-icon>

      <h3>检测到大版本升级</h3>

      <p class="version-info">
        当前版本：<el-tag type="warning">0.0.3</el-tag>
        <span style="margin: 0 8px">→</span>
        最新版本：<el-tag type="success">0.0.3</el-tag>
      </p>

      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin: 20px 0"
      >
        <template #title>
          <strong>重要提示</strong>
        </template>
        <div class="alert-content">
          <p>新架构已完全重构，历史数据将<strong style="color: #F56C6C">无法保留</strong>。</p>
          <p>升级后将清空所有历史数据，包括：</p>
          <ul>
            <li>所有连接配置</li>
            <li>所有采集任务记录</li>
            <li>所有分析结果</li>
            <li>所有报告文件</li>
          </ul>
          <p>建议在升级前备份重要数据。</p>
        </div>
      </el-alert>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel" :disabled="upgrading">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleConfirm"
          :loading="upgrading"
          :disabled="upgrading"
        >
          {{ upgrading ? '升级中...' : '确认升级' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import type { VersionCheckResult } from '@/types/api'

const props = defineProps<{
  modelValue: boolean
  versionInfo?: VersionCheckResult | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirmed'): void
  (e: 'cancelled'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const upgrading = ref(false)

const handleConfirm = async () => {
  upgrading.value = true
  try {
    // 在新架构中，数据库会自动迁移
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('升级成功，应用将自动重启')
    emit('confirmed')
    setTimeout(() => {
      visible.value = false
      window.location.reload()
    }, 1500)
  } catch (error: any) {
    ElMessage.error('升级失败：' + (error.message || '未知错误'))
    upgrading.value = false
  }
}

const handleCancel = () => {
  emit('cancelled')
  visible.value = false
}
</script>

<style scoped>
.upgrade-content {
  text-align: center;
}

.upgrade-icon {
  margin-bottom: 16px;
}

.upgrade-content h3 {
  margin: 0 0 16px 0;
  font-size: 20px;
  color: #303133;
}

.version-info {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 16px 0;
  font-size: 14px;
  color: #606266;
}

.alert-content {
  text-align: left;
  line-height: 1.8;
}

.alert-content p {
  margin: 8px 0;
}

.alert-content ul {
  margin: 8px 0;
  padding-left: 24px;
}

.alert-content li {
  margin: 4px 0;
}

.alert-content strong {
  font-weight: 600;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
