# JustFit 统一 TODO

> 更新时间：2026-02-12
> 说明：本文件为项目唯一待办清单；历史已完成事项已归档删除。

## 前端 TODO

> 进度概览：当前以联调收口与稳定性为主，组件化与页面完善为次优先。

### P0（当前优先）

#### 1) TaskDetail 联调收口

- [ ] 统一任务详情字段映射，消除 `task.id` 与 `backendTaskId` 混用
- [ ] 统一详情页路由入口参数规范（首页/任务中心进入行为一致）
- [ ] 补齐异常场景提示：任务不存在、连接失效、日志为空、导出失败
- [ ] 前端导出链路切换到任务维度 `ExportTaskReport(taskID, format)`

#### 2) 前端稳定性

- [ ] 任务进度轮询策略优化（减少重复请求与无效轮询）
- [ ] 高数据量场景下 `Collection / Dashboard / TaskDetail` 交互稳定性验证

### P1（功能完善）

#### 3) 通用组件库

- [ ] `Loading.vue`
- [ ] `Empty.vue`
- [ ] `Error.vue`
- [ ] `StatusBadge.vue`
- [ ] `ConnectionForm.vue`
- [ ] `AnalysisConfigForm.vue`
- [ ] `TaskWizard.vue`
- [ ] `ResourceTable.vue`
- [ ] `MetricCard.vue`
- [ ] `StatCard.vue`
- [ ] `InfoList.vue`

#### 4) 图表组件（ECharts）

- [ ] `LineChart.vue`
- [ ] `BarChart.vue`
- [ ] `PieChart.vue`
- [ ] `GaugeChart.vue`
- [ ] `HeatmapChart.vue`

#### 5) 业务页面与能力

- [ ] 告警管理页面
- [ ] 报告管理页面
- [ ] 虚拟机详情页面
- [ ] 资源管理页面（`Clusters / Hosts / VMs`）
- [ ] 资源列表搜索/筛选/排序/批量操作

### P2（优化与发布）

#### 6) 体验与主题

- [ ] 亮色/暗色主题切换
- [ ] 响应式布局优化
- [ ] 统一组件样式规范

#### 7) 部署与工程化

- [ ] 生产环境构建配置
- [ ] 打包体积优化
- [ ] 多平台打包测试
- [ ] 前端自动化测试（单测/E2E）

## 后端 TODO

> 进度概览：后端闭环已完成，当前仅保留非阻塞增强项。

### P1（可持续增强，非阻塞）

- [ ] ETL 断点续采与重试策略增强
- [ ] 分析算法置信度与风险说明增强
- [ ] 报告内容增强（P95、峰谷、建议动作）

## 备注

- 后端闭环（任务维度 API、任务快照、指标可观测性）已完成。
- `test/` 目录为测试代码，不作为主程序交付阻塞项。
