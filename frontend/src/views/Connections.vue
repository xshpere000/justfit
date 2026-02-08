<template>
  <div class="connections-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>平台连接管理</span>
          <el-button type="primary" :icon="'Plus'" @click="showCreateDialog">
            添加连接
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="connectionStore.loading"
        :data="connectionStore.connections"
        stripe
      >
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="platform" label="平台类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ PLATFORM_LABELS[row.platform] || row.platform }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机地址" min-width="180" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getConnectionStatusType(row.status)">
              {{ getConnectionStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync" label="最后连接" width="160">
          <template #default="{ row }">
            {{ row.last_sync ? formatDateTime(row.last_sync) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :loading="testingId === row.id"
              :disabled="row.status === 'connecting'"
              @click="handleTest(row.id)"
            >
              测试连接
            </el-button>
            <el-button size="small" :icon="'Edit'" @click="handleEdit(row)" />
            <el-popconfirm
              title="确定要删除这个连接吗？"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button
                  size="small"
                  type="danger"
                  :icon="'Delete'"
                  :disabled="row.status === 'connected'"
                />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑连接对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑连接' : '添加连接'"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="连接名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入连接名称"
            clearable
          />
        </el-form-item>

        <el-form-item label="平台类型" prop="platform">
          <el-select
            v-model="formData.platform"
            placeholder="请选择平台类型"
            :disabled="isEdit"
            style="width: 100%"
          >
            <el-option
              v-for="item in PLATFORM_TYPES"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="主机地址" prop="host">
          <el-input
            v-model="formData.host"
            placeholder="例如: 192.168.1.100"
            clearable
          />
        </el-form-item>

        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="formData.port"
            :min="1"
            :max="65535"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="验证证书" prop="insecure">
          <el-checkbox v-model="formData.insecure">
            跳过 TLS 证书验证（仅用于测试环境）
          </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useConnectionStore } from '@/stores/connection'
import { PLATFORM_TYPES, PLATFORM_LABELS } from '@/utils/constants'
import {
  formatDateTime,
  getConnectionStatusType,
  getConnectionStatusText
} from '@/utils/format'
import type { CreateConnectionRequest } from '@/api/types'

const connectionStore = useConnectionStore()

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const testingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const formData = reactive<CreateConnectionRequest>({
  name: '',
  platform: 'vcenter',
  host: '',
  port: 443,
  username: '',
  password: '',
  insecure: false
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入连接名称', trigger: 'blur' }],
  platform: [{ required: true, message: '请选择平台类型', trigger: 'change' }],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' },
    { pattern: /^[\d\w.-]+$/, message: '请输入有效的主机地址', trigger: 'blur' }
  ],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

function showCreateDialog() {
  isEdit.value = false
  dialogVisible.value = true
}

function handleEdit(row: any) {
  isEdit.value = true
  Object.assign(formData, {
    id: row.id,
    name: row.name,
    platform: row.platform,
    host: row.host,
    port: row.port,
    username: row.username,
    password: '', // 不回填密码
    insecure: row.insecure
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      await connectionStore.createConnection(formData)
      ElMessage.success(isEdit.value ? '连接已更新' : '连接已创建')
      dialogVisible.value = false
    } catch (error: any) {
      ElMessage.error(error.message || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleTest(id: number) {
  testingId.value = id
  try {
    const status = await connectionStore.testConnection(id)
    if (status === 'connected') {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error('连接测试失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '连接测试失败')
  } finally {
    testingId.value = null
  }
}

async function handleDelete(id: number) {
  try {
    await connectionStore.deleteConnection(id)
    ElMessage.success('连接已删除')
  } catch (error: any) {
    ElMessage.error(error.message || '删除失败')
  }
}

function resetForm() {
  formRef.value?.resetFields()
  Object.assign(formData, {
    name: '',
    platform: 'vcenter',
    host: '',
    port: 443,
    username: '',
    password: '',
    insecure: false
  })
}
</script>

<style scoped lang="scss">
.connections-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
