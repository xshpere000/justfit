# JustFit 前端 API 使用指南

## 快速开始

### 1. 安装依赖

确保项目中已安装 Wails 生成的绑定：

```bash
npm install
```

### 2. 类型定义导入

将 `api/0.0.1/types.ts` 复制到前端项目的 `src/types/` 目录：

```bash
mkdir -p src/types
cp api/0.0.1/types.ts src/types/api.ts
```

### 3. 在组件中使用

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useConnectionService } from '@/composables/useConnection';

const { connections, loading, listConnections } = useConnectionService();

onMounted(async () => {
  await listConnections();
});
</script>

<template>
  <div v-loading="loading">
    <div v-for="conn in connections" :key="conn.ID">
      {{ conn.Name }} - {{ conn.Host }}
    </div>
  </div>
</template>
```

---

## API 调用示例

### 创建连接

```typescript
const { createConnection } = useConnectionService();

const handleCreate = async () => {
  try {
    const id = await createConnection({
      name: '生产环境',
      platform: 'vcenter',
      host: '192.168.1.100',
      port: 443,
      username: 'administrator@vsphere.local',
      password: 'password123',
      insecure: true,
    });
    console.log('连接创建成功，ID:', id);
  } catch (error) {
    console.error('创建失败:', error.message);
  }
};
```

### 测试连接

```typescript
const { testConnection } = useConnectionService();

const handleTest = async () => {
  try {
    const result = await testConnection({
      id: 1,
      host: '192.168.1.100',
      username: 'administrator@vsphere.local',
      password: 'password123',
      platform: 'vcenter',
      insecure: true,
    });

    if (result.Success) {
      console.log('连接成功，版本:', result.Version);
    } else {
      console.error('连接失败:', result.Message);
    }
  } catch (error) {
    console.error('测试失败:', error.message);
  }
};
```

### 创建采集任务

```typescript
const { createCollectTask, tasks } = useTaskService();

const handleCollect = async (connectionId: number) => {
  try {
    const taskId = await createCollectTask(
      connectionId,
      ['clusters', 'hosts', 'vms'],
      7  // 采集7天的性能指标
    );
    console.log('任务创建成功，ID:', taskId);
  } catch (error) {
    console.error('创建任务失败:', error.message);
  }
};
```

### 运行僵尸 VM 分析

```typescript
const { detectZombieVMs, zombieVMs } = useAnalysisService();

const handleAnalyze = async (connectionId: number) => {
  try {
    const results = await detectZombieVMs(connectionId, {
      analysis_days: 7,
      cpu_threshold: 5,
      memory_threshold: 10,
      min_confidence: 0.7,
    });

    console.log(`检测到 ${results.length} 个僵尸 VM`);
    results.forEach(vm => {
      console.log(`- ${vm.VMName}: ${vm.Recommendation}`);
    });
  } catch (error) {
    console.error('分析失败:', error.message);
  }
};
```

### 获取资源列表

```typescript
const { listClusters, clusters } = useResourceService();

// 获取集群列表
const handleLoadClusters = async (connectionId: number) => {
  try {
    const result = await listClusters(connectionId);
    console.log('集群数量:', result.length);
  } catch (error) {
    console.error('加载失败:', error.message);
  }
};
```

---

## 错误处理

所有 API 调用都应该进行错误处理：

```typescript
try {
  await apiMethod(params);
  // 成功处理
} catch (error: any) {
  // 错误处理
  ElMessage.error(error.message || '操作失败');
}
```

---

## Wails 绑定说明

Wails 会自动生成 Go 后端方法的 JavaScript 绑定。调用方式：

```typescript
// 方式1: 直接调用
await window.go.main.App.MethodName(param1, param2);

// 方式2: 使用对象参数
await window.go.main.App.MethodName({
  param1: value1,
  param2: value2,
});
```

---

## 状态管理建议

对于复杂应用，建议使用 Pinia 进行状态管理：

```typescript
// stores/connection.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { Connection } from '@/types/api';

export const useConnectionStore = defineStore('connection', () => {
  const connections = ref<Connection[]>([]);
  const activeConnectionId = ref<number | null>(null);

  async function loadConnections() {
    const result = await window.go.main.App.ListConnections();
    connections.value = JSON.parse(result);
  }

  function setActiveConnection(id: number) {
    activeConnectionId.value = id;
  }

  return {
    connections,
    activeConnectionId,
    loadConnections,
    setActiveConnection,
  };
});
```

---

## API 文档索引

- [README.md](./README.md) - 完整 API 参考文档
- [types.ts](./types.ts) - TypeScript 类型定义
- [api-service.example.ts](./api-service.example.ts) - 服务层示例代码
