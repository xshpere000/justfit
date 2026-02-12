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
                <el-checkbox v-model="isAllSelected" @change="handleSelectAll" label="选择本页所有" border size="small" />
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
                         :class="{ selected: selectedVMs.has(vm.name) }"
                         @click="toggleVM(vm.name)">
                       <div class="vm-status-dot" :class="vm.power_state === 'poweredOn' ? 'on' : 'off'"></div>
                       <div class="vm-info">
                          <div class="vm-name" :title="vm.name">{{ vm.name }}</div>
                          <div class="vm-spec">
                            {{ vm.cpu_count > 0 ? vm.cpu_count + ' vCPU' : 'CPU: -' }}
                            /
                            {{ vm.memory_mb > 0 ? formatMemory(vm.memory_mb) : '内存: 未获取' }}
                          </div>
                       </div>
                       <div class="vm-check">
                          <el-icon v-if="selectedVMs.has(vm.name)"><Check /></el-icon>
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
import { Monitor, Connection, Search, Check, Flag, ArrowLeft } from '@element-plus/icons-vue'

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

function handleSelectAll(val: boolean) {
    const pageVMs = filteredVMs.value
    if (val) {
        pageVMs.forEach(vm => selectedVMs.value.add(vm.name))
    } else {
        pageVMs.forEach(vm => selectedVMs.value.delete(vm.name))
    }
}

function toggleVM(name: string) {
    if (selectedVMs.value.has(name)) {
        selectedVMs.value.delete(name)
    } else {
        selectedVMs.value.add(name)
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
     const task = taskStore.createTask({
        type: 'collection',
        name: '评估任务-' + connectionForm.name,
        platform: formData.platform,
        connectionId: createdConnectionId.value,
        connectionName: connectionForm.name,
        selectedVMs: Array.from(selectedVMs.value),
        totalVMs: selectedVMs.value.size
     })

     taskStore.startCollectionTask(task.id, createdConnectionId.value, 30)

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

        .vm-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #dcdfe6;
            margin-right: 12px;
            &.on { background: #67c23a; }
        }

        .vm-info {
            flex: 1;
            overflow: hidden;

            .vm-name { font-size: 14px; font-weight: 500; color: #303133; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .vm-spec { font-size: 12px; color: #909399; }
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
