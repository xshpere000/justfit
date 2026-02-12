# JustFit 前端开发任务清单

## 项目概述

**技术栈**: Vue 3 + Vite + TypeScript + Element Plus + Wails
**设计文档**: `docs/02-用户故事.md`, `docs/03-详细设计/05-前端设计.md`, `docs/03-详细设计/06-前端UI交互设计.md`
**API 文档**: `api/0.0.1/`

---

## 阶段 1：基础架构完善

### 1.1 类型定义集成

- [ ] 复制 `api/0.0.1/types.ts` 到 `frontend/src/types/api.ts`
- [ ] 创建通用类型定义文件 `frontend/src/types/common.ts`
- [ ] 创建图表相关类型 `frontend/src/types/chart.ts`

### 1.2 API 服务层实现

参考文档: `api/0.0.1/GUIDE.md`, `api/0.0.1/api-service.example.ts`

- [ ] 创建 `src/composables/useConnection.ts` - 连接管理服务
- [ ] 创建 `src/composables/useTask.ts` - 任务管理服务
- [ ] 创建 `src/composables/useResource.ts` - 资源查询服务
- [ ] 创建 `src/composables/useAnalysis.ts` - 分析服务
- [ ] 创建 `src/composables/useReport.ts` - 报告服务
- [ ] 创建 `src/composables/useSettings.ts` - 系统配置服务
- [ ] 创建 `src/composables/useAlert.ts` - 告警服务
- [ ] 创建 `src/composables/useDashboard.ts` - 仪表盘服务

### 1.3 Pinia 状态管理

参考文档: `docs/03-详细设计/05-前端设计.md`

- [ ] 创建 `src/stores/connection.ts` - 连接状态管理
- [ ] 创建 `src/stores/task.ts` - 任务状态管理
- [ ] 创建 `src/stores/resource.ts` - 资源状态管理
- [ ] 创建 `src/stores/analysis.ts` - 分析结果状态管理
- [ ] 创建 `src/stores/settings.ts` - 系统配置状态管理
- [ ] 创建 `src/stores/app.ts` - 应用全局状态

### 1.4 路由配置

- [ ] 完善路由配置，添加所有页面路由
- [ ] 配置路由守卫（权限、导航）
- [ ] 配置页面标题和元信息

---

## 阶段 2：通用组件开发

参考文档: `docs/03-详细设计/06-前端UI交互设计.md`

### 2.1 状态组件

- [ ] `Loading.vue` - 加载状态组件
- [ ] `Empty.vue` - 空状态组件
- [ ] `Error.vue` - 错误状态组件
- [ ] `StatusBadge.vue` - 状态徽章组件

### 2.2 表单组件

- [ ] `ConnectionForm.vue` - 连接表单组件
- [ ] `AnalysisConfigForm.vue` - 分析配置表单组件
- [ ] `TaskWizard.vue` - 任务向导组件

### 2.3 数据展示组件

- [ ] `ResourceTable.vue` - 资源表格组件（支持展开行）
- [ ] `MetricCard.vue` - 指标卡片组件
- [ ] `StatCard.vue` - 统计卡片组件
- [ ] `InfoList.vue` - 信息列表组件

### 2.4 图表组件

参考文档: `docs/03-详细设计/05-前端设计.md` (ECharts 配置)

- [ ] `LineChart.vue` - 折线图组件（性能指标）
- [ ] `BarChart.vue` - 柱状图组件
- [ ] `PieChart.vue` - 饼图组件
- [ ] `GaugeChart.vue` - 仪表盘图组件（健康度评分）
- [ ] `HeatmapChart.vue` - 热力图组件

---

## 阶段 3：核心页面开发

### 3.1 首页/仪表盘

参考文档: `docs/02-用户故事.md` (用户故事1)
现有文件: `views/Home.vue`, `views/Dashboard.vue`

- [ ] 完善 `Dashboard.vue` - 仪表盘 KPI 展示
- [ ] 实现 `Dashboard.vue` - 连接状态概览
- [ ] 实现 `Dashboard.vue` - 风险提示面板
- [ ] 实现 `Dashboard.vue` - 快捷操作入口

### 3.2 连接管理

参考文档: `docs/03-详细设计/04-接口设计.md` (连接管理 API)
现有文件: `views/connections/Connections.vue`

- [ ] 完善 `Connections.vue` - 连接列表页面
- [ ] 创建 `ConnectionForm.vue` - 新建/编辑连接对话框
- [ ] 实现 `ConnectionForm.vue` - 连接测试功能
- [ ] 实现 `ConnectionForm.vue` - 连接删除确认

### 3.3 数据采集

参考文档: `docs/03-详细设计/04-接口设计.md` (采集任务 API)
现有文件: `views/connections/Collection.vue`, `views/Wizard.vue`

- [ ] 完善 `Collection.vue` - 数据采集页面
- [ ] 实现 `Wizard.vue` - 采集任务向导（3步流程）
- [ ] 实现 `Wizard.vue` - 采集配置（数据类型选择、时间范围）
- [ ] 实现 `Wizard.vue` - 采集进度展示
- [ ] 实现 `Wizard.vue` - 采集结果展示

### 3.4 任务中心

参考文档: `docs/03-详细设计/04-接口设计.md` (任务管理 API)
现有文件: `views/tasks/Tasks.vue`, `views/tasks/TaskDetail.vue`

- [ ] 完善 `Tasks.vue` - 任务列表页面
- [ ] 实现 `Tasks.vue` - 任务筛选（状态、类型）
- [ ] 实现 `Tasks.vue` - 任务批量操作
- [ ] 完善 `TaskDetail.vue` - 任务详情页
- [ ] 实现 `TaskDetail.vue` - 任务日志 Tab
- [ ] 实现 `TaskDetail.vue` - 虚拟机列表（支持展开查看指标）

### 3.5 分析功能

参考文档: `docs/03-详细设计/04-接口设计.md` (分析 API)
现有文件: `views/analysis/Zombie.vue`, `views/analysis/RightSize.vue`, `views/analysis/Tidal.vue`, `views/analysis/Health.vue`

#### 3.5.1 僵尸 VM 检测

- [ ] 完善 `Zombie.vue` - 僵尸 VM 检测页面
- [ ] 实现 `Zombie.vue` - 检测配置面板
- [ ] 实现 `Zombie.vue` - 结果汇总统计
- [ ] 实现 `Zombie.vue` - 僵尸 VM 列表（支持详情查看）
- [ ] 实现 `Zombie.vue` - 批量操作（标记、忽略）

#### 3.5.2 Right Size 分析

- [ ] 完善 `RightSize.vue` - Right Size 分析页面
- [ ] 实现 `RightSize.vue` - 分析配置面板
- [ ] 实现 `RightSize.vue` - 优化建议统计
- [ ] 实现 `RightSize.vue` - 优化建议列表
- [ ] 实现 `RightSize.vue` - 节省成本估算

#### 3.5.3 潮汐检测

- [ ] 完善 `Tidal.vue` - 潮汐检测页面
- [ ] 实现 `Tidal.vue` - 检测配置面板
- [ ] 实现 `Tidal.vue` - 模式统计展示
- [ ] 实现 `Tidal.vue` - 潮汐 VM 列表
- [ ] 实现 `Tidal.vue` - 潮汐模式可视化（图表）

#### 3.5.4 平台健康度

- [ ] 完善 `Health.vue` - 平台健康度页面
- [ ] 实现 `Health.vue` - 评分仪表盘（GaugeChart）
- [ ] 实现 `Health.vue` - 各项指标展示
- [ ] 实现 `Health.vue` - 风险项列表
- [ ] 实现 `Health.vue` - 改进建议列表

### 3.6 虚拟机详情

参考文档: `docs/03-详细设计/06-前端UI交互设计.md`

- [ ] 创建 `views/vms/VMDetail.vue` - 虚拟机详情页
- [ ] 实现 `VMDetail.vue` - 基本信息 Tab
- [ ] 实现 `VMDetail.vue` - 性能指标图表（CPU、内存、磁盘、网络）
- [ ] 实现 `VMDetail.vue` - 历史趋势分析
- [ ] 实现 `VMDetail.vue` - 分析建议 Tab

### 3.7 资源管理

- [ ] 创建 `views/resources/Clusters.vue` - 集群管理页面
- [ ] 创建 `views/resources/Hosts.vue` - 主机管理页面
- [ ] 创建 `views/resources/VMs.vue` - 虚拟机管理页面
- [ ] 实现资源列表的搜索、筛选、排序功能
- [ ] 实现资源批量操作

### 3.8 报告管理

参考文档: `docs/03-详细设计/04-接口设计.md` (报告 API)

- [ ] 创建 `views/reports/Reports.vue` - 报告列表页面
- [ ] 创建 `views/reports/ReportDetail.vue` - 报告详情页
- [ ] 实现 `Reports.vue` - 报告生成向导
- [ ] 实现 `ReportDetail.vue` - 报告内容展示
- [ ] 实现 `ReportDetail.vue` - 报告导出功能

### 3.9 系统设置

参考文档: `docs/03-详细设计/04-接口设计.md` (系统配置 API)
现有文件: `views/Settings.vue`

- [ ] 完善 `Settings.vue` - 系统设置页面
- [ ] 实现 `Settings.vue` - 分析配置设置
- [ ] 实现 `Settings.vue` - 采集配置设置
- [ ] 实现 `Settings.vue` - 界面主题设置
- [ ] 实现 `Settings.vue` - 诊断包导出

---

## 阶段 4：高级功能

### 4.1 告警管理

参考文档: `docs/03-详细设计/04-接口设计.md` (告警 API)

- [ ] 创建 `views/alerts/Alerts.vue` - 告警列表页面
- [ ] 实现 `Alerts.vue` - 告警筛选（级别、类型、状态）
- [ ] 实现 `Alerts.vue` - 告警确认/忽略
- [ ] 实现 `Alerts.vue` - 告警统计面板
- [ ] 创建告警通知组件

### 4.2 实时数据更新

- [ ] 实现任务进度实时更新（轮询或 WebSocket）
- [ ] 实现采集进度实时展示
- [ ] 实现仪表盘数据自动刷新

### 4.3 数据可视化优化

- [ ] 实现性能指标图表的交互（缩放、tooltip）
- [ ] 实现图表数据导出功能
- [ ] 优化大数据量的图表渲染性能

---

## 阶段 5：样式与主题

参考文档: `docs/03-详细设计/06-前端UI交互设计.md`

### 5.1 主题系统

- [ ] 实现亮色/暗色主题切换
- [ ] 定义 CSS 变量（颜色、间距、圆角）
- [ ] 实现主题切换动画效果

### 5.2 响应式布局

- [ ] 确保在不同分辨率下正常显示
- [ ] 优化表格在窄屏下的展示

### 5.3 样式优化

- [ ] 统一组件样式规范
- [ ] 优化动画过渡效果
- [ ] 优化表格和表单样式

---

## 阶段 6：集成与测试

### 6.1 前后端集成

参考文档: `api/0.0.1/GUIDE.md`

- [ ] 配置 Wails 绑定
- [ ] 测试所有 API 调用
- [ ] 处理错误场景和边界情况

### 6.2 功能测试

- [ ] 测试所有页面的用户流程
- [ ] 测试表单验证和提交
- [ ] 测试数据加载和展示
- [ ] 测试图表渲染和交互

### 6.3 性能优化

- [ ] 实现虚拟滚动（长列表）
- [ ] 优化图表数据量（降采样）
- [ ] 实现图片懒加载
- [ ] 优化打包体积

---

## 阶段 7：部署准备

### 7.1 构建优化

- [ ] 配置生产环境构建
- [ ] 优化打包体积
- [ ] 配置资源压缩

### 7.2 打包测试

- [ ] Wails 桌面应用打包测试
- [ ] 多平台兼容性测试（Windows、Linux、macOS）

---

## 任务优先级

### P0（核心功能）

- 阶段 1：基础架构完善
- 阶段 2：通用组件开发
- 阶段 3.1-3.5：核心页面开发

### P1（增强功能）

- 阶段 3.6-3.9：资源管理、报告、设置
- 阶段 4.1：告警管理

### P2（优化功能）

- 阶段 4.2-4.3：实时更新、数据可视化
- 阶段 5：样式与主题
- 阶段 6：集成与测试

---

## 参考资料

### 设计文档

- `docs/02-用户故事.md` - 用户故事和功能需求
- `docs/03-详细设计/05-前端设计.md` - 前端架构设计
- `docs/03-详细设计/06-前端UI交互设计.md` - UI交互规范

### API 文档

- `api/0.0.1/README.md` - API 完整参考
- `api/0.0.1/types.ts` - TypeScript 类型定义
- `api/0.0.1/GUIDE.md` - 使用指南

### 现有前端代码

- `frontend/src/` - 前端源代码目录
- `frontend/src/components/` - 现有组件
- `frontend/src/views/` - 现有页面组件

### 后端 API（已实现）

- 37 个 API 方法已全部实现并通过测试
- 详见 `TODO.md` 中的 API 方法汇总
