# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

JustFit 是一个**桌面端云平台资源评估与优化工具**，基于 **Electron** + **Python FastAPI** + **Vue 3** 构建。

### 核心功能
- **数据采集**: 连接 VMware vCenter/H3C UIS，采集集群/主机/虚拟机资源与性能指标
- **智能分析**: 僵尸VM检测、Right Size优化、潮汐模式识别、平台健康评分
- **报告生成**: Excel + PDF 双格式专业评估报告
- **评估模式**: 安全/节省/激进/自定义四种预设模式

### 技术栈
- **桌面框架**: Electron 34 (Node.js)
- **前端**: Vue 3 + TypeScript + Element Plus + ECharts + Vite
- **后端**: Python 3.14 + FastAPI + SQLAlchemy (aiosqlite，无 Alembic)
- **数据库**: SQLite
- **通信**: HTTP REST API（camelCase JSON）

---

## 常用命令

### 开发模式

```bash
# Linux/macOS - 使用 Makefile
make dev              # 同时启动前后端 (端口: 后端22631, 前端22632)
make build-all        # 完整打包（前端 + 后端 exe + Electron）
make build-frontend   # 仅打包前端
make build-backend    # 仅打包后端（Python → exe）
make package-electron # 基于已打包前后端生成 Electron 安装包
make test             # 运行所有后端测试
make test-frontend    # 运行前端测试
make clean            # 清理构建产物

# 或直接运行脚本
./scripts/dev/dev-linux.sh    # Linux/macOS 开发模式 (绑定 0.0.0.0)
./scripts/dev/dev-windows.sh  # Windows Git Bash 开发模式 (绑定 0.0.0.0)
./scripts/build/build-all.sh  # 生产构建
```

### 分别启动（调试用）

```bash
# 后端 (FastAPI) - 端口 22631
cd backend
python -m uvicorn app.main:app --reload --port 22631 --host 0.0.0.0
# API 文档: http://localhost:22631/docs

# 前端 (Vite Dev Server) - 端口 22632
cd frontend
npm run dev -- --host 0.0.0.0 --port 22632
# 前端地址: http://localhost:22632
```

**注意**: 开发模式下后端使用端口 22631，前端使用端口 22632。

### 停止开发服务

```bash
# Linux/macOS - 停止所有开发服务
pkill -f "uvicorn app.main:app"      # 停止后端
pkill -f "vite.*22632"               # 停止前端

# 或使用 Ctrl+C 在运行 dev-linux.sh 的终端中停止
```

```bash
# Windows Git Bash - 停止所有开发服务
taskkill //F //IM python.exe         # 停止后端
taskkill //F //IM node.exe           # 停止前端

# 或使用 Ctrl+C 在运行 dev-windows.sh 的终端中停止
```

### 测试命令

```bash
# 后端测试 - 从项目根目录运行
# Linux/macOS 使用 python3.14；Windows 使用 python（取决于安装方式）
cd backend && PYTHONPATH=. python3.14 -m pytest tests/ -v                           # 所有后端测试
cd backend && PYTHONPATH=. python3.14 -m pytest tests/backend/integration/ -v -s   # 集成测试（带输出）
cd backend && PYTHONPATH=. python3.14 -m pytest tests/backend/e2e/ -v -s           # E2E 测试
cd backend && PYTHONPATH=. python3.14 -m pytest tests/backend/integration/test_connectors.py::test_vcenter_connection -v -s  # 单个测试

# 或使用 Makefile
make test              # 运行所有后端测试
make test-frontend     # 运行前端测试

# 前端测试
cd frontend
npm test               # Vitest 交互模式
npm run test:run       # 运行一次
npm run test:coverage  # 带覆盖率报告
```

### 依赖安装

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 代码质量检查

```bash
# 后端 - 代码检查和格式化
cd backend
ruff check .                # 检查代码问题
ruff check . --fix          # 自动修复问题
ruff format .               # 格式化代码
mypy app/                   # 类型检查

# 前端 - 代码检查和格式化
cd frontend
npm run test:coverage       # 测试覆盖率报告
```

---

## 架构与代码组织

### 整体架构

```
Electron Shell
├── Renderer Process (Vue 3 + TypeScript)
│   └── HTTP API → http://localhost:22631/api/*
└── Main Process (Node.js)
    └── spawn → Python FastAPI (localhost:22631)
        └── SQLite Database (~/.local/share/justfit/justfit.db)
```

### 目录结构概览

```
backend/app/
├── routers/        # API 路由 (/api/connections, /api/tasks, 等)
├── services/       # 业务逻辑层 (collection.py, analysis.py, task.py)
├── models/         # SQLAlchemy 数据模型
├── schemas/        # Pydantic DTO (请求/响应)
├── connectors/     # 平台连接器 (vcenter.py, uis.py)
├── analyzers/      # 分析算法 (idle_detector.py, rightsize.py, resource_analyzer.py, health.py, modes.py)
├── report/         # 报告生成 (excel.py, pdf.py, builder.py)
├── repositories/   # 数据访问层
├── security/       # 凭证加密 (credentials.py)
└── core/           # 核心配置 (database.py, errors.py, logging.py, migration.py)

frontend/src/
├── api/            # HTTP API 客户端
├── stores/         # Pinia 状态管理
├── views/          # 页面组件
├── components/     # 通用组件
├── composables/    # Vue 组合式函数
├── types/          # TypeScript 类型定义
├── router/         # Vue Router 配置
└── utils/          # 工具函数

electron/
├── main.ts         # Electron 主进程入口
├── preload.ts      # 预加载脚本 (IPC 通信)
├── backend.ts      # Python 子进程管理
├── window.ts       # 窗口管理
└── tray.ts         # 系统托盘
```

### 分析器架构

后端 `analyzers/` 目录包含四个核心分析器：

| 分析器 | 文件 | 功能 |
|--------|------|------|
| `IdleDetector` | `idle_detector.py` | 检测关机僵尸VM（按关机天数分级）和开机闲置VM（活跃度评分算法）|
| `RightSizeAnalyzer` | `rightsize.py` | 基于 P95/P90 + 缓冲系数推荐规格，对齐标准 CPU/内存配置；内置错配检测（`_determine_mismatch_type`）|
| `TidalDetector` | `resource_analyzer.py` | 识别潮汐型 VM（日/周/月粒度），仅输出具有潮汐特征的 VM |
| `ResourceAnalyzer` | `resource_analyzer.py` | 组合 `RightSizeAnalyzer` + `TidalDetector` 并行执行，返回 `{resourceOptimization, tidal, summary}` |
| `HealthAnalyzer` | `health.py` | 超配（40%）+ 均衡（30%）+ 热点（30%）综合评分 |
| 评估模式配置 | `modes.py` | 四种预设分析模式的阈值配置（safe/saving/aggressive/custom）|

**指标存储格式（重要）**：
- CPU 指标存储为绝对值（`percentage / 100 × cpu_count × host_cpu_mhz`，单位 MHz）
- 内存指标存储为绝对值（实际使用字节数）
- 分析时统一换算回百分比再进行阈值比较

---

## 关键开发规则

### 时间戳规范（⚠️ 重要）

**统一使用 `datetime.now()`（本地时间），禁止使用 `datetime.utcnow()`。**

项目部署在 UTC+8 中国时区，若混用会导致用户可见的时间戳偏快 8 小时。

| 场景 | 正确 | 错误 |
|------|------|------|
| 写入数据库时间字段 | `datetime.now()` | `datetime.utcnow()` |
| 报告 `generated_at` | `datetime.now()` | `datetime.utcnow()` |
| 文件名时间戳 | `datetime.now()` | `datetime.utcnow()` |
| 查询时间范围（`end_time`）| `datetime.now()` | `datetime.utcnow()` |

**例外**：纯内部比较（如两个用同一方式写入的字段做差值）可以保持内部一致，但新代码应统一用 `datetime.now()`。

### 命名规范

| 层级 | 规范 | 示例 |
|------|------|------|
| 数据库列 | snake_case | `connection_id`, `created_at` |
| Python 变量 | snake_case | `connection_id`, `get_vm` |
| JSON API | camelCase | `connectionId`, `vmCount` |
| TypeScript | camelCase | `connectionId`, `vmCount` |
| Vue 组件 | PascalCase | `TaskDetail.vue`, `AppShell.vue` |

**重要**: JSON 响应必须使用 camelCase。使用 Pydantic `alias_generator=to_camel` 自动转换。

### 前后端数据对接规范（⚠️ 重要）

**基本原则**: **以后端为标准**，前端不得随意添加转换、映射或适配层。

#### 1. 字段命名统一
- 后端 API 返回的字段名使用 **camelCase**（如 `overallScore`, `vmCount`, `balanceScore`）
- 前端必须**直接使用**后端返回的字段名
- **禁止**在前端创建字段映射、转换或别名

#### 2. 数据传递原则
```typescript
// ✅ 正确：直接使用后端字段
const healthScore = result.overallScore
const balance = result.balanceScore

// ❌ 错误：创建映射或转换
const healthScore = result.score  // 后端没有这个字段
const healthData = {
  overallScore: result.overallScore,
  resourceBalance: result.balanceScore  // 不要这样做！
}
```

#### 3. 问题排查流程
当发现前端显示问题或字段不匹配时，按以下顺序排查：
1. **检查后端**：确认后端 API 返回的字段名是什么
2. **统一后端**：如果后端字段名不符合规范，修改后端
3. **修改前端**：如果后端字段名已符合规范，修改前端模板直接使用

**绝对禁止**：
- ❌ 在前端做字段映射（如 `resourceBalance: result.balanceScore`）
- ❌ 创建"兼容字段"（如 `score: result.overallScore`）
- ❌ 添加转换层或适配器

#### 4. 统一验证方式
修改 API 后，验证以下场景：
- 数据库 → 后端 API：字段名是 camelCase
- 后端 API → 前端：前端直接使用，无映射
- 前端模板：显示时直接访问字段

### API 响应格式

```python
# 成功响应
{
    "success": True,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "success": False,
    "error": {
        "code": "ERROR_CODE",
        "message": "错误描述"
    }
}
```

### 数据库会话管理

**关键**: 每个请求会话必须提交，否则测试中数据不可见：

```python
async def override_get_db():
    async with session_maker() as session:
        try:
            yield session
            await session.commit()  # 必须提交！
        except Exception:
            await session.rollback()
            raise
```

### 异步编程规范

- 所有 I/O 操作必须使用异步库 (`aiosqlite`, `httpx`, 不是 `sqlite3`, `requests`)
- 并发限制使用 `asyncio.Semaphore(5)` 控制同时进行的请求数
- 使用 `asyncio.gather()` 并行执行多个异步任务

### vCenter 连接器关键点

1. **指标采集固定使用天级间隔 (86400s)**，与 H3C UIS 对齐，确保两端置信度计算一致
2. **实例名使用空字符串 `""`** 获取聚合数据
3. **主机IP获取**: 从 `config.network.vnic[vmk0].spec.ip.ipAddress` 获取
4. **VM Key 生成**: 优先 `uuid:<lowercase_uuid>` → `<datacenter>:<name>`

### 评估模式配置

分析器支持四种预设模式，配置在 `analyzers/modes.py`：

| 模式 | 闲置阈值（CPU/内存）| Right Size 缓冲 | 健康超配阈值 | 适用场景 |
|------|---------------------|-----------------|-------------|----------|
| `safe` | 5% / 10%，置信度≥80 | 30% | 120% | 生产核心环境 |
| `saving` | 10% / 20%，置信度≥60 | 20% | 150% | 通用，默认推荐 |
| `aggressive` | 15% / 25%，置信度≥50 | 10% | 200% | 测试/开发环境 |
| `custom` | 用户自定义 | 用户自定义 | 用户自定义 | 特殊场景 |

自定义模式基于某个预设（`baseMode`）扩展，任务 `config` 字段存储 `mode`、`baseMode`、`customConfig`。

### ⚠️ 代码质量与兼容性准则

**核心原则**: **禁止向后兼容逻辑，保持代码简洁清晰**

#### 1. 零兼容原则
- ❌ **禁止**向后兼容旧数据、旧字段、旧接口
- ❌ **禁止**添加兼容逻辑（如 `if old_field: new_field = old_field`）
- ❌ **禁止**添加数据迁移脚本
- ❌ **禁止**创建字段映射或转换层

#### 2. 修改策略
当需要修改字段名、接口或数据结构时：
1. **直接修改**：一次性修改到位
2. **修改所有引用**：确保前后端完全同步，**特别注意以下容易遗漏的地方**：
   - `report/builder.py`：汇总字段计算（`build_resource_summary`、`build_savings_estimate`）
   - `report/excel.py`：列定义（`COLUMNS` 字典）和数据标准化逻辑
   - `report/pdf.py`：表格数据组装和图表数据取值
3. **删除旧代码**：不保留任何兼容逻辑，包括定义了但未被调用的私有方法
4. **验证完整性**：确保所有相关文件都已修改

#### 3. 用户数据管理
- 用户会删除旧的运行数据重新测试
- 不需要考虑历史数据的兼容性
- 修改完成后告知用户是否需要删除数据

#### 4. 示例对比

**❌ 错误做法（屎山代码）**：
```python
# 兼容旧数据
selected_vm_count = config.get("selectedVMCount")
if selected_vm_count is None:
    selected_vm_count = config.get("vmCount", 0)  # 兼容逻辑

return {
    "selectedVMCount": selected_vm_count,
    "vmCount": selected_vm_count  # 保留旧字段
}
```

```typescript
// 前端兼容处理
const displayName = task.connectionHost || task.connectionName  // 回退逻辑
```

**✅ 正确做法（干净代码）**：
```python
# 直接使用新字段
return {
    "connectionHost": config.get("connectionHost", ""),
    # 不保留旧字段，不添加兼容逻辑
}
```

```typescript
// 前端直接使用
const displayName = task.connectionHost  // 假设字段一定存在
```

#### 5. 修改完成后的输出
每次修改完成后，只需告知用户：
- ✅ **需要删除数据重新测试**：当修改了数据库结构、config 格式、API 字段等
- ✅ **无需删除数据**：当仅修改了 UI、样式、非数据相关的逻辑

---

## 版本迁移机制

**⚠️ 重要**: `core/migration.py` 在每次应用启动时检查版本，若版本号与存储的版本不匹配，**会自动删除所有数据**（数据库、加密密钥、凭证、日志），然后写入新版本号。

- 版本号定义在 `backend/app/__init__.py` 的 `__version__`
- 升级版本时用户数据会在下次启动时自动清除
- 调试时若遇到数据丢失，检查版本号是否与 `~/.local/share/justfit/version` 文件一致

---

## 常见问题

### 问题: 构建失败 "axios not found"

**解决**: 确保 `frontend/package.json` 中包含 `"axios": "^1.7.0"`

### 问题: vCenter 指标返回空值

**原因**: 使用了非天级间隔（如历史 5 分钟间隔）

**解决**: 固定使用 `intervalId=86400`（天级间隔）

### 问题: 测试中数据不可见

**原因**: 数据库会话未提交

**解决**: 在测试 fixture 中添加 `await session.commit()`

### 问题: 窗口控制按钮不工作

**原因**: 未在 Electron 环境中运行

**解决**: 检查 `window.electronAPI` 是否存在

### 问题: 端口冲突 22631/22632

**原因**: 另一个开发实例正在运行

**解决**: `pkill -f "uvicorn app.main:app"` 或 `pkill -f "vite.*22632"`

---

## 测试环境

- **VMware vCenter**: 10.103.116.116
- **用户**: administrator@vsphere.local
- **密码**: Admin@123.

---

## 版本管理

- **当前版本**: v0.0.5
- **版本定义**: `backend/app/__init__.py` 中的 `__version__`
- **版本格式**: MAJOR.MINOR.PATCH
  - **MAJOR**: 重大架构变更，数据库不兼容升级
  - **MINOR**: 新功能添加，向后兼容
  - **PATCH**: Bug 修复，不影响功能

---

## 数据存储位置

- **数据目录**: Windows: `%LOCALAPPDATA%\justfit`，Linux/macOS: `~/.local/share/justfit`
- **数据库**: `justfit.db`
- **日志**: `logs/justfit.log`
- **加密密钥**: `.key`
- **加密凭证**: `credentials.enc`

---

## 环境变量配置

后端配置通过环境变量或 `.env` 文件设置，**所有环境变量使用 `JUSTFIT_` 前缀**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JUSTFIT_API_PORT` | API 监听端口 | `22631` |
| `JUSTFIT_API_HOST` | API 监听地址 | `127.0.0.1` |
| `JUSTFIT_DEBUG` | 调试模式 | `True`（开发），`False`（打包后）|
| `JUSTFIT_DATA_DIR` | 数据目录路径 | Windows: `%LOCALAPPDATA%\justfit`，Linux/macOS: `~/.local/share/justfit` |
| `JUSTFIT_DB_NAME` | 数据库文件名 | `justfit.db` |
| `JUSTFIT_DEFAULT_METRIC_DAYS` | 默认采集天数 | `30` |
| `JUSTFIT_METRIC_INTERVAL_SECONDS` | 指标采集间隔 | `20` |
| `JUSTFIT_VCENTER_TIMEOUT` | vCenter 连接超时(秒) | `30` |
| `JUSTFIT_VCENTER_MAX_RETRIES` | vCenter 最大重试次数 | `3` |

---

## 文件参考

- 架构详细说明: `docs/REFACTORING_SUMMARY.md`
- Debug 指南: `docs/DEBUG_GUIDE.md`
- API 文档: `docs/API.md`
- 部署指南: `docs/DEPLOYMENT.md`
