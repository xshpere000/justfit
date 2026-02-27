# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 硬性规则

**⚠️ 版本管理规则**  

1. **当前版本**: v0.0.2（以 `internal/version/version.go` 中的 `Version` 常量为准）
2. **禁止擅自创建新版本**: 除非用户明确要求"更新版本"或"发布新版本"，否则：
   - ❌ 不得在任何地方创建 "v0.0.3"、"v0.0.4" 等新版本章节
   - ❌ 不得在 TODO.md、CHANGELOG.md 或任何文档中添加新版本内容
   - ❌ 不得声称"已完成 v0.0.x 开发"
3. **当前开发原则**: 用户未要求版本迭代时，所有开发工作都是基于当前版本（v0.0.2）的增量改进
4. **版本更新流程**: 只有用户明确要求时，才能：
   - 修改 `internal/version/version.go` 中的 `Version` 常量
   - 在相关文档中创建新版本章节
   - 更新 CHANGELOG

**违反此规则是严重错误，会导致版本管理混乱。**

---

## 当前版本状态

**版本**: v0.0.2
**状态**: 生产就绪

### 核心特性

- ✅ **数据隔离架构** - 指标数据按任务隔离，支持独立分析
- ✅ **双平台支持** - vCenter 和 H3C UIS 统一处理
- ✅ **6 种指标完整采集** - CPU、内存、磁盘读写、网络收发
- ✅ **命名规范统一** - 全项目驼峰命名（首字母小写）
- ✅ **DTO + Service + Mapper** - v2 分层架构
- ✅ **结构化日志系统** - 统一的日志和错误处理

## 项目概述

JustFit 是一个基于 Wails v2 构建的桌面应用，用于云平台资源评估与优化。它支持 vCenter 和 H3C UIS 两个虚拟化平台，提供僵尸 VM 检测、Right Size 分析、潮汐模式检测和平台健康评分功能。

- **前端**: Vue 3 + TypeScript + Vite + Element Plus + ECharts
- **后端**: Go 1.24 + Wails v2
- **数据库**: SQLite (GORM)
- **构建**: `wails dev` / `wails build`

## 常用命令

### 开发命令

```bash
# 启动开发模式 (前端热重载 + 后端编译)
wails dev

# 构建生产版本
wails build

# 前端独立开发 (进入 frontend 目录)
cd frontend
npm run dev    # 启动 Vite 开发服务器
npm run build  # 构建前端
```

### 测试命令

```bash
# 运行所有测试
go test ./...

# 运行特定包的测试
go test ./internal/analyzer
go test ./internal/connector
go test ./internal/logger
go test ./internal/errors

# 运行测试并显示覆盖率
go test -cover ./...

# 运行 v2 单元测试
go test ./test/unit/...

# 运行集成测试
go test ./test/integration/...

# 运行 E2E 测试
go test ./test/e2e/...

# 测试 vCenter 连接器
go test ./test -run TestVCenter
```

### 其他命令

```bash
# 格式化代码
go fmt ./...
gofmt -w .

# 代码检查
go vet ./...

# 编译检查
go build ./internal/...
```

## 项目架构

### 分层架构

```
├── frontend/              # Vue 3 前端 (Wails Asset Server)
│   └── src/
│       ├── api/          # Wails 绑定 API 调用封装
│       ├── components/   # 通用 Vue 组件
│       ├── views/        # 页面组件
│       ├── stores/       # Pinia 状态管理
│       ├── router/       # Vue Router 配置
│       ├── types/        # TypeScript 类型定义
│       │   ├── v2.ts     # v2 版本类型定义（与后端 DTO 对齐）
│       └── utils/        # 工具函数
│
├── internal/
│   ├── dto/              # v2 数据传输对象层
│   │   ├── response/     # 响应 DTO
│   │   ├── request/      # 请求 DTO
│   │   └── mapper/       # 数据映射器
│   │
│   ├── service/v2/       # v2 服务层（使用 DTO）
│   │
│   ├── logger/           # 结构化日志系统
│   ├── errors/           # 统一错误处理
│   ├── appdir/           # 应用目录管理（统一配置、数据库、日志位置）
│   │
│   ├── analyzer/         # 分析算法引擎
│   ├── connector/        # 云平台连接器
│   ├── etl/              # 数据采集与 ETL
│   ├── storage/          # 数据持久化 (GORM + SQLite)
│   ├── task/             # 任务调度系统
│   ├── report/           # 报告生成
│   ├── security/         # 安全模块
│   └── app.go            # 主应用结构 (Wails 绑定)
│
├── test/
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   ├── api/              # API 测试
│   ├── e2e/              # E2E 测试
│   └── fixtures/         # 测试辅助
│
├── main.go               # Wails 入口
├── app.go                # 应用服务实现 (导出到前端)
├── wails.json            # Wails 配置
└── go.mod                # Go 依赖管理
```

### 应用目录管理 (appdir)

**重要**: 所有配置文件、数据库、日志文件通过 `internal/appdir` 包统一管理。

```go
// 获取应用数据目录
appdir.GetAppDataDir()

// 获取日志目录
appdir.GetLogDir()

// 获取数据库路径
appdir.GetDBPath()

// 确保目录存在
appdir.EnsureAppDirs()
```

**数据目录位置** (所有平台统一使用标准目录):

- **Windows**: `%APPDATA%\justfit` (例如: `C:\Users\xxx\AppData\Roaming\justfit`)
- **macOS**: `~/Library/Application Support/justfit`
- **Linux**: `~/.local/share/justfit`

**自定义目录**: 设置环境变量 `JUSTFIT_DATA_DIR` 可指定自定义目录。

**目录结构**:

```
justfit/
├── justfit.db          # SQLite 数据库
├── credentials.enc     # 加密凭据
├── .key               # 加密密钥
└── logs/              # 日志目录
    ├── app.log        # 应用日志
    └── task.log       # 任务日志
```

### v2 架构 (DTO + Service + Mapper)

```
请求 → app.go (Wails绑定) → Service v2 → Mapper → Storage → 数据库
                     ↓                ↓           ↓
                  Logger         DTO        Domain Model
                     ↓                ↓
                   Errors         Response
```

- **DTO (Data Transfer Object)**: 前后端数据传输的标准格式
- **Mapper**: Storage Model ↔ DTO 转换
- **Service v2**: 业务逻辑，使用 DTO 和 Logger/Errors

## 代码审查检查点

### 快速检查（每次提交必查）

```bash
# 1. 编译检查
go build ./internal/...

# 2. 字段对齐检查
grep -rn 'json:"' internal/dto/ app.go | grep -E '[A-Z]{2,}"'  # 不应有全大写 JSON tag

# 3. 单位字段检查
grep -rn 'json:.*[MGT][hbHB]' --include="*.go" | grep -vE '(Mhz|Mb|Gb)"'  # 单位应小写

# 4. 测试通过
go test ./test/unit/...
```

### 完整检查（发布前执行）

- [ ] 快速检查项全部通过
- [ ] **数据库**: 外键关系正确，使用 CASCADE 删除
- [ ] **日志完整**: 关键操作有日志记录，包含足够上下文
- [ ] **错误处理**: 使用 `internal/errors` 包，错误链完整
- [ ] **前端联动**: `frontend/src/types/v2.ts` 已同步，API 调用已更新
- [ ] **文档更新**: CLAUDE.md 相关部分已更新
- [ ] **无 TODO**: 生产代码中不遗留 TODO/FIXME 注释

---

## ETL 数据采集流程

### 采集架构

```
用户创建任务 → TaskService 创建任务记录
                          ↓
          ETL.Collector 连接平台采集数据
                          ↓
          ProcessVMMetrics 保存指标（关联 TaskID）
                          ↓
          任务进度实时推送 (Progress Channel)
                          ↓
          采集完成 → 触发分析任务 (可选)
```

### 支持的指标类型

| 指标类型 | 说明 | 单位 |
|---------|------|-----|
| `cpu` | CPU 使用率 | MHz |
| `memory` | 内存使用量 | 字节 |
| `disk_read` | 磁盘读速率 | bytes/s |
| `disk_write` | 磁盘写速率 | bytes/s |
| `net_rx` | 网络接收速率 | bytes/s |
| `net_tx` | 网络发送速率 | bytes/s |

### 数据隔离特性

- **采集隔离**: 每个任务采集的指标数据独立存储（通过 TaskID）
- **查询隔离**: 分析引擎只查询该任务的指标数据
- **删除隔离**: 删除任务时 CASCADE 删除关联指标数据
- **独立分析**: 使用 `taskID=0` 查询所有历史数据

### 关键文件

- `internal/etl/collector.go` - 指标采集器
- `internal/etl/etl.go` - ETL 处理流程
- `internal/connector/vcenter.go` - vCenter 连接器
- `internal/connector/uis.go` - H3C UIS 连接器

---

## 分析算法配置

### 僵尸 VM 检测

检测长期低使用的虚拟机，识别可能的资源浪费。

```go
type ZombieVMConfig struct {
    DaysLowUsage         int     // 低使用率天数阈值（默认 30 天）
    CpuThreshold         float64 // CPU 使用率阈值（默认 10%）
    MemoryThreshold      float64 // 内存使用率阈值（默认 20%）
    DiskIoThreshold      float64 // 磁盘 I/O 阈值（默认 5%）
    NetworkThreshold     float64 // 网络流量阈值（默认 5%）
    ConfidenceThreshold  float64 // 置信度阈值（默认 0.7）
}
```

**分析逻辑**:

- 统计过去 N 天内 CPU/内存/磁盘/网络使用率低于阈值的比例
- 计算置信度（基于低使用天数和指标一致性）
- 提供证据链（低使用天数、各指标平均使用率）

### Right Size 分析

分析 VM 资源配置是否合理，提供调整建议。

```go
type RightSizeConfig struct {
    CpuBufferPercent     float64 // CPU 缓冲百分比（默认 20%）
    MemoryBufferPercent  float64 // 内存缓冲百分比（默认 20%）
    HighUsageThreshold   float64 // 高使用率阈值（默认 85%）
    LowUsageThreshold    float64 // 低使用率阈值（默认 30%）
    MinConfidence        float64 // 最小置信度（默认 0.6）
}
```

**调整类型**:

- `up`: 资源不足，建议升级
- `down`: 资源过剩，建议降级
- `none`: 配置合理，无需调整

**风险等级**:

- `low`: 低风险，建议可信
- `medium`: 中等风险，需评估影响
- `high`: 高风险，建议谨慎

### 潮汐模式检测

检测 VM 资源使用的周期性模式，识别潮汐特征。

```go
type TidalConfig struct {
    PeakThreshold        float64 // 峰值阈值（默认 80%）
    ValleyThreshold      float64 // 谷值阈值（默认 30%）
    StabilityThreshold   float64 // 稳定性阈值（默认 0.7）
    MinDays              int     // 最小分析天数（默认 7 天）
}
```

**模式类型**:

- `daily`: 日周期模式（工作日/周末差异）
- `weekly`: 周周期模式（周一到周五变化）
- `none`: 无明显周期模式

### 健康评分

评估整体云平台的资源健康状态。

```go
type HealthConfig struct {
    OvercommitThreshold  float64 // 超分阈值（默认 150%）
    HotspotThreshold     float64 // 热点阈值（默认 90%）
    BalanceThreshold     float64 // 平衡阈值（默认 0.6）
}
```

**评分维度**:

- 资源平衡度: CPU/内存分配是否均衡
- 超分风险: 资源超分配程度
- 热点集中度: 负载是否过度集中

**健康等级**:

- `excellent`: 90-100 分
- `good`: 75-89 分
- `fair`: 60-74 分
- `poor`: 0-59 分

---

## 前后端接口对齐（⚠️ 硬性要求）

**⚠️ 字段名大小写不匹配是严重 BUG，会导致数据丢失！每次修改字段必须执行以下检查：**

- [ ] **字段名完全一致**: 后端 JSON tag 与前端类型定义**逐字符匹配**
  - 检查命令：`grep -rn 'json:"' internal/dto/ | grep -oE 'json:"[^"]*"'`
  - 对比前端：`grep -rn 'interface.*{' frontend/src/types/`
  - 验证：后端 `json:"vmCount"` 必须匹配前端 `vmCount: number`（不是 `VMCount`）

- [ ] **字段类型一致**: Go 类型与 TypeScript 类型正确映射
  - `uint/int` ↔ `number`
  - `string` ↔ `string`
  - `bool` ↔ `boolean`
  - `time.Time` ↔ `string` (ISO 8601)

- [ ] **必填字段**: 前端 `validate` 标签与后端验证一致
- [ ] **可选字段**: `omitempty` 在 JSON tag 和前端类型中正确处理（`?:` 标记）
- [ ] **类型同步**: 后端 DTO 修改时**必须**同步更新 `frontend/src/types/v2.ts`、`frontend/src/types/api.ts`
- [ ] **组件使用验证**: 搜索所有使用该字段的前端组件，确保字段名一致
  - 检查命令：`grep -rn '字段名' frontend/src/views/ frontend/src/stores/`

**🔍 字段对齐检查清单（每次修改字段后执行）**:

```bash
# 1. 搜索后端 JSON tag
grep -rn 'json:".*字段"' internal/ app.go

# 2. 搜索前端类型定义
grep -rn '字段名:' frontend/src/types/

# 3. 搜索前端组件使用
grep -rn '字段名' frontend/src/views/ frontend/src/stores/

# 4. 编译验证
go build ./internal/... && cd frontend && npm run build
```

**验证示例**:

```typescript
// 前端发送数据
const data = {
  vmCount: 5,           // 驼峰小写开头
  selectedVMs: ['vm1'], // 缩写 VM 全大写
  connectionId: 1       // 驼峰小写开头
}

// 后端接收
type Config struct {
  VMCount     int      `json:"vmCount"`       // 匹配
  SelectedVMs []string `json:"selectedVMs"`   // 匹配
  ConnectionID uint     `json:"connectionId"` // 匹配
}
```

---

## 核心概念

### 数据隔离架构

指标数据按任务隔离，确保不同采集任务的性能数据互不影响：

```go
// VMMetric 模型包含 TaskID 字段
type VMMetric struct {
    ID        uint      `json:"id"`
    TaskID    uint      `json:"taskId"`    // 关联的任务 ID
    VMID      uint      `json:"vmId"`      // 关联的虚拟机 ID
    MetricType string   `json:"metricType"` // cpu, memory, disk_read, disk_write, net_rx, net_tx
    Value     float64   `json:"value"`
    Timestamp time.Time `json:"timestamp"`
}
```

**关键特性**:

- **采集隔离**: 每个任务采集的指标数据独立存储
- **查询隔离**: 分析引擎只查询该任务的指标数据
- **删除隔离**: 删除任务时自动清理关联的指标数据（CASCADE）
- **独立分析**: 使用 `taskID=0` 查询所有历史数据（用于独立分析功能）

**使用示例**:

```go
// 按任务查询指标
metrics, err := repos.Metric.ListByTaskAndVMAndType(taskID, vmID, "cpu", start, end)

// 删除任务的所有指标
repos.Metric.DeleteByTaskID(taskID)

// 独立分析（查询所有数据）
metrics, err := repos.Metric.ListByTaskAndVMAndType(0, vmID, "cpu", start, end)
```

### 连接器接口

所有云平台连接器实现 `connector.Connector` 接口:

```go
type Connector interface {
    Close() error
    TestConnection() error
    GetClusters() ([]ClusterInfo, error)
    GetHosts() ([]HostInfo, error)
    GetVMs() ([]VMInfo, error)
    GetVMMetrics(...) (*VMMetrics, error)
}
```

### 任务调度系统

- 任务类型: `collection` (采集), `analysis` (分析)
- 任务状态: `pending` → `running` → `completed`/`failed`/`cancelled`
- 任务执行器 (`Executor`) 接口: 支持自定义任务执行逻辑
- 任务结果通过进度通道实时推送

### 日志系统使用

```go
import "justfit/internal/logger"

// 获取 logger
log := logger.With(logger.Str("service", "connection"))

// 记录日志
log.Debug("调试信息", logger.String("name", name))
log.Info("普通信息", logger.Int("count", count))
log.Warn("警告信息", logger.String("reason", reason))
log.Error("错误信息", logger.Err(err))

// 子日志器（带预设字段）
childLog := log.With(logger.Uint("connection_id", id))
```

### 错误处理使用

```go
import apperrors "justfit/internal/errors"

// 使用预定义错误
return apperrors.ErrConnectionNotFound

// 包装错误
return apperrors.ErrInternalError.Wrap(err, "创建连接失败")

// 判断错误类型
if apperrors.IsNotFound(err) {
    // 处理不存在的情况
}
```

## 重要约定

### 强制命名规范

**本项目使用混合命名策略，在 API 层统一为驼峰，数据库层保持 SQL 约定**

| 位置 | 规范 | 示例 |
|------|------|------|
| 后端 Go 结构体 | 驼峰 | `ConnectionResponse`, `ConnectionID` |
| 后端 Go 方法 | 驼峰 | `ListConnections()`, `GetByID(id uint)` |
| 后端 JSON tag | **驼峰（首字母小写）** | `json:"connectionId"`, `json:"vmCount"` |
| 前端 TS 类型/接口 | 驼峰 | `ConnectionResponse`, `connectionId` |
| 前端 TS 属性 | **驼峰（首字母小写）** | `connectionId`, `vmCount` |
| 数据库列名 | **蛇形** | `connection_id`, `created_at` (SQL 约定) |
| 数据库表名 | 蛇形复数 | `connections`, `assessment_tasks` |

**⚠️ 关键规则 - 字段命名大小写敏感性**：

1. **前端 TypeScript 属性必须首字母小写**（驼峰命名）

   ```typescript
   // 正确
   vmCount: number
   collectedVMCount: number
   selectedVMs: string[]
   connectionId: number

   // 错误 - 会导致后端无法解析
   VMCount: number      // Go 期望 json:"vmCount" 不是 "VMCount"
   ConnectionID: number // Go 期望 json:"connectionId" 不是 "ConnectionID"
   ```

2. **后端 JSON tag 必须首字母小写**

   ```go
   // 正确
   type CollectionConfig struct {
       VMCount     int      `json:"vmCount"`       // 首字母小写
       SelectedVMs []string `json:"selectedVMs"`    // 后续单词首字母大写
   }

   // 错误
   type CollectionConfig struct {
       VMCount     int      `json:"VMCount"`       // 前端无法正确解析
   }
   ```

3. **缩写词处理（VM, ID, URL 等）**
   - **双字母缩写**：全部大写 → `VM`, `ID`, `IP`
   - **三字母缩写**：全部大写 → `CPU`, `GPU`
   - **JSON tag**：缩写保持大写，但整体驼峰（首字母小写）
     - `vmCount` (VM 虚拟机)
     - `cpuCount` (CPU 处理器)
     - `ipAddress` (IP 地址)
     - `userId` (用户 ID)
     - `taskId` (任务 ID)
     - `selectedVMs` (VM 复数，缩写保持大写)
   - **错误示例**：
     - ❌ `Vms` → 应该是 `VMs`（两个字母都大写）
     - ❌ `vmcount` → 应该是 `vmCount`（驼峰）
     - ❌ `CPUCount` → 应该是 `cpuCount`（首字母小写）

### 单位字段命名规则

**单位统一使用小写缩写**（保持一致性，避免混淆）：

| 类型 | JSON tag 格式 | 示例 | 说明 |
|------|--------------|------|------|
| 频率 | `xxxMhz` | `cpuMhz` | 小写 h |
| 内存（MB） | `xxxMb` | `memoryMb`, `currentMemoryMb` | 小写 b |
| 内存（GB） | `xxxGb` | `memoryGb`, `totalMemoryGb` | 小写 b |
| 数量 | `xxxCount` | `vmCount`, `cpuCount` | Count 后缀 |
| 字节数 | `xxxMemory` | `totalMemory`, `freeMemory` | 原始字节数 |

**重要**：

- ✅ **Go 结构体字段** 使用 PascalCase + 大写单位：`MemoryMB`, `CPUMHz`, `MemoryGB`
- ✅ **JSON tag** 使用 camelCase + 小写单位：`memoryMb`, `cpuMhz`, `memoryGb`
- ✅ **TypeScript 属性** 使用 camelCase + 小写单位：`memoryMb`, `cpuMhz`

```go
// 正确示例
type VMResponse struct {
    MemoryMB  int32   `json:"memoryMb"`   // 字段名大写 MB，JSON 小写 Mb
    MemoryGB  float64 `json:"memoryGb"`   // 字段名大写 GB，JSON 小写 Gb
    CPUMHz    int32   `json:"cpuMhz"`     // 字段名大写 MHz，JSON 小写 Mhz
}
```

**常见混淆字段对照表**：

| 混淆字段 | 正确写法 | 错误写法 |
|---------|---------|---------|
| CPU 频率 | `cpuMhz` | `cpuMHz`, `CPUMhz` |
| 内存 MB | `memoryMb` | `memoryMB`, `MemoryMB` |
| 内存 GB | `memoryGb` | `memoryGB`, `MemoryGB` |
| VM 数量 | `vmCount` | `VMCount`, `vmcount` |
| CPU 数量 | `cpuCount` | `CPUCount`, `cpucount` |
| IP 地址 | `ipAddress` | `IPAddress`, `IPaddress` |
| 用户 ID | `userId` | `UserID`, `user_Id` |

**数据流验证顺序**（每次修改字段后必须执行）:

```
后端 DTO → 后端 JSON tag → 前端类型定义 → 前端组件使用 → 前端 API 调用
   ↓            ↓               ↓               ↓              ↓
 验证类型    验证首字母小写   验证完全一致    验证使用正确   验证传递正确
```

**数据流转换**（GORM 自动处理）:

```
Go 对象            JSON                前端 TS
{                    {                    {
  ConnectionID        "connectionId": 123,   connectionId: 123,
  Name: "test"        "name": "test",        name: "test"
}                    }                    }
       ↓                    ↓                    ↓
数据库 (蛇形列名)     HTTP API (驼峰)        浏览器
connection_id=123
name="test"
```

**设计理由**:

- API 层（JSON/TypeScript）使用驼峰：代码一致，易读易写
- 数据库列名使用蛇形：符合 SQL 传统，工具兼容性好
- GORM 自动处理转换，无需手动映射

### 时间处理

- 后端统一使用 `time.Time`
- API 响应中时间自动格式化为 ISO 8601 字符串
- 前端使用 dayjs 处理时间格式化

### 凭据安全

- 数据库 `connections` 表密码字段为空
- 实际密码通过 `security.CredentialManager` 加密存储
- 加密算法: AES-256-GCM

## 前后端类型映射

| Go 类型 | TypeScript 类型 | JSON 序列化 |
|---------|----------------|-------------|
| `uint` | `number` | 数字 |
| `int` | `number` | 数字 |
| `float64` | `number` | 数字 |
| `string` | `string` | 字符串 |
| `bool` | `boolean` | true/false |
| `time.Time` | `string` | ISO 8601 |
| `*time.Time` | `string \| undefined` | ISO 8601 或 null |
| `[]T` | `T[]` | 数组 |
| `map[K]V` | `Record<K, V>` | 对象 |

## 扩展指南

### 添加新的 API 端点

1. 在 `internal/dto/response/` 添加响应 DTO
2. 在 `internal/dto/request/` 添加请求 DTO
3. 在 `internal/dto/mapper/` 添加 Mapper
4. 在 `internal/service/v2/` 添加 Service 方法
5. 在 `app.go` 添加 Wails 绑定方法
6. 更新 `frontend/src/types/v2.ts`
7. 添加前端 API 调用
8. 添加单元测试

### 添加新的云平台支持

1. 在 `internal/connector/` 创建新文件，实现 `Connector` 接口
2. 在 `connector.go` 的 `NewConnector` 中注册平台类型
3. 更新前端平台选择下拉菜单
4. 添加对应的数据采集测试

### vCenter 指标采集注意事项

vCenter 性能指标采集的关键配置：

```go
// internal/connector/vcenter.go
func (c *VCenterClient) GetVMMetrics(...) (*VMMetrics, error) {
    // 1. 使用实时间隔（20 秒）而非历史间隔（5 分钟）
    spec.Interval = duration20s  // 正确
    // spec.Interval = duration5m  // 错误：磁盘/网络指标不可用

    // 2. 使用空字符串获取聚合数据
    metricInfo.Instance = ""  // 正确：获取聚合数据
    // metricInfo.Instance = "*"  // 错误：返回空数据

    // 支持的指标类型
    // - cpu: CPU 使用率 (MHz)
    // - memory: 内存使用 (字节)
    // - disk_read: 磁盘读速率
    // - disk_write: 磁盘写速率
    // - net_rx: 网络接收速率
    // - net_tx: 网络发送速率
}
```

**关键点**：

- 实时间隔（`Realtime`）才提供全部 6 种指标
- 历史间隔（`Historical`）仅提供 CPU 和内存指标
- 使用空字符串 `""` 作为实例名获取聚合数据

---

## 调试技巧

### 启用详细日志

```go
// 在 main.go 或 app.go 开头
log.SetLevel(logger.DebugLevel)
```

### 数据库检查

```bash
# 查看数据库位置
echo $JUSTFIT_DATA_DIR  # 或查看 appdir.GetDBPath() 返回值

# 使用 sqlite3 查询
sqlite3 ~/.local/share/justfit/justfit.db
sqlite3> SELECT * FROM assessment_tasks;
```

### 前端调试

```typescript
// 在浏览器控制台
import { useAppStore } from '@/stores/app'
const app = useAppStore()
console.log('当前连接:', app.connections)
```

### Wails 开发模式问题

```bash
# 清理缓存
rm -rf frontend/node_modules/.vite
wails dev -clean
```

### 常见陷阱

#### 陷阱 1: 字段名大小写不匹配

**问题**: 前端使用 `VMCount`（大写 V），后端期望 `vmCount`（小写 v）
**后果**: 后端无法解析字段，数据丢失

**检查命令**:

```bash
# 检查所有后端 JSON tag
grep -rn 'json:"' internal/dto/ app.go | grep -vE 'json:"[a-z]'

# 检查所有前端类型定义
grep -rn '[A-Z][a-z]+:' frontend/src/types/ | grep -v 'interface\|type\|export'
```

#### 陷阱 2: 单位字段命名混淆

**问题**: `cpuMhz` vs `cpuMHz` vs `CPUMhz`
**后果**: 前后端字段不匹配，数据无法正确显示

**检查命令**:

```bash
# 检查所有单位字段的 JSON tag（应全部为小写单位）
grep -rn 'json:.*[MGT][hbHB]' --include="*.go" | grep -v '//'

# 查找不一致的单位命名
grep -rn 'json:".*MHz"' --include="*.go"   # 应该是 Mhz
grep -rn 'json:".*GB"' --include="*.go"    # 应该是 Gb
grep -rn 'json:".*MB"' --include="*.go"    # 应该是 Mb
```

#### 陷阱 3: 修改后端 DTO 但未更新前端

**检查清单**:

- [ ] `internal/dto/response/*.go` 修改后
- [ ] `frontend/src/types/v2.ts` 已同步
- [ ] `frontend/src/types/api.ts` 已同步
- [ ] `frontend/src/stores/*.ts` 已同步
- [ ] 使用该字段的 Vue 组件已更新
