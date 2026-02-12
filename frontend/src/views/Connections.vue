<template>
  <div class="connections-page">
    <el-card class="action-card">
      <div class="action-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索连接名称"
          :prefix-icon="Search"
          style="width: 300px"
          clearable
        />
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">
          添加连接
        </el-button>
      </div>
    </el-card>

    <el-card class="list-card">
      <el-table
        :data="filteredConnections"
        :loading="connectionStore.loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="连接名称" min-width="180" />
        <el-table-column prop="platform" label="平台类型" width="150">
          <template #default="{ row }">
            <el-tag :type="row.platform === 'vcenter' ? 'primary' : 'success'">
              {{ row.platform === 'vcenter' ? 'VMware vCenter' : 'H3C UIS' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="服务器地址" min-width="200">
          <template #default="{ row }">
            {{ row.host }}:{{ row.port }}
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync" label="最后同步" width="180">
          <template #default="{ row }">
            {{ row.last_sync || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :loading="testingIds.has(row.id)" @click="handleTest(row.id)">
              测试连接
            </el-button>
            <el-button link type="primary" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button link type="danger" @click="handleDelete(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!connectionStore.loading && connectionStore.connections.length === 0"
        description="暂无连接，点击上方按钮添加"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑连接' : '添加连接'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="连接名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入连接名称" clearable />
        </el-form-item>
        <el-form-item label="平台类型" prop="platform">
          <el-select v-model="formData.platform" placeholder="请选择平台类型" style="width: 100%">
            <el-option label="VMware vCenter" value="vcenter" />
            <el-option label="H3C UIS" value="h3c-uis" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务器地址" prop="host">
          <el-input v-model="formData.host" placeholder="请输入服务器地址" clearable />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="formData.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="formData.password" type="password" show-password placeholder="请输入密码" clearable />
        </el-form-item>
        <el-form-item label="SSL验证">
          <el-switch v-model="formData.insecure" active-text="跳过验证" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useConnectionStore } from '@/stores/connection'
import * as ConnectionAPI from '@/api/connection'

const connectionStore = useConnectionStore()

const searchText = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const testingIds = ref(new Set<number>())
const formRef = ref<FormInstance>()

const formData = reactive({
  id: 0,
  name: '',
  platform: 'vcenter' as 'vcenter' | 'h3c-uis',
  host: '',
  port: 443,
  username: '',
  password: '',
  insecure: false
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入连接名称', trigger: 'blur' }],
  platform: [{ required: true, message: '请选择平台类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入服务器地址', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const filteredConnections = computed(() => {
  if (!searchText.value) {
    return connectionStore.connections
  }
  const search = searchText.value.toLowerCase()
  return connectionStore.connections.filter(
    (c: any) =>
      c.name.toLowerCase().includes(search) ||
      c.host.toLowerCase().includes(search)
  )
})

connectionStore.fetchConnections()

function openCreateDialog() {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(conn: any) {
  isEdit.value = true
  Object.assign(formData, {
    id: conn.id,
    name: conn.name,
    platform: conn.platform,
    host: conn.host,
    port: conn.port,
    username: conn.username,
    password: '',
    insecure: conn.insecure
  })
  dialogVisible.value = true
}

function resetForm() {
  Object.assign(formData, {
    id: 0,
    name: '',
    platform: 'vcenter' as 'vcenter' | 'h3c-uis',
    host: '',
    port: 443,
    username: '',
    password: '',
    insecure: false
  })
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (isEdit.value && formData.id) {
      await ConnectionAPI.updateConnection({
        id: formData.id,
        name: formData.name,
        platform: formData.platform,
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password || '',
        insecure: formData.insecure
      })
      ElMessage.success('连接更新成功')
    } else {
      await ConnectionAPI.createConnection({
        name: formData.name,
        platform: formData.platform,
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password,
        insecure: formData.insecure
      })
      ElMessage.success('连接创建成功')
    }
    dialogVisible.value = false
    await connectionStore.fetchConnections()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleTest(id: number) {
  testingIds.value.add(id)
  try {
    const result = await ConnectionAPI.testConnection(id)
    ElMessage.success('连接测试成功: ' + result)
    await connectionStore.fetchConnections()
  } catch (error: any) {
    ElMessage.error(error.message || '连接测试失败')
  } finally {
    testingIds.value.delete(id)
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除该连接吗？', '提示', {
      type: 'warning'
    })
    await ConnectionAPI.deleteConnection(id)
    ElMessage.success('删除成功')
    await connectionStore.fetchConnections()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function getStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    connected: 'success',
    disconnected: 'info',
    error: 'danger',
    connecting: 'warning'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status: string): string {
  const textMap: Record<string, string> = {
    connected: '已连接',
    disconnected: '未连接',
    error: '连接失败',
    connecting: '连接中'
  }
  return textMap[status] || status
}
</script>

<style scoped lang="scss">
.connections-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);

  .action-card {
    .action-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .list-card {
    flex: 1;
  }
}
</style>
