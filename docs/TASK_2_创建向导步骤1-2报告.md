# 任务 #2 修改报告：创建向导步骤1-2重构

**开发者**: front-dev-2
**任务**: 重构创建向导 - 平台选择和连接配置 (步骤1-2)
**状态**: ✅ 已完成
**审查结果**: ✅ 通过

---

## 修改时间
2026-03-09

---

## 修改文件

### 1. frontend/src/api/connection.ts

#### 添加的类型接口

```typescript
// VM 数据结构，严格按照 API 文档定义
export interface TestFetchVM {
    id: number;
    name: string;
    datacenter: string;
    uuid: string;
    vmKey: string;        // 唯一标识，重要！
    cpuCount: number;
    memoryGb: number;     // 单位：GB
    powerState: string;
    guestOs?: string;
    ipAddress?: string;
    hostIp: string;
    connectionState: string;
}

// 测试连接并获取VM列表的响应结构
export interface TestConnectionAndFetchVMsResult {
    status: string;
    message: string;
    vms: TestFetchVM[];
    total: number;
}
```

#### 修改的函数

**getVMList** - 移除字段映射逻辑：
```typescript
// 修改前：有 map 转换
return vms.map((v: any) => ({
    id: v.id,
    name: v.name,
    // ... 字段映射
}));

// 修改后：直接返回后端数据
return response.data.data.items || [];
```

---

### 2. frontend/src/views/Wizard.vue

#### 类型导入
```typescript
import type { TestFetchVM } from '@/api/connection'
```

#### 状态类型更新
```typescript
// 修改前
const vmList = ref<any[]>([])

// 修改后
const vmList = ref<TestFetchVM[]>([])
```

#### 内存显示修复
```vue
<!-- 修改前 -->
{{ vm.memoryGb > 0 ? formatMemory(vm.memoryGb * 1024) : '内存: 未获取' }}

<!-- 修改后 -->
{{ vm.memoryGb > 0 ? vm.memoryGb + ' GB' : '内存: 未获取' }}
```

#### 函数参数类型更新
```typescript
// 以下函数参数类型从 any 更改为 TestFetchVM：
- getVMActualState(vm: TestFetchVM)
- isVMStateNormal(vm: TestFetchVM)
- getVMStateText(vm: TestFetchVM)
- getVMStateDotClass(vm: TestFetchVM)
- toggleVM(vm: TestFetchVM)
```

#### 删除的函数
- `formatMemory()` - 不再需要内存单位转换

---

## API 对接说明

### 创建连接
```
POST /api/connections
请求: { name, platform, host, port, username, password, insecure }
响应: Connection 对象
```

### 测试连接并获取VM列表
```
POST /api/connections/{id}/test-and-fetch-vms
响应: { status, message, vms: TestFetchVM[], total }
```

### VM 数据字段映射表

| API 返回字段 | 前端直接使用 | 说明 |
|-------------|-------------|------|
| `vmKey` | ✅ | 唯一标识，用于VM选择 |
| `memoryGb` | ✅ | 内存，单位GB，直接显示 |
| `connectionState` | ✅ | 连接状态，直接判断 |
| `powerState` | ✅ | 电源状态，直接判断 |

---

## 核心原则遵循

1. ✅ **以后端为标准** - 所有字段名直接使用后端返回的 camelCase 格式
2. ✅ **禁止字段映射** - 移除了所有 map 转换逻辑
3. ✅ **类型安全** - 使用 TypeScript 接口替代 any 类型

---

## 调试参考

### VM 列表渲染的 key
```vue
<div v-for="vm in filteredVMs" :key="vm.vmKey">
```

### VM 选择逻辑
```typescript
// 直接使用 vm.vmKey 作为唯一标识
if (selectedVMs.value.has(vm.vmKey)) {
    selectedVMs.value.delete(vm.vmKey)
} else {
    selectedVMs.value.add(vm.vmKey)
}
```

### 内存显示
```vue
<!-- 直接显示 memoryGb，无需转换 -->
{{ vm.memoryGb }} GB
```

---

## 遗留问题
无

---

## 相关文件
- API 文档: `docs/API.md`
- 后端路由: `backend/app/routers/connections.py`
