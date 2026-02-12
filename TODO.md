# JustFit 项目开发 TODO

## 整体进度概览

| 模块 | 进度 | 状态 |
|------|------|------|
| 后端 API | 100% | ✅ 完成 |
| 前端基础架构 | 90% | 🟡 进行中 |
| 前端页面开发 | 70% | 🟡 进行中 |
| 前后端集成 | 80% | 🟡 进行中 |
| 测试验证 | 85% | 🟡 进行中 |

---

## 后端开发进度 ✅ (100%)

### 阶段 1：连接管理 API ✅

- [x] `GetConnection(id uint) (*ConnectionInfo, error)` - 获取单个连接详情
- [x] `UpdateConnection(req UpdateConnectionRequest) error` - 更新连接配置

### 阶段 2：采集任务管理模块 ✅

- [x] 创建 `internal/service/task_service.go` 文件
- [x] 实现 `CollectionExecutor` 任务执行器
- [x] 实现 `AnalysisExecutor` 任务执行器
- [x] 修改 `app.go` 添加任务调度器字段
- [x] 修改 `startup` 方法初始化任务调度器
- [x] `CreateCollectTask(config CollectionConfig) (uint, error)` - 创建采集任务
- [x] `ListTasks(status string, limit, offset int) ([]TaskInfo, error)` - 获取任务列表
- [x] `GetTask(id uint) (*TaskInfo, error)` - 获取任务详情
- [x] `StopTask(id uint) error` - 停止任务
- [x] `RetryTask(id uint) (uint, error)` - 重试任务
- [x] `GetTaskLogs(id uint, limit int) ([]TaskLogEntry, error)` - 获取任务日志

### 阶段 3：资源查询 API 标准化 ✅

- [x] `ListClusters(connectionID uint) ([]ClusterListItem, error)` - 标准化集群列表
- [x] `ListHosts(connectionID uint) ([]HostListItem, error)` - 标准化主机列表
- [x] `ListVMs(connectionID uint) ([]VMListItem, error)` - 标准化虚拟机列表
- [x] `GetMetrics(vmID uint, metricType string, days int) (*MetricsData, error)` - 获取指标数据
- [x] `GetEntityDetail(entityType EntityType, id uint) (*EntityDetail, error)` - 获取实体详情

### 阶段 4：分析服务统一入口 ✅

- [x] `RunAnalysis(req AnalysisRequest) (*AnalysisResponse, error)` - 统一分析入口
- [x] `GetAnalysisResult(resultID uint) (map[string]interface{}, error)` - 获取分析结果
- [x] `GetAnalysisSummary(connectionID uint) (*AnalysisSummary, error)` - 获取分析汇总

### 阶段 5：报告服务 ✅

- [x] `ListReports(limit, offset int) ([]ReportListItem, error)` - 获取报告列表
- [x] `GetReport(id uint) (*ReportDetail, error)` - 获取报告详情
- [x] `ExportReport(req ExportReportRequest) (string, error)` - 导出报告

### 阶段 6：系统配置服务 ✅

- [x] 创建 `internal/storage/settings_repo.go` 文件
- [x] 在 `models.go` 添加 `Settings` 模型
- [x] 在 `db.go` 添加 Settings 表迁移
- [x] 在 `repositories.go` 添加 SettingsRepository
- [x] `GetSettings() (*SystemSettings, error)` - 获取系统配置
- [x] `UpdateSettings(settings SystemSettings) error` - 更新系统配置
- [x] `ExportDiagnosticPackage() (string, error)` - 导出诊断包

### 阶段 7：告警服务 ✅

- [x] `ListAlerts(acknowledged *bool, limit, offset int) ([]AlertListItem, error)` - 获取告警列表
- [x] `MarkAlert(req MarkAlertRequest) error` - 标记告警
- [x] `GetAlertStats() (*AlertStats, error)` - 获取告警统计

### 阶段 8：H3C UIS 连接器支持 ✅

- [x] 创建 `internal/connector/uis.go` 文件
- [x] 实现 UIS 登录认证 (`/uis/spring_check`)
- [x] 实现虚拟机列表获取 (`/uis/vm/list/summary`)
- [x] 实现虚拟机性能报表获取 (CPU、内存、磁盘、网络)
- [x] 实现 UIS 报表类型枚举和配置

### 验证

- [x] 编译验证 (`go build`) ✅ 通过
- [x] 单元测试 (47个测试用例全部通过)
- [x] 集成测试 (7个测试模块全部通过)
- [x] 真实环境测试 (vCenter 9.0.0 连接成功，采集数据正常)

---

## 前端开发进度 🟡 (70%)

### 已完成

#### 阶段 1：基础架构 ✅

- [x] 类型定义集成 (`frontend/src/types/api.ts`, `frontend/src/types/common.ts`)
- [x] API 服务层实现 (`frontend/src/api/connection.ts` - 完整的 Wails 绑定)
- [x] Pinia 状态管理
  - [x] `stores/connection.ts` - 连接状态管理
  - [x] `stores/task.ts` - 任务状态管理
  - [x] `stores/app.ts` - 应用全局状态
- [x] 路由配置 (`frontend/src/router/index.ts`)

#### 阶段 2：核心页面组件 ✅

- [x] `AppShell.vue` - 应用框架组件
- [x] `Dashboard.vue` - 仪表盘页面
- [x] `Connections.vue` - 连接管理页面
- [x] `Tasks.vue` - 任务列表页面
- [x] `TaskDetail.vue` - 任务详情页面
- [x] `Wizard.vue` - 数据采集向导页面
- [x] `Collection.vue` - 数据采集页面
- [x] `Settings.vue` - 系统设置页面
- [x] 分析页面
  - [x] `Zombie.vue` - 僵尸 VM 检测
  - [x] `RightSize.vue` - Right Size 评估
  - [x] `Tidal.vue` - 潮汐检测
  - [x] `Health.vue` - 平台健康度

#### 阶段 3：前后端集成 ✅

- [x] Wails 绑定生成 (`wails generate module`)
- [x] API 服务层封装 (所有 37 个后端 API 已对接)
- [x] 类型定义同步 (后端模型与前端类型对齐)

### 进行中

#### 阶段 4：通用组件 🟡

- [ ] `Loading.vue` - 加载状态组件
- [ ] `Empty.vue` - 空状态组件
- [ ] `Error.vue` - 错误状态组件
- [ ] `StatusBadge.vue` - 状态徽章组件
- [ ] `ConnectionForm.vue` - 连接表单组件
- [ ] `AnalysisConfigForm.vue` - 分析配置表单组件
- [ ] `ResourceTable.vue` - 资源表格组件
- [ ] `MetricCard.vue` - 指标卡���组件
- [ ] 图表组件 (ECharts 封装)
  - [ ] `LineChart.vue` - 折线图
  - [ ] `BarChart.vue` - 柱状图
  - [ ] `PieChart.vue` - 饼图
  - [ ] `GaugeChart.vue` - 仪表盘图

#### 阶段 5：高级功能 🟡

- [ ] 实时数据更新 (任务进度轮询优化)
- [ ] 数据可视化优化
- [ ] 告警管理页面
- [ ] 报告管理页面
- [ ] 虚拟机详情页面

#### 阶段 6：样式与主题 🟡

- [ ] 亮色/暗色主题切换
- [ ] 响应式布局优化
- [ ] 统一组件样式规范

### 待开始

#### 阶段 7：部署准备 📋

- [ ] 生产环境构建配置
- [ ] 打包体积优化
- [ ] 多平台打包测试

---

## 实施优先级

**P0（高）**: ✅ 完成

- 后端所有 API (37 个方法)
- 前端基础架构
- 前端核心页面

**P1（中）**: 🟡 进行中

- 前端通用组件库
- 前后端集成优化
- 虚拟机详情页

**P2（低）**: 📋 待开始

- 主题系统
- 高级图表组件
- 性能优化

---

## 后端文件清单

### 新增文件

1. `internal/service/task_service.go` - 任务执行器实现
2. `internal/storage/settings_repo.go` - 系统配置仓储
3. `internal/connector/uis.go` - H3C UIS 连接器

### 修改文件

1. `app.go` - 添加所有缺失的 API 方法
2. `internal/storage/models.go` - 添加 Settings 模型
3. `internal/storage/db.go` - 添加 Settings 表迁移和仓储

---

## 前端文件清单

### 目录结构

```
frontend/src/
├── api/
│   ├── connection.ts      # 连接/任务/采集/分析/资源/仪表盘 API
│   ├── analysis.ts        # 分析服务 API
│   ├── report.ts         # 报告服务 API
│   └── types.ts          # 类型定义
├── stores/
│   ├── connection.ts     # 连接状态管理
│   ├── task.ts          # 任务状态管理
│   └── app.ts           # 应用全局状态
├── types/
│   ├── api.ts           # API 类型定义
│   ├── common.ts        # 通用类型
│   └── index.ts         # 类型导出
├── views/
│   ├── Dashboard.vue     # 仪表盘
│   ├── Connections.vue  # 连接管理
│   ├── Tasks.vue        # 任务列表
│   ├── TaskDetail.vue   # 任务详情
│   ├── Wizard.vue       # 采集向导
│   ├── Collection.vue  # 数据采集
│   ├── Settings.vue     # 系统设置
│   └── analysis/
│       ├── Zombie.vue   # 僵尸 VM 检测
│       ├── RightSize.vue # Right Size 评估
│       ├── Tidal.vue    # 潮汐检测
│       └── Health.vue   # 平台健康度
├── components/
│   ├── AppShell.vue     # 应��框架
│   └── HelloWorld.vue  # 示例组件
├── router/
│   └── index.ts        # 路由配置
└── utils/
    ├── format.ts        # 格式化工具
    ├── constants.ts     # 常量定义
    └── dayjs.ts        # 日期处理
```

---

## API 方法汇总

### 连接管理 (6个)

- CreateConnection ✅
- TestConnection ✅
- ListConnections ✅
- GetConnection ✅ (新增)
- UpdateConnection ✅ (新增)
- DeleteConnection ✅

### 采集任务 (6个)

- CreateCollectTask ✅ (新增)
- ListTasks ✅ (新增)
- GetTask ✅ (新增)
- StopTask ✅ (新增)
- RetryTask ✅ (新增)
- GetTaskLogs ✅ (新增)

### 资源查询 (5个)

- ListClusters ✅ (新增)
- ListHosts ✅ (新增)
- ListVMs ✅ (新增)
- GetMetrics ✅ (新增)
- GetEntityDetail ✅ (新增)

### 分析服务 (7个)

- DetectZombieVMs ✅
- AnalyzeRightSize ✅
- DetectTidalPattern ✅
- AnalyzeHealthScore ✅
- RunAnalysis ✅ (新增)
- GetAnalysisResult ✅ (新增)
- GetAnalysisSummary ✅ (新增)

### 报告服务 (3个)

- GenerateReport ✅
- ListReports ✅ (新增)
- GetReport ✅ (新增)
- ExportReport ✅ (新增)

### 系统配置 (3个)

- GetSettings ✅ (新增)
- UpdateSettings ✅ (新增)
- ExportDiagnosticPackage ✅ (新增)

### 告警服务 (4个)

- CreateAlert ✅
- ListAlerts ✅ (新增)
- MarkAlert ✅ (新增)
- GetAlertStats ✅ (新增)

### 其他

- GetDashboardStats ✅
- ExportReport ✅
- Greet ✅

**总计**: 37 个 API 方法

---

## 测试验证

- [x] 单元测试 (47个测试用例全部通过)
- [x] 集成测试 (7个测试模块全部通过)
- [x] 真实环境测试 (vCenter 9.0.0 连接成功，采集数据正常)

详细测试报告见 `test/` 目录：

- `test/TEST_PLAN.md` - 测试计划
- `test/TEST_REPORT.md` - 单元测试与集成测试报告
- `test/TEST_REPORT_E2E.md` - 真实环境端到端测试报告

---

## API 文档

详细的 API 文档（含入参出参）请查看 `api/0.0.1/` 目录：

### API 文档目录结构

```
api/0.0.1/
├── README.md              # API 参考文档（所有接口的入参出参）
├── types.ts               # TypeScript 类型定义（前端可直接使用）
├── GUIDE.md               # 前端 API 使用指南
└── api-service.example.ts # Vue 3 Composition API 服务层示例
```

### 快速开始

1. 复制类型定义到前端项目：

   ```bash
   cp api/0.0.1/types.ts frontend/src/types/api.ts
   ```

2. 参考示例代码实现服务层：

   ```bash
   cp api/0.0.1/api-service.example.ts frontend/src/composables/useApi.ts
   ```

3. 在组件中使用：

   ```vue
   <script setup lang="ts">
   import { useConnectionService } from '@/composables/useApi';

   const { connections, listConnections } = useConnectionService();

   onMounted(() => listConnections());
   </script>
  ```

---

## 前端开发

详细的前端开发任务清单请查看 `FRONTEND_TODO.md` 文件。

该文件包含：
- 7 个开发阶段（基础架构、通用组件、核心页面、高级功能、样式主题、集成测试、部署准备）
- 50+ 个具体任务项
- 任务优先级划分（P0/P1/P2）
- 相关文档和参考资料索引

### 前后端对接修复已完成 ✅

已完成以下工作：

1. **生成 Wails 绑定** - 执行 `wails generate module` 生成前端绑定
2. **创建 API 服务层** - `frontend/src/api/connection_new.ts` 封装所有后端 API 调用
3. **更新类型定义** - 创建 `frontend/src/types/` 目录，统一类型管理
4. **修复 Store 层** - 更新 `connection_new.ts` 和 `task_new.ts` 使用真实 API
5. **修复视图页面** - 创建新版本的视图文件：
   - `Dashboard_new.vue` - 仪表盘页面
   - `Connections_new.vue` - 连接管理页面
   - `Tasks_new.vue` - 任务管理页面
   - `Wizard_new.vue` - 任务向导页面
   - `analysis/Zombie_new.vue` - 僵尸 VM 检测页面
   - `analysis/RightSize_new.vue` - Right Size 评估页面
   - `analysis/Tidal_new.vue` - 潮汐检测页面
   - `analysis/Health_new.vue` - 平台健康度分析页面

### 待替换的文件清单

需要将新版本的文件替换旧版本（重命名或复制）：

```bash
# API 层
mv frontend/src/api/connection_new.ts frontend/src/api/connection.ts
mv frontend/src/api/connection.ts frontend/src/api/connection_old.ts

# Store 层
mv frontend/src/stores/connection_new.ts frontend/src/stores/connection.ts
mv frontend/src/stores/task_new.ts frontend/src/stores/task.ts

# 视图层
mv frontend/src/views/Dashboard_new.vue frontend/src/views/Dashboard.vue
mv frontend/src/views/Connections_new.vue frontend/src/views/Connections.vue
mv frontend/src/views/Tasks_new.vue frontend/src/views/Tasks.vue
mv frontend/src/views/Wizard_new.vue frontend/src/views/Wizard.vue
mv frontend/src/views/analysis/Zombie_new.vue frontend/src/views/analysis/Zombie.vue
mv frontend/src/views/analysis/RightSize_new.vue frontend/src/views/analysis/RightSize.vue
mv frontend/src/views/analysis/Tidal_new.vue frontend/src/views/analysis/Tidal.vue
mv frontend/src/views/analysis/Health_new.vue frontend/src/views/analysis/Health.vue
```

### 注意事项

1. 所有 Mock 数据已移除，全部使用真实后端 API
2. 类型定义与后端 API 完全对齐
3. Wails 绑定文件于 `frontend/wailsjs/` 目录
4. 任务状态通过轮询后端获取，不再使用 localStorage 模拟

---

## 技术栈

### 后端
- Go 1.21+
- Wails v2
- SQLite (存储)
- VMware vSphere API (vCenter 连接器)
- H3C UIS REST API (UIS 连接器)

### 前端
- Vue 3 (Composition API)
- TypeScript
- Vite
- Element Plus (UI 组件库)
- Pinia (状态管理)
- Vue Router
- ECharts (图表)
- Wails (桌面应用框架)

---

## 下一步工作

### 短期 (1-2 周)

1. **完善前端通用组件** - 加载状态、空状态、错误提示等
2. **优化任务轮询机制** - 使用 WebSocket 或优化轮询策略
3. **完善虚拟机详情页** - 展示完整性能指标和历史趋势
4. **告警管理功能** - 告警列表、确认、统计

### 中期 (3-4 周)

1. **报告管理功能** - 报告生成、查看、导出
2. **主题系统** - 亮色/暗色主题切换
3. **数据可视化优化** - 图表交互、大数据量处理
4. **响应式布局** - 适配不同分辨率

### 长期 (1-2 月)

1. **性能优化** - 虚拟滚动、懒加载、打包优化
2. **多语言支持** - i18n 国际化
3. **用户配置持久化** - 主题、布局等用户偏好
4. **自动化测试** - 前端单元测试、E2E 测试

---

## 文档索引

### 设计文档
- `docs/0.0.1/1-需求与规划/01-需求规范.md` - 需求规范
- `docs/0.0.1/1-需求与规划/02-用户故事.md` - 用户故事
- `docs/0.0.1/2-架构设计/01-架构设计.md` - 架构设计
- `docs/0.0.1/3-详细设计/04-接口设计.md` - 接口设计
- `docs/0.0.1/3-详细设计/05-前端设计.md` - 前端设计
- `docs/0.0.1/3-详细设计/06-前端UI交互设计.md` - UI交互设计
- `docs/0.0.1/6-部署与运维/01-部署指南.md` - 部署指南

### API 文档
- `api/0.0.1/README.md` - API 完整参考
- `api/0.0.1/types.ts` - TypeScript 类型定义
- `api/0.0.1/GUIDE.md` - 使用指南

### 测试文档
- `test/TEST_PLAN.md` - 测试计划
- `test/TEST_REPORT.md` - 单元测试与集成测试报告
- `test/TEST_REPORT_E2E.md` - 端到端测试报告

### 外部接口文档
- `docs/外部资料/UIS对外接口文档_R0886P05（转换版）.md` - H3C UIS API 参考