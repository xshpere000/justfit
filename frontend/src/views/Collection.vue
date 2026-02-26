<template>
  <div class="collection-page">
    <!-- 采集配置 -->
    <el-card class="config-card">
      <template #header>
        <span>数据采集配置</span>
      </template>

      <el-form
        ref="formRef"
        :model="config"
        label-width="120px"
        label-position="left"
      >
        <el-row :gutter="20">
          <el-col :span="12">
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
                  :disabled="conn.status !== 'connected'"
                >
                  <span>{{ conn.name }}</span>
                  <el-tag
                    :type="getConnectionStatusType(conn.status)"
                    size="small"
                    style="margin-left: 8px"
                  >
                    {{ getConnectionStatusText(conn.status) }}
                  </el-tag>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="采集天数">
              <el-input-number
                v-model="config.metricsDays"
                :min="1"
                :max="90"
                style="width: 100%"
              />
              <span class="form-tip">最多采集 90 天的历史数据</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="数据类型">
          <el-checkbox-group v-model="config.dataTypes">
            <el-checkbox label="clusters">集群信息</el-checkbox>
            <el-checkbox label="hosts">主机信息</el-checkbox>
            <el-checkbox label="vms">虚拟机信息</el-checkbox>
            <el-checkbox label="metrics">性能指标</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 采集控制 -->
    <el-card class="control-card">
      <div class="control-buttons">
        <el-button
          type="primary"
          :icon="'Play'"
          :disabled="!canStart"
          :loading="collecting"
          @click="handleStart"
        >
          {{ collecting ? '采集中...' : '开始采集' }}
        </el-button>
        <el-button
          :icon="'Refresh'"
          :disabled="!canStart"
          @click="handleRefresh"
        >
          刷新连接状态
        </el-button>
      </div>

      <!-- 采集进度 -->
      <div v-if="collecting || progress" class="progress-section">
        <el-progress
          :percentage="progressPercent"
          :status="progressStatus"
        >
          <span class="progress-text">{{ progressText }}</span>
        </el-progress>
      </div>
    </el-card>

    <!-- 采集结果 -->
    <el-card v-if="result" class="result-card">
      <template #header>
        <span>采集结果</span>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="状态">
          <el-tag :type="result.success ? 'success' : 'danger'">
            {{ result.success ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="耗时">
          {{ formatDuration(result.duration) }}
        </el-descriptions-item>
        <el-descriptions-item label="集群数量">
          {{ result.clusters }}
        </el-descriptions-item>
        <el-descriptions-item label="主机数量">
          {{ result.hosts }}
        </el-descriptions-item>
        <el-descriptions-item label="虚拟机数量">
          {{ result.vms }}
        </el-descriptions-item>
        <el-descriptions-item label="指标数据">
          {{ formatNumber(result.metrics) }}
        </el-descriptions-item>
        <el-descriptions-item label="消息" :span="2">
          {{ result.message }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 数据预览 -->
    <el-card v-if="result && result.success" class="preview-card">
      <template #header>
        <div class="card-header">
          <span>数据预览</span>
          <el-button-group>
            <el-button
              :type="previewTab === 'clusters' ? 'primary' : ''"
              size="small"
              @click="previewTab = 'clusters'"
            >
              集群
            </el-button>
            <el-button
              :type="previewTab === 'hosts' ? 'primary' : ''"
              size="small"
              @click="previewTab = 'hosts'"
            >
              主机
            </el-button>
            <el-button
              :type="previewTab === 'vms' ? 'primary' : ''"
              size="small"
              @click="previewTab = 'vms'"
            >
              虚拟机
            </el-button>
          </el-button-group>
        </div>
      </template>

      <el-table
        v-loading="previewLoading"
        :data="previewData"
        stripe
        max-height="400"
      >
        <el-table-column
          v-for="col in previewColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.width"
        />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection'
import { collectData, getClusterListRaw, getHostListRaw, getVMList } from '@/api/connection'
import type { CollectionConfig, CollectionResult, ClusterListItem, HostListItem, VMListItem } from '@/api/connection'
import {
  formatDuration,
  formatNumber,
  getConnectionStatusType,
  getConnectionStatusText
} from '@/utils/format'

const connectionStore = useConnectionStore()

const config = reactive<CollectionConfig>({
  connectionId: 0,
  dataTypes: ['clusters', 'hosts', 'vms', 'metrics'],
  metricsDays: 7
})

const collecting = ref(false)
const progress = ref(0)
const result = ref<CollectionResult | null>(null)
const previewTab = ref<'clusters' | 'hosts' | 'vms'>('clusters')
const previewLoading = ref(false)
const previewData = ref<any[]>([])

const canStart = computed(() => {
  return (
    config.connectionId > 0 &&
    config.dataTypes.length > 0 &&
    !collecting.value
  )
})

const progressPercent = computed(() => {
  return progress.value
})

const progressStatus = computed(() => {
  if (result.value) {
    return result.value.success ? 'success' : 'exception'
  }
  return undefined
})

const progressText = computed(() => {
  if (result.value) {
    return result.value.message
  }
  return collecting.value ? '采集中... ' + progress.value + '%' : ''
})

const previewColumns = computed(() => {
  const columnsMap: Record<string, any[]> = {
    clusters: [
      { prop: 'name', label: '名称', width: 150 },
      { prop: 'datacenter', label: '数据中心', width: 150 },
      { prop: 'totalCpu', label: 'CPU总量(MHz)', width: 120 },
      { prop: 'totalMemoryGb', label: '内存(GB)', width: 120 },
      { prop: 'numHosts', label: '主机数', width: 80 },
      { prop: 'numVMs', label: '虚拟机数', width: 100 },
      { prop: 'status', label: '状态', width: 100 }
    ],
    hosts: [
      { prop: 'name', label: '名称', width: 150 },
      { prop: 'datacenter', label: '数据中心', width: 150 },
      { prop: 'ipAddress', label: 'IP地址', width: 120 },
      { prop: 'cpuCores', label: 'CPU核数', width: 100 },
      { prop: 'memoryGb', label: '内存(GB)', width: 120 },
      { prop: 'numVMs', label: '虚拟机数', width: 100 },
      { prop: 'powerState', label: '电源状态', width: 100 }
    ],
    vms: [
      { prop: 'name', label: '名称', width: 200 },
      { prop: 'datacenter', label: '数据中心', width: 150 },
      { prop: 'hostName', label: '主机', width: 150 },
      { prop: 'cpuCount', label: 'CPU核数', width: 100 },
      { prop: 'memoryGb', label: '内存(GB)', width: 120 },
      { prop: 'ipAddress', label: 'IP地址', width: 120 },
      { prop: 'powerState', label: '电源状态', width: 100 }
    ]
  }
  return columnsMap[previewTab.value] || []
})

watch(previewTab, () => {
  loadPreviewData()
})

async function handleStart() {
  if (!config.connectionId) {
    ElMessage.warning('请选择连接')
    return
  }

  if (config.dataTypes.length === 0) {
    ElMessage.warning('请至少选择一种数据类型')
    return
  }

  collecting.value = true
  progress.value = 0
  result.value = null

  // 模拟进度
  const progressInterval = setInterval(() => {
    if (progress.value < 90) {
      progress.value += Math.random() * 10
    }
  }, 500)

  try {
    const res = await collectData(config)
    result.value = res
    progress.value = 100

    if (res.success) {
      ElMessage.success('采集完成！获取 ' + res.vms + ' 个虚拟机数据')
      // 自动加载预览数据
      loadPreviewData()
    } else {
      ElMessage.error(res.message || '采集失败')
    }
  } catch (error: any) {
    result.value = {
      success: false,
      message: error.message || '采集失败',
      clusters: 0,
      hosts: 0,
      vms: 0,
      metrics: 0,
      duration: 0
    }
    ElMessage.error(error.message || '采集失败')
  } finally {
    clearInterval(progressInterval)
    collecting.value = false
  }
}

async function handleRefresh() {
  await connectionStore.fetchConnections()
  ElMessage.success('连接状态已刷新')
}

async function loadPreviewData() {
  if (!config.connectionId) return

  previewLoading.value = true
  try {
    let dataStr = ''
    switch (previewTab.value) {
      case 'clusters':
        dataStr = await getClusterListRaw(config.connectionId)
        break
      case 'hosts':
        dataStr = await getHostListRaw(config.connectionId)
        break
      case 'vms':
        const vmResult = await getVMList(config.connectionId)
        previewData.value = vmResult.vms
        return
    }

    if (dataStr) {
      const parsedData = JSON.parse(dataStr)
      if (Array.isArray(parsedData)) {
        previewData.value = parsedData
      } else {
        previewData.value = []
      }
    } else {
      previewData.value = []
    }
  } catch (error: any) {
    console.error('Failed to load preview data:', error)
    ElMessage.error('加载预览数据失败')
  } finally {
    previewLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.collection-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);

  .form-tip {
    font-size: var(--font-size-small);
    color: var(--text-color-secondary);
    margin-left: var(--spacing-sm);
  }

  .control-card {
    .control-buttons {
      display: flex;
      gap: var(--spacing-md);
      margin-bottom: var(--spacing-lg);
    }

    .progress-section {
      .progress-text {
        margin-left: var(--spacing-sm);
      }
    }

    .preview-card {
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
    }
  }
}
</style>
