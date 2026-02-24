# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 当前版本状态

**版本**: v0.0.2
**状态**: 架构重构完成，前端适配待进行

### v0.0.2 完成项
- ✅ DTO 层 (15 个文件)
- ✅ Logger 结构化日志系统 (5 个文件)
- ✅ Errors 统一错误处理
- ✅ Service v2 层 (3 个服务)
- ✅ appdir 简化 (统一数据目录)
- ✅ 单元测试 (24 个测试用例通过)

### 待完成项
- ⏳ 前端类型定义迁移到 v2.ts
- ⏳ Service v2 集成到 app.go
- ⏳ 前端状态刷新问题修复
- ⏳ 集成测试补充

详见 `TODO.md`

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

# 运行测试并显示覆盖率
go test -cover ./...

# 运行 v2 单元测试
go test ./test/unit/...
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

每次完成任务后，必须进行以下检查：

### 1. 配置与文件管理

- [x] **appdir 统一管理**: 所有配置、数据库、日志文件使用 `appdir` 包获取路径
- [x] **统一数据目录**: 所有平台使用标准数据目录，不再区分开发/生产模式
- [ ] **权限控制**: 确保目录创建时有正确的权限 (0755)

### 2. 前后端接口对齐

- [ ] **字段名一致**: 后端 JSON tag 与前端类型定义完全一致（注意蛇形/驼峰）
- [ ] **字段类型一致**: Go 类型与 TypeScript 类型正确映射
- [ ] **必填字段**: 前端 `validate` 标签与后端验证一致
- [ ] **可选字段**: `omitempty` 在 JSON tag 和前端类型中正确处理
- [ ] **类型同步**: 后端 DTO 修改时同步更新 `frontend/src/types/v2.ts`

### 3. 数据库与数据结构

- [ ] **模型定义**: GORM Model 字段类型正确，有适当的索引
- [ ] **迁移影响**: 数据结构变更考虑向后兼容性
- [ ] **外键关系**: 关联关系正确定义
- [ ] **软删除**: 需要软删除的表使用 `gorm.DeletedAt`
- [ ] **时间戳**: `created_at`, `updated_at` 统一使用

### 4. 日志与错误处理

- [ ] **关键操作日志**: 创建、更新、删除操作有日志记录
- [ ] **错误日志**: 所有错误路径都有 `logger.Error()` 记录
- [ ] **结构化字段**: 日志包含足够的上下文信息 (id, name, type 等)
- [ ] **错误码**: 使用 `internal/errors` 包的预定义错误
- [ ] **错误链**: 使用 `Wrap()` 保留原始错误信息

### 5. 前端联动

- [ ] **API 调用**: 后端新增 API 时前端对应调用已更新
- [ ] **类型定义**: `frontend/src/types/v2.ts` 已同步更新
- [ ] **UI 更新**: 界面展示逻辑与新的数据结构匹配
- [ ] **错误处理**: 前端正确处理后端错误响应

### 6. 其他关键检查

- [ ] **编译通过**: `go build ./internal/...` 无错误
- [ ] **测试通过**: `go test ./test/unit/...` 全部通过
- [ ] **代码格式**: `go fmt ./...` 已执行
- [ ] **无 TODO**: 生产代码中不遗留 TODO/FIXME 注释
- [ ] **文档更新**: CLAUDE.md 或相关文档已更新

### 接口对齐示例

```go
// 后端 - internal/dto/response/connection.go
type ConnectionResponse struct {
    ID        uint       `json:"id"`         // 驼峰
    Name      string     `json:"name"`
    LastSync  *time.Time `json:"last_sync,omitempty"`  // 蛇形 + omitempty
}
```

```typescript
// 前端 - frontend/src/types/v2.ts
export interface ConnectionResponse {
    id: number              // 驼峰（前端）
    name: string
    last_sync?: string      // 蛇形（与后端 json tag 一致）
}
```

## 核心概念

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

### 命名规范

| 位置 | 规范 | 示例 |
|------|------|------|
| 后端 Go 结构体 | 驼峰 | `ConnectionResponse`, `CreateConnectionRequest` |
| 后端 Go 方法 | 驼峰 | `ListConnections()`, `GetByID(id uint)` |
| 后端 JSON tag | 蛇形 | `json:"last_sync,omitempty"` |
| 前端 TS 类型/接口 | 驼峰 | `ConnectionResponse`, `ListItem` |
| 前端 TS 属性 | 驼峰 | `lastSync`, `totalCount` |
| 数据库字段 | 蛇形 | `last_sync`, `created_at` |

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
