# JustFit

JustFit 是面向多云/虚拟化平台的**桌面端资源评估与优化工具**，基于 **Electron** + **Python FastAPI** + **Vue 3** 构建，帮助运维团队快速发现资源浪费、生成专业评估报告。

当前版本：**v0.0.5**

---

## 功能特性

### 1. 多平台连接管理

- 支持 **VMware vCenter**（已上线）
- 支持 **H3C UIS**（已上线）
- 连接配置持久化存储，支持测试连通性
- 凭证加密存储（AES 加密）

### 2. 五步向导式评估任务创建

| 步骤 | 说明 |
|------|------|
| 选择平台 | 选择 VMware vCenter 或 H3C UIS |
| 配置连接 | 填写或选择已保存的连接 |
| 选择虚拟机 | 按集群/主机筛选，勾选目标 VM |
| 任务配置 | 选择评估模式（安全/节省/激进/自定义）及采集天数 |
| 开始确认 | 确认配置后启动后台采集与分析 |

### 3. 智能分析引擎（四大分析模块）

#### 闲置 VM 检测（IdleDetector）

- **关机型僵尸**：检测已关机 14/30/90 天以上的 VM，按严重程度分级（medium/high/critical）。关机VM已不占用CPU和内存，删除后仅释放磁盘空间
- **开机闲置**：对开机 VM 计算活跃度评分（CPU 40%权重 + 内存 30% + 磁盘 15% + 网络 15%），活跃度 < 30 判定为闲置。关闭后释放CPU、内存和磁盘
- **低活跃**：活跃度在 15~30 之间的 VM。关闭后释放CPU、内存和磁盘
- 指标采用 P95 统计，CPU/内存数值从存储绝对值反算为使用率百分比
- 自动排除模板 VM（`-template`、`-tmpl` 等关键词），测试 VM 降低置信度

#### 资源配置优化（RightSizeAnalyzer）

- 仅针对开机 VM（需要历史性能数据），推荐公式：`max(P95, P90) × buffer_ratio`，同时设置峰值保护下限 `= max × 0.8`
- CPU 推荐结果对齐标准规格（1/2/4/8/12/16/24/32/48/64 核）
- 内存推荐结果对齐标准规格（0.5/1/2/3/4/6/8/12/16/24/32/48/64/96/128/192/256 GB）
- CPU 和内存分别独立判断调整方向：显著缩容（≥50%）/ 缩容（≥25%）/ 扩容 / 显著扩容 / 合理
- 内置**配置错配检测**：CPU/内存 P95 组合判断 5 种类型（`cpu_rich_memory_poor` / `cpu_poor_memory_rich` / `both_underutilized` / `both_overutilized` / `balanced`）
- 输出字段：`cpuWasteRatio` / `memWasteRatio`（各维度浪费比例）、`mismatchType`（错配类型）、`riskLevel`、`confidence`、`reason`（含具体数值的决策依据）

#### 潮汐检测（TidalDetector）

- 基于 CPU 使用率的变异系数（CV）和峰谷比识别潮汐型 VM
- 潮汐粒度：**日粒度**（昼夜波动）/ **周粒度**（工作日/周末）/ **月粒度**
- 仅输出具有潮汐特征的 VM（高 CV + 高峰谷比）
- 输出推荐关机时段（`recommendedOffHours`）及详细周期数据（`tidalDetails`）

#### 平台健康评分（HealthAnalyzer）

- **超配分析**（权重 40%）：计算各集群 CPU/内存分配比 vs 物理资源，使用 3GHz 作为 MHz→核换算基准
- **负载均衡**（权重 30%）：集群内各主机 VM 数量的变异系数（CV），评级 excellent/good/fair/poor
- **热点检测**（权重 30%）：主机 VM 密度（VMs/CPU核），检测过载主机
- 综合评分 0~100，评级：excellent（≥90）/ good（≥75）/ fair（≥60）/ poor（≥40）/ critical

### 4. 评估模式（四种预设）

| 模式 | 闲置阈值（CPU/内存） | Right Size 缓冲 | 健康超配阈值 | 适用场景 |
|------|---------------------|-----------------|-------------|----------|
| 安全 | 5% / 10% | 30% | 120% | 生产核心环境 |
| 节省（默认） | 10% / 20% | 20% | 150% | 通用场景 |
| 激进 | 15% / 25% | 10% | 200% | 测试/开发环境 |
| 自定义 | 用户自定义 | 用户自定义 | 用户自定义 | 特殊场景 |

自定义模式基于某预设扩展，支持调节：闲置检测天数、CPU/内存阈值、最低置信度、Right Size 缓冲比例、CV 阈值、峰谷比阈值、错配判断阈值、健康评分阈值等。

### 5. 任务详情（10 个标签页）

| 标签 | 内容 |
|------|------|
| 任务概览 | 任务状态、分析启动入口、报告生成入口 |
| 虚拟机列表 | 采集的 VM 清单（名称、CPU、内存、状态、数据中心、主机IP） |
| 闲置检测 | 闲置 VM 列表，支持按类型/风险等级筛选 |
| 资源配置优化 | Right Size 建议表格（当前配置、推荐配置、P95使用率）及配置错配分析 |
| 潮汐检测 | 潮汐型 VM 列表（粒度、峰谷比、推荐关机时段） |
| **分析结果** | 集群资源总量汇总、优化选项选择、可释放资源/主机贪心计算结果 |
| 健康评分 | 平台综合健康分数、各集群超配/均衡/热点评分 |
| 评估模式 | 查看/修改当前任务的分析参数 |
| 任务配置 | 任务基本信息、执行耗时、评估对象数量等 |
| 执行日志 | 任务各阶段日志流 |

### 6. 报告生成

- **Excel 报告**（8 个工作表）：概览、集群、主机、虚拟机、闲置检测、资源优化、潮汐检测、健康评分
- **PDF 报告**（7 个章节）：评估概况、平台健康评分、闲置VM分析、资源配置优化、潮汐检测分析、配置错配分析、资源清单
- 支持历史报告下载与删除管理

### 7. Electron 桌面特性

- 单实例锁定（防止重复启动，二次启动时激活已有窗口）
- 系统托盘图标
- 自定义标题栏（最小化/最大化/关闭按钮）
- 自动管理 Python 后端子进程的启停

---

## 技术架构

```
Electron Shell
├── Renderer Process (Vue 3 + TypeScript)
│   └── HTTP API → http://localhost:22631/api/*
└── Main Process (Node.js)
    └── spawn → Python FastAPI (localhost:22631)
        └── SQLite Database
```

| 层级 | 技术 |
|------|------|
| 桌面框架 | Electron 34 |
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts |
| 后端 | Python 3.14 + FastAPI + SQLAlchemy (aiosqlite) |
| 数据库 | SQLite |
| 通信 | HTTP REST API（camelCase JSON）|

---

## 快速开始

### 环境要求

- **Python 3.14+**
- **Node.js 18+**

### 安装依赖

```bash
# 后端
cd backend && pip install -r requirements.txt

# 前端
cd frontend && npm install

# Electron
cd electron && npm install
```

### 开发模式

#### Windows（Git Bash）

```bash
./scripts/dev/dev-windows.sh
```

#### Linux / macOS

```bash
./scripts/dev/dev-linux.sh
# 或
make dev
```

启动后：

- 后端 API：`http://localhost:22631`
- 前端页面：`http://localhost:22632`
- API 文档（Swagger）：`http://localhost:22631/docs`

#### 手动分别启动（调试用）

```bash
# 后端
cd backend
python -m uvicorn app.main:app --reload --port 22631 --host 0.0.0.0

# 前端
cd frontend
npm run dev -- --host 0.0.0.0 --port 22632
```

#### 停止服务

```bash
# Linux/macOS
pkill -f "uvicorn app.main:app"
pkill -f "vite.*22632"

# Windows Git Bash
taskkill //F //IM python.exe
taskkill //F //IM node.exe
```

---

## 构建与打包

```bash
make build-all        # 完整打包（前端 + 后端 exe + Electron 安装包）⭐
make build-frontend   # 仅打包前端
make build-backend    # 仅打包后端（Python → exe）
make package-electron # 基于已打包前后端生成 Electron 安装包
make clean            # 清理构建产物
```

打包完成后，安装包位于 `dist/electron/`：

- `JustFit-0.0.5-x64.exe` — NSIS 安装程序
- `JustFit-0.0.5-x64-portable.exe` — 免安装便携版

---

## 测试

```bash
# 后端测试（全部）
cd backend && PYTHONPATH=. python3.14 -m pytest tests/ -v

# 后端集成测试
cd backend && PYTHONPATH=. python3.14 -m pytest tests/backend/integration/ -v -s

# 后端 E2E 测试
cd backend && PYTHONPATH=. python3.14 -m pytest tests/backend/e2e/ -v -s

# 前端测试
cd frontend && npm run test:run

# 或使用 Makefile
make test           # 后端测试
make test-frontend  # 前端测试
```

---

## 目录结构

```
justfit/
├── electron/               # Electron 主进程
│   ├── main.ts             # 主进程入口（单实例锁、IPC 注册）
│   ├── backend.ts          # Python 子进程管理
│   ├── window.ts           # 窗口管理
│   ├── tray.ts             # 系统托盘
│   └── logger.ts           # Electron 日志
├── frontend/               # Vue 3 前端
│   └── src/
│       ├── api/            # HTTP API 客户端
│       ├── components/     # 通用组件（AppShell、TaskCard、VersionUpgradeDialog 等）
│       ├── stores/         # Pinia 状态管理
│       ├── views/          # 页面（Home、Wizard、TaskDetail、Connections、AnalysisModeTab）
│       ├── types/          # TypeScript 类型定义
│       └── router/         # Vue Router 配置
├── backend/
│   └── app/
│       ├── routers/        # API 路由（connections、tasks、resources、analysis、reports）
│       ├── services/       # 业务逻辑层
│       ├── analyzers/      # 分析算法（idle_detector、rightsize、resource_analyzer、health、modes）
│       ├── connectors/     # 平台连接器（vcenter.py、uis.py）
│       ├── models/         # SQLAlchemy 数据模型
│       ├── schemas/        # Pydantic DTO
│       ├── report/         # 报告生成（excel、pdf、builder、charts）
│       ├── repositories/   # 数据访问层
│       ├── security/       # 凭证加密
│       └── core/           # 核心（database、migration、errors、logging）
├── scripts/
│   ├── dev/                # 开发启动脚本
│   └── build/              # 构建打包脚本
├── tests/                  # 测试文件
├── resources/              # 静态资源（图标等）
├── Makefile
└── electron-builder.json
```

---

## API 路由概览

| 前缀 | 功能 |
|------|------|
| `GET/POST /api/connections` | 连接管理（增删改查、测试连通性）|
| `GET /api/resources/connections/{id}/vms` | 获取可采集的 VM 列表 |
| `POST /api/resources/connections/{id}/collect` | 触发资源采集 |
| `GET/POST/DELETE /api/tasks` | 任务管理 |
| `POST /api/tasks/{id}/re-evaluate` | 重新评估 |
| `GET /api/tasks/{id}/logs` | 任务执行日志 |
| `GET /api/tasks/{id}/vms` | 任务关联的 VM 快照 |
| `POST /api/analysis/tasks/{id}/idle` | 执行闲置检测 |
| `GET /api/analysis/tasks/{id}/idle` | 获取闲置检测结果 |
| `POST /api/analysis/tasks/{id}/resource` | 执行资源分析（资源配置优化 + 潮汐检测）|
| `GET /api/analysis/tasks/{id}/resource` | 获取资源分析结果 |
| `POST /api/analysis/tasks/{id}/health` | 执行健康评分 |
| `GET /api/analysis/tasks/{id}/health` | 获取健康评分结果 |
| `GET /api/analysis/tasks/{id}/summary` | 计算可释放主机（贪心算法）|
| `GET /api/analysis/modes` | 获取所有预设分析模式配置 |
| `POST /api/reports/tasks/{id}/reports` | 生成报告 |
| `GET /{report_id}/download` | 下载报告文件 |

---

## 配置

后端通过环境变量或 `.env` 文件配置，所有变量使用 `JUSTFIT_` 前缀：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JUSTFIT_API_PORT` | API 监听端口 | `22631` |
| `JUSTFIT_API_HOST` | API 监听地址 | `127.0.0.1` |
| `JUSTFIT_DEBUG` | 调试模式 | `true`（开发），`false`（打包后） |
| `JUSTFIT_DATA_DIR` | 数据目录 | Windows: `%LOCALAPPDATA%\justfit`，Linux/macOS: `~/.local/share/justfit` |
| `JUSTFIT_DB_NAME` | 数据库文件名 | `justfit.db` |
| `JUSTFIT_DEFAULT_METRIC_DAYS` | 默认采集天数 | `30` |
| `JUSTFIT_METRIC_INTERVAL_SECONDS` | 指标采集间隔（秒） | `20` |
| `JUSTFIT_VCENTER_TIMEOUT` | vCenter 连接超时（秒） | `30` |
| `JUSTFIT_VCENTER_MAX_RETRIES` | vCenter 最大重试次数 | `3` |

---

## 数据存储

| 文件 | 路径 |
|------|------|
| 数据库 | `%LOCALAPPDATA%\justfit\justfit.db`（Windows）/ `~/.local/share/justfit/justfit.db`（Linux/macOS） |
| 加密密钥 | `…justfit/.key` |
| 加密凭证 | `…justfit/credentials.enc` |
| 日志 | `…justfit/logs/justfit.log` |
| 版本标记 | `…justfit/version` |

---

## 版本升级机制

应用启动时自动检查版本文件（`…justfit/version`）。版本号变更时，自动清除所有历史数据（数据库、密钥、凭证）并写入新版本号，**不支持历史数据迁移**。

版本号定义在 `backend/app/__init__.py`，遵循 `MAJOR.MINOR.PATCH` 规范。

---

## API 文档

启动后端后访问：

- Swagger UI：`http://localhost:22631/docs`
- ReDoc：`http://localhost:22631/redoc`

---

## 许可证

Copyright © 2025 JustFit. All rights reserved.
