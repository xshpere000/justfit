# 任务 #1 修改报告：首页 (Home.vue) 重构

**开发者**: front-dev-1
**完成时间**: 2026-03-09
**状态**: ✅ 已完成并通过审查

---

## 修改的文件清单

### 新建文件
1. `frontend/src/components/TaskCard.vue`
   - 类型：新建组件
   - 作用：封装任务卡片显示逻辑

2. `frontend/src/components/HomeBanner.vue`
   - 类型：新建组件
   - 作用：封装轮播 Banner 显示逻辑

### 修改文件
3. `frontend/src/api/task.ts`
   - 修改类型定义

4. `frontend/src/views/Home.vue`
   - 重构：使用新组件，代码精简

5. `frontend/src/views/TaskDetail.vue`
   - 修正：删除字段映射逻辑

---

## 主要修改内容

### 1. 类型定义修正 (`frontend/src/api/task.ts`)

```typescript
// 修改前
analysisResults: {
  zombie: boolean;
  rightsize: boolean;
  tidal: boolean;
  health: boolean;
};

// 修改后（与后端 API 一致）
analysisResults: {
  idle: boolean;
  resource: boolean;
  health: boolean;
};
```

### 2. 组件拆分

**TaskCard.vue** - 任务卡片组件
- Props: `task: Task`
- Emits: `click`, `command`
- 支持所有任务状态显示
- 完整 TypeScript 类型定义

**HomeBanner.vue** - Banner 轮播组件
- 展示四个核心功能
- 支持高度自定义

### 3. Home.vue 重构

**修改前**：~700 行
**修改后**：~200 行

保留功能：
- 任务状态筛选（全部/进行中/已完成）
- 任务搜索（按名称或连接）
- 任务卡片展示
- 分页功能

### 4. TaskDetail.vue 字段映射修正

**状态定义更新**：
```typescript
// 修改前
const hasAnalysisResults = reactive({
  zombie: false,
  rightsize: false,
  tidal: false,
  health: false
});

// 修改后（直接使用后端字段名）
const hasAnalysisResults = reactive({
  idle: false,
  resource: false,
  health: false
});
```

**添加映射辅助函数**：
```typescript
function getAnalysisStatus(analysisKey: string): boolean {
  const keyMapping: Record<string, 'idle' | 'resource' | 'health'> = {
    zombie: 'idle',
    rightsize: 'resource',
    tidal: 'resource',
    health: 'health'
  };
  return hasAnalysisResults[keyMapping[analysisKey]] || false;
}
```

---

## API 对接说明

### 使用的 API 端点

**GET /api/tasks** - 获取任务列表

**关键字段对接**（camelCase）：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | number | 任务ID |
| name | string | 任务名称 |
| status | string | pending/running/completed/failed/cancelled |
| progress | number | 进度 0-100 |
| analysisResults | object | { idle, resource, health } |
| platform | string | vcenter/h3c-uis |
| connectionHost | string | 连接主机地址 |
| selectedVMCount | number | 选中的VM数量 |
| createdAt | string | 创建时间 |

---

## 注意事项

### 1. 字段命名规范
- **前端类型定义必须与后端 API 返回一致**
- `analysisResults` 使用 `{ idle, resource, health }`
- 禁止创建字段映射或转换层

### 2. UI 标识符 vs 数据字段
- **前端 Tab 标识符**：`zombie`, `rightsize`, `tidal`, `health`（用于 UI）
- **后端数据字段**：`idle`, `resource`, `health`（用于数据）
- 使用 `getAnalysisStatus()` 函数进行 UI 层面的映射

### 3. 后续维护建议
- 新增分析类型时，同步更新：
  - `frontend/src/api/task.ts` 类型定义
  - `hasAnalysisResults` 状态
  - `getAnalysisStatus()` 映射函数

---

## 修改摘要

- 新建组件：2 个
- 修改文件：3 个
- 删除代码行数：~500 行（通过组件拆分）
- 字段映射修正：~15 处
