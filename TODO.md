# JustFit 后端开发 TODO

## 开发进度

### 阶段 1：连接管理 API 补充 ✅

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

### 验证

- [x] 编译验证 (`go build`) ✅ 通过

---

## 实施优先级

**P0（高）**: ✅ 完成

- 阶段 1：连接管理
- 阶段 2：采集任务管理
- 阶段 3：资源查询

**P1（中）**: ✅ 完成

- 阶段 4：分析服务
- 阶段 7：告警服务

**P2（低）**: ✅ 完成

- 阶段 5：报告服务
- 阶段 6：系统配置

---

## 新增文件清单

1. `internal/service/task_service.go` - 任务执行器实现
2. `internal/storage/settings_repo.go` - 系统配置仓储
3. `TODO.md` - 本文件

## 修改文件清单

1. `app.go` - 添加所有缺失的 API 方法
2. `internal/storage/models.go` - 添加 Settings 模型
3. `internal/storage/db.go` - 添加 Settings 表迁移和仓储

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