# JustFit

JustFit 是面向多云/虚拟化平台资源优化的交互式桌面工具，基于 **Electron** + **Python FastAPI** + **Vue 3** 构建。

## 功能特性

### 1. 多平台连接与数据采集

- 支持 VMware vCenter
- 支持 H3C UIS（规划中）
- 自动采集集群、主机、虚拟机资源信息
- 性能指标采集（CPU、内存、磁盘、网络）

### 2. 智能分析引擎

- **僵尸 VM 检测**：识别长期闲置的虚拟机
- **Right Size 分析**：智能推荐资源配置
- **潮汐模式识别**：发现周期性使用规律
- **平台健康评分**：评估资源均衡与风险

### 3. 评估模式

- **安全模式**：保守阈值，适合生产环境
- **节省模式**：平衡阈值，推荐默认
- **激进模式**：最大化发现优化机会
- **自定义模式**：灵活调整分析参数

### 4. 报告生成

- Excel 格式（多工作表详细数据）
- PDF 格式（可打印专业报告）

## 技术架构

| 层级 | 技术 |
|------|------|
| 桌面框架 | Electron (Node.js) |
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts |
| 后端 | Python 3.14 + FastAPI |
| 数据库 | SQLite (SQLAlchemy + Alembic) |
| 通信 | HTTP REST API |

## 快速开始

### 环境要求

- Python 3.14+
- Node.js 18+

### 开发模式

#### Windows

```powershell
# 方式 1：双击运行批处理脚本（最简单）
scripts\dev.bat

# 方式 2：手动启动（打开两个 PowerShell 窗口）
# 窗口 1 - 后端
cd backend
python -m uvicorn app.main:app --reload --port 22631

# 窗口 2 - 前端
cd frontend
npm run dev
```

然后访问：<http://localhost:22632>

#### Linux / macOS

```bash
# 方式 1：使用 Makefile（推荐）
make dev

# 方式 2：直接运行脚本
./scripts/dev.sh
```

这将启动：

- FastAPI 后端（端口 22631）
- Vite 前端开发服务器（端口 22632）

### 生产构建

```bash
# 构建前后端
make build

# 打包 Electron 应用
make package
```

## 命令参考

### Makefile 目标

| 命令 | 说明 |
|------|------|
| `make dev` | 启动开发模式 |
| `make build` | 生产构建 |
| `make package` | Electron 打包 |
| `make clean` | 清理构建产物 |
| `make test` | 运行所有测试 |
| `make test-backend` | 运行后端测试 |
| `make install` | 安装依赖 |

### 测试

```bash
# 后端测试
cd backend && uv run pytest

# 前端测试
cd frontend && npm test

# E2E 测试
PYTHONPATH=backend pytest tests/backend/e2e/
```

## 目录结构

```
justfit/
├── electron/           # Electron 主进程
├── frontend/           # Vue 3 前端
│   ├── src/
│   │   ├── api/       # API 客户端
│   │   ├── components/# 通用组件
│   │   ├── stores/    # Pinia 状态管理
│   │   ├── views/     # 页面组件
│   │   └── utils/     # 工具函数
├── backend/           # Python FastAPI 后端
│   ├── app/
│   │   ├── analyzers/ # 分析算法
│   │   ├── connectors/# 平台连接器
│   │   ├── models/    # 数据模型
│   │   ├── routers/   # API 路由
│   │   ├── schemas/   # Pydantic DTO
│   │   └── services/  # 业务逻辑
├── scripts/           # 构建脚本
├── tests/             # 测试文件
└── resources/         # 静态资源
```

## 版本管理

当前版本：**v0.0.3**

版本号定义在 `backend/app/__init__.py` 中。

### 版本命名规范

- **MAJOR.MINOR.PATCH** 格式
- **MAJOR**: 重大架构变更，数据库不兼容升级
- **MINOR**: 新功能添加，向后兼容
- **PATCH**: Bug 修复，不影响功能

## API 文档

启动后端服务后，访问：

- Swagger UI: <http://localhost:22631/docs>
- ReDoc: <http://localhost:22631/redoc>

## 配置

后端配置通过环境变量或 `.env` 文件：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_PATH` | 数据库文件路径 | `~/.justfit/data.db` |
| `API_HOST` | API 监听地址 | `127.0.0.1` |
| `API_PORT` | API 监听端口 | `22631` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 许可证

Copyright © 2025 JustFit. All rights reserved.
