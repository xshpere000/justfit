# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 当前版本状态

**版本**: v0.0.2
**状态**: 命名规范统一完成，前后端对齐

### v0.0.2 完成项

- ✅ DTO 层 (15 个文件)
- ✅ Logger 结构化日志系统 (5 个文件)
- ✅ Errors 统一错误处理
- ✅ Service v2 层 (3 个服务)
- ✅ appdir 简化 (统一数据目录)
- ✅ 单元测试 (24 个测试用例通过)
- ✅ **命名规范统一为驼峰 (全项目)**
- ✅ **字段对齐检查规则写入 CLAUDE.md (硬性要求)**

### 关键 BUG 修复记录

**2026-02-26: 字段名大小写不匹配导致数据丢失**

- **问题**: 前端使用 `VMCount`（大写 V），后端期望 `vmCount`（小写 v）
- **影响**: 创建采集任务时，VM 数量数据无法被后端解析
- **修复**:
  - 统一所有字段为驼峰命名（首字母小写）
  - 修复文件: 11 个前端文件 + 6 个后端文件
  - 添加字段对齐检查到 CLAUDE.md 作为硬性规则
- **教训**: 字段名大小写敏感性是隐蔽但严重的 BUG 源头

### 待完成项

- ⏳ 集成测试补充
- ⏳ 前端状态刷新问题修复

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

### 2. 前后端接口对齐（⚠️ 硬性要求）

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

### 7. 字段对齐验证（⚠️ 硬性要求，不可跳过）

**每次修改任何字段后，必须执行以下验证步骤**：

```bash
# 步骤 1: 后端 JSON tag 检查
# 确保所有 JSON tag 使用驼峰命名（首字母小写）
grep -rn '`json:"' internal/dto/ app.go | grep -E '[A-Z]{2,}"'  # 不应有全大写的 JSON tag

# 步骤 2: 前端类型定义检查
# 确保接口属性使用驼峰命名（首字母小写）
grep -rn 'interface.*{' frontend/src/types/*.ts

# 步骤 3: 前后端字段对比
# 提取所有后端 JSON tag
grep -rh 'json:"' internal/dto/ app.go | grep -oE 'json:"[^"]*"' | sort -u > /tmp/backend_fields.txt

# 提取所有前端类型字段
grep -rh '^\s*[a-zA-Z].*:' frontend/src/types/*.ts | grep -oE '[a-zA-Z][a-zA-Z0-9]*:' | sed 's/:$//' | sort -u > /tmp/frontend_fields.txt

# 对比差异（手动检查）

# 步骤 4: 编译验证
go build ./internal/... && cd frontend && npm run build
```

**常见错误模式**（避免这些）：

| 错误模式 | 正确模式 | 原因 |
|---------|---------|------|
| `VMCount: number` | `vmCount: number` | 首字母必须小写 |
| `json:"VMCount"` | `json:"vmCount"` | JSON tag 首字母小写 |
| `Vms` | `VMs` | 双字母缩写全大写 |
| `ConnectionID` | `connectionId` | 前端属性必须驼峰小写开头 |

**验证示例**：

```typescript
// 前端发送数据
const data = {
  vmCount: 5,           // ✅ 驼峰小写开头
  selectedVMs: ['vm1'], // ✅ 缩写 VM 全大写
  connectionId: 1       // ✅ 驼峰小写开头
}

// 后端接收
type Config struct {
  VMCount     int      `json:"vmCount"`       // ✅ 匹配
  SelectedVMs []string `json:"selectedVMs"`   // ✅ 匹配
  ConnectionID uint     `json:"connectionId"` // ✅ 匹配
}
```

### 接口对齐示例

```go
// 后端 - internal/dto/response/connection.go
type ConnectionResponse struct {
    ID        uint       `json:"id"`                 // 驼峰
    Name      string     `json:"name"`
    LastSync  *time.Time `json:"lastSync,omitempty"`  // 驼峰 + omitempty
}

// GORM 自动映射: LastSync → 数据库列 last_sync (蛇形)
// JSON 序列化: LastSync → JSON 字段 lastSync (驼峰)
```

```typescript
// 前端 - frontend/src/types/v2.ts
export interface ConnectionResponse {
    id: number              // 驼峰，匹配后端 JSON tag
    lastSync?: string       // 驼峰，匹配后端 JSON tag (数据库列名是 last_sync)
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
   // ✅ 正确
   vmCount: number
   collectedVMCount: number
   selectedVMs: string[]
   connectionId: number

   // ❌ 错误 - 会导致后端无法解析
   VMCount: number      // Go 期望 json:"vmCount" 不是 "VMCount"
   ConnectionID: number // Go 期望 json:"connectionId" 不是 "ConnectionID"
   ```

2. **后端 JSON tag 必须首字母小写**

   ```go
   // ✅ 正确
   type CollectionConfig struct {
       VMCount     int      `json:"vmCount"`       // 首字母小写
       SelectedVMs []string `json:"selectedVMs"`    // 后续单词首字母大写
   }

   // ❌ 错误
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
// ✅ 正确示例
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

1. **数据流验证顺序**（每次修改字段后必须执行）

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

## 常见陷阱和解决方案

### 陷阱 1: 字段名大小写不匹配

**问题**：前端使用 `VMCount`（大写 V），后端期望 `vmCount`（小写 v）
**后果**：后端无法解析字段，数据丢失
**解决方案**：

```bash
# 检查所有后端 JSON tag
grep -rn 'json:"' internal/dto/ app.go | grep -vE 'json:"[a-z]'

# 检查所有前端类型定义
grep -rn '[A-Z][a-z]+:' frontend/src/types/ | grep -v 'interface\|type\|export'
```

### 陷阱 2: 缩写词大小写错误

**问题**：`Vms` vs `VMs`
**规则**：

- 双字母缩写全大写：`VM`, `ID`, `IP`, `CPU`
- 复数形式：`VMs`, `IDs`（缩写保持大写）
- 驼峰命名：`numVMs`, `selectedVMs`, `vmCount`

### 陷阱 2.5: 单位字段命名混淆

**问题**：`cpuMhz` vs `cpuMHz` vs `CPUMhz`，`memoryGb` vs `memoryGB`
**后果**：前后端字段不匹配，数据无法正确显示
**规则**：

- **JSON tag**：单位使用小写 → `cpuMhz`, `memoryGb`, `memoryMb`
- **Go 字段名**：单位使用大写 → `CPUMHz`, `MemoryGB`, `MemoryMB`
- **TypeScript**：与 JSON tag 保持一致 → `cpuMhz`, `memoryGb`

**检查命令**：

```bash
# 检查所有单位字段的 JSON tag（应全部为小写单位）
grep -rn 'json:.*[MGT][hbHB]' --include="*.go" | grep -v '//'

# 查找不一致的单位命名
grep -rn 'json:".*MHz"' --include="*.go"   # 应该是 Mhz
grep -rn 'json:".*GB"' --include="*.go"    # 应该是 Gb
grep -rn 'json:".*MB"' --include="*.go"    # 应该是 Mb
```

### 陷阱 3: 修改后端 DTO 但未更新前端

**问题**：后端修改了字段名或类型，前端类型定义未同步
**检查清单**：

- [ ] `internal/dto/response/*.go` 修改后
- [ ] `frontend/src/types/v2.ts` 已同步
- [ ] `frontend/src/types/api.ts` 已同步
- [ ] `frontend/src/stores/*.ts` 已同步
- [ ] 使用该字段的 Vue 组件已更新

### 陷阱 4: 可选字段处理不当

**问题**：后端 `omitempty` 但前端未用 `?` 标记可选
**正确做法**：

```go
// 后端
type TaskResponse struct {
  VMCount int `json:"vmCount,omitempty"`
}
```

```typescript
// 前端
interface TaskResponse {
  vmCount?: number  // 必须用 ? 标记可选
}
```

### 调试技巧

**1. 启用详细日志查看数据传输**

```typescript
console.log('[DEBUG] 发送数据:', JSON.stringify(data))
```

**2. 使用浏览器开发工具**

- Network 标签查看请求 payload
- 确认字段名与后端期望一致

**3. 后端日志验证**

```go
log.Debug("接收配置", applogger.Any("config", config))
```
