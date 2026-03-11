# 任务 #4 修改报告：任务详情 - 配置和日志界面

**开发者**: front-dev-4
**任务**: 重构任务详情 - 配置和日志界面
**状态**: ✅ 已完成
**审查结果**: ✅ 通过

---

## 修改时间
2026-03-09

---

## 修改的文件清单

### 修改文件
- `frontend/src/views/TaskDetail.vue` - 新增配置 Tab、增强日志 Tab

---

## 主要修改内容

### 1. 新增"配置"Tab

使用 `el-descriptions` 组件展示任务配置信息：

**显示字段**:
- 任务名称、类型（带 Tag 样式）、状态
- 平台类型（vCenter/UIS）
- 连接名称、连接主机
- 评估对象数量
- 采集天数

**新增功能**:
- 选中的虚拟机列表展示
- 支持展开/收起，默认显示 20 台

### 2. 重构"日志"Tab

**新增功能**:
- 日志级别筛选（el-select 多选）
  - 支持 Debug/Info/Warning/Error 级别筛选
  - 支持折叠标签显示
- 保留关键字搜索功能
- 日志级别显示改为大写（DEBUG/INFO/WARN/ERROR）
- 日志时间格式化（使用 `formatLogTimestamp` 函数）
- 刷新按钮添加图标

---

## API 对接说明

### 获取任务详情
```
GET /api/tasks/{task_id}
```

**关键字段**（直接使用后端返回）:
```typescript
{
  id: number
  name: string
  type: string
  status: string
  platform: string
  connectionName: string      // ✅ 直接使用
  connectionHost: string      // ✅ 直接使用
  selectedVMCount: number     // ✅ 直接使用
  config: {
    metricsDays: number       // ✅ 直接使用
  }
}
```

### 获取任务日志
```
GET /api/tasks/{task_id}/logs
```

**关键字段**:
```typescript
{
  items: [{
    id: number
    level: "debug" | "info" | "warn" | "error"  // ✅ 直接使用
    message: string                               // ✅ 直接使用
    timestamp: string                             // ✅ 直接使用
  }]
  total: number
}
```

---

## 核心原则遵循

1. ✅ **以后端为标准** - 所有字段名直接使用后端返回的 camelCase 格式
2. ✅ **禁止字段映射** - 未添加任何字段映射或转换层
3. ✅ **类型安全** - 使用 TypeScript 类型定义

---

## 新增代码元素

### 配置 Tab
- `el-descriptions` 组件
- VM 列表展开/收起功能
- 显示选中 VM 的 `vmKey` 和 `name`

### 日志 Tab
- `el-select` 多选组件（日志级别筛选）
- `formatLogTimestamp` 函数
- 折叠标签显示

---

## 注意事项

1. **字段命名**: 
   - 严格使用后端返回的字段名
   - `connectionName`, `connectionHost`, `selectedVMCount`, `metricsDays`

2. **日志级别**:
   - 后端返回小写（debug/info/warn/error）
   - 前端显示大写（DEBUG/INFO/WARN/ERROR）

3. **日志筛选**:
   - 使用 `selectedLogLevels` 存储选中的级别
   - 筛选逻辑在 `filteredLogs` computed 中实现

---

## 测试建议

1. **配置 Tab 测试**:
   - 验证所有字段正确显示
   - 测试 VM 列表展开/收起功能

2. **日志 Tab 测试**:
   - 测试日志级别筛选
   - 测试关键字搜索
   - 验证日志时间格式化

---

## 后续优化建议

1. 日志自动滚动到底部（可选功能）
2. 日志导出功能
3. 日志实时更新（WebSocket 支持）

---

## 相关文件
- API 文档: `docs/API.md`
- 任务 #1 报告: `docs/TASK_1_首页重构报告.md`
