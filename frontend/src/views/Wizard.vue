<template>
  <div class="wizard-page">
    <div class="wizard-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-button icon="ArrowLeft" circle plain @click="$router.push('/')" size="small" style="margin-right: 12px" />
          创建评估任务
        </h1>
        <el-steps :active="currentStep" simple style="flex: 1; max-width: 1000px; margin-left: 40px; background: transparent">
           <el-step title="选择平台" icon="Monitor" />
           <el-step title="配置连接" icon="Connection" />
           <el-step title="选择虚拟机" icon="Search" />
           <el-step title="开始确认" icon="Flag" />
        </el-steps>
      </div>
    </div>

    <div class="wizard-body">
      <!-- 步骤1：选择平台 -->
      <div v-show="currentStep === 0" class="step-panel">
        <h2 class="section-title">请选择目标云平台</h2>
        <div class="platform-list">
           <div class="platform-item"
                :class="{ active: formData.platform === 'vcenter' }"
                @click="selectPlatform('vcenter')">
              <div class="item-icon"><el-icon><Monitor /></el-icon></div>
              <div class="item-info">
                  <h3>VMware vSphere</h3>
                  <p>适用于 vCenter 6.0 及以上版本</p>
              </div>
              <div class="item-check" v-if="formData.platform === 'vcenter'"><el-icon><Check /></el-icon></div>
           </div>

           <div class="platform-item"
                :class="{ active: formData.platform === 'h3c-uis' }"
                @click="selectPlatform('h3c-uis')">
              <div class="item-icon"><el-icon><Connection /></el-icon></div>
              <div class="item-info">
                  <h3>H3C UIS</h3>
                  <p>适用于 H3C UIS 超融合 7.0 及以上版本</p>
              </div>
              <div class="item-check" v-if="formData.platform === 'h3c-uis'"><el-icon><Check /></el-icon></div>
           </div>
        </div>
      </div>

      <!-- 步骤2：连接配置 -->
      <div v-show="currentStep === 1" class="step-panel" style="max-width: 600px; margin: 0 auto;">
         <h2 class="section-title">填写连接信息</h2>
         <el-form :model="connectionForm" :rules="connectionRules" ref="connectionFormRef" label-position="top" size="large" class="conn-form">
            <el-form-item label="连接名称" prop="name">
               <el-input v-model="connectionForm.name" placeholder="例如：生产环境集群" />
            </el-form-item>
            <el-row :gutter="20">
               <el-col :span="16">
                  <el-form-item label="主机地址" prop="host">
                     <el-input v-model="connectionForm.host" placeholder="IP 地址或域名" />
                  </el-form-item>
               </el-col>
               <el-col :span="8">
                  <el-form-item label="端口" prop="port">
                     <el-input-number v-model="connectionForm.port" :min="1" :max="65535" style="width: 100%" />
                  </el-form-item>
               </el-col>
            </el-row>
            <el-form-item label="用户名" prop="username">
               <el-input v-model="connectionForm.username" placeholder="管理员账号" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
               <el-input v-model="connectionForm.password" type="password" show-password placeholder="管理员密码" />
            </el-form-item>
         </el-form>
      </div>

      <!-- 步骤3：选择虚拟机 -->
       <div v-show="currentStep === 2" class="step-panel flex-panel">
          <div class="panel-header">
             <div class="header-left">
                <el-input v-model="vmSearchQuery" placeholder="搜索虚拟机名称..." prefix-icon="Search" style="width: 280px" clearable />
             </div>
             <div class="header-right">
                <span style="color: #606266; font-size: 13px; margin-right: 12px">已选择 {{ selectedVMs.size }} 台</span>
                <el-checkbox v-model="isAllSelected" @change="handleSelectAll" label="选择本页所有" border size="small" style="margin-right: 8px" />
                <el-button :icon="Refresh" @click="refreshVMList" :loading="vmLoading" link>刷新列表</el-button>
             </div>
          </div>

          <div class="vm-list-container">
             <el-scrollbar v-loading="vmLoading">
                 <div v-if="vmListLoaded && filteredVMs.length === 0" class="empty-list">
                    <el-empty description="未找到匹配的虚拟机" :image-size="80" />
                 </div>
                 <div class="vm-grid" v-else>
                    <div v-for="vm in filteredVMs" :key="vm.uuid || vm.id"
                         class="vm-item"
                         :class="{
                           selected: selectedVMs.has(getVMKey(vm)),
                           'state-warning': !isVMStateNormal(vm)
                         }"
                         @click="toggleVM(vm)">
                       <div class="vm-status-dot" :class="getVMStateDotClass(vm)"></div>
                       <div class="vm-info">
                          <div class="vm-name" :title="vm.name">{{ vm.name }}</div>
                          <div class="vm-spec">
                            {{ vm.cpu_count > 0 ? vm.cpu_count + ' vCPU' : 'CPU: -' }}
                            /
                            {{ vm.memory_mb > 0 ? formatMemory(vm.memory_mb) : '内存: 未获取' }}
                          </div>
                       </div>
                       <div class="vm-state-badge" v-if="!isVMStateNormal(vm)">
                          {{ getVMStateText(vm) }}
                       </div>
                       <div class="vm-check">
                          <el-icon v-if="selectedVMs.has(getVMKey(vm))"><Check /></el-icon>
                       </div>
                    </div>
                 </div>
             </el-scrollbar>
          </div>

          <div class="panel-pagination">
             <el-pagination
                v-model:current-page="pagination.page"
                v-model:page-size="pagination.pageSize"
                :total="vmList.length"
                :page-sizes="[50, 100, 200]"
                layout="total, sizes, prev, pager, next"
                background />
          </div>
       </div>

       <!-- 步骤4：确认 -->
       <div v-show="currentStep === 3" class="step-panel" style="max-width: 700px; margin: 0 auto;">
          <h2 class="section-title">任务概览确认</h2>
          <div class="confirm-card">
              <el-descriptions :column="1" border size="large">
                 <el-descriptions-item label="任务类型">
                    <el-tag>{{ formData.platform === 'vcenter' ? 'vCenter 集群评估' : 'H3C UIS 评估' }}</el-tag>
                 </el-descriptions-item>
                 <el-descriptions-item label="连接地址">
                    <span style="font-family: monospace">{{ connectionForm.host }}:{{ connectionForm.port }}</span>
                 </el-descriptions-item>
                 <el-descriptions-item label="接入账户">
                    {{ connectionForm.username }}
                 </el-descriptions-item>
                 <el-descriptions-item label="评估对象">
                    <span style="color: #409EFF; font-weight: bold">{{ selectedVMs.size }}</span> 台虚拟机
                 </el-descriptions-item>
              </el-descriptions>
          </div>
          <p style="text-align: center; color: #909399; margin-top: 20px; font-size: 13px;">点击"开始评估"后，系统将自动采集性能数据并生成分析报告。</p>
       </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="wizard-footer">
       <el-button v-if="currentStep > 0" @click="prevStep" size="large">上一步</el-button>
       <div class="footer-right">
          <el-button @click="handleCancel" size="large">取消</el-button>

          <el-button v-if="currentStep === 1" type="primary" size="large" :loading="testLoading" @click="testConnection">
             测试并继续
          </el-button>
          <el-button v-else-if="currentStep < 3" type="primary" size="large" @click="nextStep">
             下一步
          </el-button>
          <el-button v-else type="success" size="large" :loading="submitLoading" @click="submitTask">
             开始评估
          </el-button>
       </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore, type CreateTaskParams } from '@/stores/task'
import * as ConnectionAPI from '@/api/connection'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Monitor, Connection, Search, Check, Flag, ArrowLeft, Refresh } from '@element-plus/icons-vue'

defineOptions({
  name: 'Wizard'
})

const router = useRouter()
const taskStore = useTaskStore()

// State
const currentStep = ref(0)
const submitLoading = ref(false)
const testLoading = ref(false)
const vmLoading = ref(false)
const vmListLoaded = ref(false)
const createdConnectionId = ref<number>(0)

const formData = reactive({
  platform: 'vcenter',
})

const connectionFormRef = ref<FormInstance>()
const connectionForm = reactive({
  name: '',
  host: '',
  port: 443,
  username: '',
  password: ''
})

const connectionRules = {
  name: [{ required: true, message: '请输入连接名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// VM List
const vmList = ref<any[]>([])
const selectedVMs = ref<Set<string>>(new Set())
const vmSearchQuery = ref('')
const isAllSelected = ref(false)
const pagination = reactive({
  page: 1,
  pageSize: 50
})

// Computeds
const filteredVMs = computed(() => {
  let list = vmList.value

  if (vmSearchQuery.value) {
    const q = vmSearchQuery.value.toLowerCase()
    list = list.filter(vm => vm.name.toLowerCase().includes(q))
  }

  const start = (pagination.page - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  return list.slice(start, end)
})

// Methods
function selectPlatform(type: string) {
  formData.platform = type
  if (type === 'vcenter') {
    connectionForm.port = 443
  } else {
    connectionForm.port = 443
  }
  nextStep()
}

function nextStep() {
  if (currentStep.value === 1) {
    if (!vmListLoaded.value) {
        ElMessage.warning('请先点击"测试并继续"以验证连接')
        return
    }
  }
  if (currentStep.value === 2) {
    if (selectedVMs.value.size === 0) {
        ElMessage.warning('请至少选择一台虚拟机')
        return
    }
  }

  if (currentStep.value < 3) currentStep.value++
}

function prevStep() {
  if (currentStep.value > 0) currentStep.value--
}

async function testConnection() {
  if (!connectionFormRef.value) return

  try {
    await connectionFormRef.value.validate()
  } catch {
    return
  }

  testLoading.value = true
  try {
    // 1. 创建连接
    const connId = await ConnectionAPI.ConnectionApi.create({
      name: connectionForm.name,
      platform: formData.platform,
      host: connectionForm.host,
      port: connectionForm.port,
      username: connectionForm.username,
      password: connectionForm.password,
      insecure: false
    })

    createdConnectionId.value = connId
    ElMessage.success('连接成功，正在获取资源列表...')

    // 2. 采集数据
    await ConnectionAPI.CollectionApi.collect({
      connection_id: connId,
      data_types: ['clusters', 'hosts', 'vms'],
      metrics_days: 30
    })

    // 3. 获取虚拟机列表
    await fetchVMList(connId)

    currentStep.value++
  } catch (e: any) {
    ElMessage.error(e.message || '连接失败')
  } finally {
    testLoading.value = false
  }
}

async function fetchVMList(connId: number) {
    vmLoading.value = true
    try {
        const result = await ConnectionAPI.ResourceApi.getVMList(connId)
        vmList.value = result.vms
        vmListLoaded.value = true
    } catch(e) {
        console.error(e)
        vmList.value = []
    } finally {
        vmLoading.value = false
    }
}

// 刷新虚拟机列表
async function refreshVMList() {
    if (!createdConnectionId.value) {
        ElMessage.warning('请先建立连接')
        return
    }

    try {
        await fetchVMList(createdConnectionId.value)
        ElMessage.success('虚拟机列表已刷新')
    } catch (e: any) {
        ElMessage.error('刷新失败: ' + (e.message || '未知错误'))
    }
}

// 获取虚拟机的唯一标识，必须与后端 buildVMKey 函数的格式一致
// 后端 buildVMKey 逻辑：
//   - 如果有 UUID，返回 "uuid:" + lowercase(uuid)
//   - 否则如果有 datacenter，返回 "datacenter:name"
//   - 否则返回 name
function getVMKey(vm: any): string {
    // 优先使用 UUID，与后端保持一致
    if (vm.uuid && vm.uuid.trim() !== '') {
        return 'uuid:' + vm.uuid.trim().toLowerCase()
    }
    // 如果有 datacenter，使用 datacenter:name 格式
    if (vm.datacenter && vm.datacenter.trim() !== '') {
        return vm.datacenter.trim() + ':' + (vm.name || '').trim()
    }
    // 最后使用 name
    return (vm.name || '').trim()
}

// ==================== 虚拟机状态判断 ====================

// 正常连接状态
const NORMAL_CONNECTION_STATES = new Set([
    'connected',     // 正常连接
    ''               // 空字符串（H3C UIS 可能没有此字段）
])

// 正常电源状态列表（支持扩展）
const NORMAL_VM_STATES = new Set([
    // VMware vCenter 状态（全部小写存储）
    'poweredon',      // 开机
    'poweredoff',     // 关机
    'suspended',      // 挂起

    // H3C UIS 状态（全部小写存储）
    'running',        // 运行中（对应 vCenter 的 poweredOn）
    'stopped',        // 已停止（对应 vCenter 的 poweredOff）
    'on',             // 开机
    'off',            // 关机
    'shutdown'        // 已关机
])

// 异常状态映射表（支持扩展）
const VM_STATE_TEXT_MAP: Record<string, string> = {
    // VMware vCenter 状态
    'orphaned': '孤立',
    'inaccessible': '无法访问',
    'disconnected': '已断开',
    'notResponding': '无响应',
    'unknown': '未知状态',
    'invalid': '无效',
    'wait': '等待中',
    'blocked': '已阻塞',

    // H3C UIS 状态
    'isolated': '孤立',
    'lost': '丢失',
    'error': '错误',
    'migrating': '迁移中',
    'creating': '创建中',
    'deleting': '删除中',
    'rebooting': '重启中'
}

/**
 * 获取虚拟机的实际显示状态
 * 优先使用连接状态（如果异常），否则使用电源状态
 * @param vm 虚拟机对象
 * @returns 实际应该显示的状态字符串
 */
function getVMActualState(vm: any): string {
    // 如果有连接状态且不是正常连接，返回连接状态
    const connectionState = vm.connection_state || ''
    if (connectionState && !NORMAL_CONNECTION_STATES.has(connectionState.toLowerCase())) {
        return connectionState
    }
    // 否则返回电源状态
    return vm.power_state || ''
}

/**
 * 判断虚拟机状态是否正常
 * @param vm 虚拟机对象
 * @returns true=正常状态，false=异常状态
 */
function isVMStateNormal(vm: any): boolean {
    // 检查连接状态
    const connectionState = (vm.connection_state || '').toLowerCase()
    if (connectionState && !NORMAL_CONNECTION_STATES.has(connectionState)) {
        console.log(`[VM State] 虚拟机 "${vm.name}" 连接状态异常: ${vm.connection_state}`)
        return false
    }

    // 检查电源状态
    const powerState = vm.power_state || ''
    if (!powerState) {
        console.warn(`[VM State] 虚拟机 "${vm.name}" 空电源状态，判定为异常`)
        return false
    }

    const state = powerState.toLowerCase()
    const isNormal = NORMAL_VM_STATES.has(state)
    if (!isNormal) {
        console.log(`[VM State] 虚拟机 "${vm.name}" 未知电源状态: "${powerState}"，判定为异常`)
    }
    return isNormal
}

/**
 * 获取虚拟机状态的显示文本
 * @param vm 虚拟机对象
 * @returns 状态显示文本
 */
function getVMStateText(vm: any): string {
    const actualState = getVMActualState(vm)
    if (!actualState) return '未知'

    const state = actualState.toLowerCase()

    // 先检查是否是已知异常状态
    if (VM_STATE_TEXT_MAP[state]) {
        return VM_STATE_TEXT_MAP[state]
    }

    // 如果不是正常状态也不是已知异常状态，返回原始值
    if (!isVMStateNormal(vm)) {
        return actualState
    }

    // 正常状态不需要显示标签
    return ''
}

/**
 * 获取虚拟机状态指示点的样式类
 * @param vm 虚拟机对象
 * @returns 样式类名
 */
function getVMStateDotClass(vm: any): string {
    const actualState = getVMActualState(vm)
    if (!actualState) return 'unknown'

    const state = actualState.toLowerCase()

    // 开机状态（包括 H3C UIS 的 running）
    if (state === 'poweredon' || state === 'on' || state === 'running') {
        return 'on'
    }

    // 关机状态（包括 H3C UIS 的 stopped）
    if (state === 'poweredoff' || state === 'off' || state === 'shutdown' || state === 'stopped') {
        return 'off'
    }

    // 挂起状态
    if (state === 'suspended') {
        return 'paused'
    }

    // 异常状态使用警告色
    return 'warning'
}

// ==================== 虚拟机选择 ====================

function toggleVM(vm: any) {
    // 检查虚拟机状态，异常状态不允许选择
    if (!isVMStateNormal(vm)) {
        ElMessage.warning({
            message: `虚拟机 "${vm.name}" 状态异常（${getVMStateText(vm)}），无法评估`,
            duration: 3000
        })
        return
    }

    const key = getVMKey(vm)
    if (selectedVMs.value.has(key)) {
        selectedVMs.value.delete(key)
    } else {
        selectedVMs.value.add(key)
    }
}

function handleSelectAll(val: boolean) {
    const pageVMs = filteredVMs.value
    // 只选择状态正常的虚拟机
    const normalVMs = pageVMs.filter(vm => isVMStateNormal(vm))

    if (val) {
        normalVMs.forEach(vm => selectedVMs.value.add(getVMKey(vm)))
    } else {
        pageVMs.forEach(vm => selectedVMs.value.delete(getVMKey(vm)))
    }
}

function formatMemory(value: number | undefined) {
    if (!value) return '-'
    // 后端 GetVMList 返回的 memory_mb 字段，单位是 MB
    // 转换为 GB 显示
    if (value >= 1024) return (value / 1024).toFixed(1) + ' GB'
    return value + ' MB'
}

async function submitTask() {
  submitLoading.value = true
  try {
     console.log('[Wizard.submitTask] 开始创建任务')
     console.log('[Wizard.submitTask] selectedVMs.value:', selectedVMs.value)
     console.log('[Wizard.submitTask] selectedVMs.value类型:', typeof selectedVMs.value)
     console.log('[Wizard.submitTask] selectedVMs.value.size:', selectedVMs.value?.size)
     console.log('[Wizard.submitTask] Array.from(selectedVMs.value):', Array.from(selectedVMs.value || []))

     const task = taskStore.createTask({
        type: 'collection',
        name: '评估任务-' + connectionForm.name,
        platform: formData.platform,
        connectionId: createdConnectionId.value,
        connectionName: connectionForm.name,
        selectedVMs: Array.from(selectedVMs.value),
        totalVMs: selectedVMs.value.size
     })

     taskStore.startCollectionTask(task.id, createdConnectionId.value, Array.from(selectedVMs.value), 30)

     ElMessage.success('任务已创建，后台正在采集中...')
     router.push('/')
  } catch (e: any) {
     ElMessage.error(e.message || '创建失败')
  } finally {
     submitLoading.value = false
  }
}

function handleCancel() {
    ElMessageBox.confirm('确定放弃当前配置吗？', '提示', { type: 'warning' })
    .then(() => router.push('/'))
    .catch(() => {})
}
</script>

<style scoped lang="scss">
.wizard-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
}

.wizard-header {
  flex: 0 0 auto;
  padding: 24px 40px;
  background: white;
  border-bottom: 1px solid #f0f2f5;

  .header-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;

    :deep(.el-step.is-simple .el-step__title) {
       white-space: nowrap;
       font-size: 15px;
    }
  }

  .page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    display: flex;
    align-items: center;
  }
}

.wizard-body {
  flex: 1;
  padding: 40px;
  overflow-y: auto;
  background: white;

  .step-panel {
    max-width: 1200px;
    margin: 0 auto;
    background: white;

    .section-title {
        font-size: 24px;
        text-align: center;
        margin-bottom: 60px;
        color: #303133;
        font-weight: 600;
    }

    &.flex-panel {
        display: flex;
        flex-direction: column;
        height: 100%;
        max-height: 100%;
    }
  }
}

/* Platform List Styles */
.platform-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-width: 600px;
    margin: 0 auto;

    .platform-item {
        display: flex;
        align-items: center;
        padding: 24px;
        border:1px solid #e4e7ed;
        border-radius: 12px;
        background: white;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
        position: relative;

        &:hover {
            border-color: #c6e2ff;
            background-color: #fdfdfd;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }

        &.active {
            border-color: #409eff;
            background-color: #f0f9eb;

            .item-icon { color: #409eff; background: #ecf5ff; }
        }

        .item-icon {
            width: 56px;
            height: 56px;
            border-radius: 8px;
            background: #f2f6fc;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            color: #909399;
            margin-right: 20px;
            transition: all 0.2s;
        }

        .item-info {
            flex: 1;
            h3 { margin: 0 0 6px 0; font-size: 18px; color: #303133; }
            p { margin: 0; font-size: 14px; color: #909399; }
        }

        .item-check {
            color: #409eff;
            font-size: 24px;
            font-weight: bold;
        }
    }
}

/* VM List Styles */
.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex: 0 0 auto;
}

.vm-list-container {
    flex: 1;
    border:1px solid #e4e7ed;
    border-radius: 4px;
    background: #fff;
    overflow: hidden;

    .vm-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 12px;
        padding: 12px;
    }

    .vm-item {
        border:1px solid #ebeef5;
        border-radius: 6px;
        padding: 12px;
        display: flex;
        align-items: center;
        cursor: pointer;
        transition: all 0.2s;
        position: relative;

        &:hover { border-color: #c6e2ff; background: #fdfdfd; }
        &.selected {
            border-color: #409eff;
            background: #ecf5ff;
            .vm-check { opacity: 1; }
        }

        // 异常状态样式
        &.state-warning {
            background: #fef9e7;  // 淡黄色背景
            border-color: #e6c48c;  // 深黄色边框
            cursor: not-allowed;

            &:hover {
                background: #fef9e7;
                border-color: #e6c48c;
            }

            .vm-name {
                color: #e6a23c;  // 橙黄色文字
            }
        }

        .vm-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #dcdfe6;
            margin-right: 12px;
            flex-shrink: 0;

            &.on { background: #67c23a; }
            &.off { background: #909399; }
            &.paused { background: #409eff; }
            &.warning { background: #e6a23c; }  // 异常状态：橙色
            &.unknown { background: #f56c6c; }  // 未知状态：红色
        }

        .vm-info {
            flex: 1;
            overflow: hidden;

            .vm-name { font-size: 14px; font-weight: 500; color: #303133; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .vm-spec { font-size: 12px; color: #909399; }
        }

        // 异常状态标签
        .vm-state-badge {
            position: absolute;
            top: 6px;
            right: 6px;
            padding: 2px 6px;
            background: rgba(230, 162, 60, 0.15);
            color: #e6a23c;
            font-size: 11px;
            border-radius: 3px;
            border: 1px solid rgba(230, 162, 60, 0.3);
        }

        .vm-check {
            color: #409eff;
            opacity: 0;
            transition: opacity 0.2s;
        }
    }

    .empty-list {
        padding: 40px;
        text-align: center;
    }
}

.panel-pagination {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
    flex: 0 0 auto;
}

/* Footer Styles */
.wizard-footer {
    flex: 0 0 auto;
    background: white;
    border-top: 1px solid #e4e7ed;
    padding: 20px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .footer-right {
        margin-left: auto;
        display: flex;
        gap: 12px;
    }
}
</style>
