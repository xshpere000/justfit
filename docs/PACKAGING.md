# JustFit 打包指南

本文档说明如何将 JustFit 打包成独立的 Windows exe **便携版**程序。

---

## 快速打包（推荐）

### 一键完整打包

```bash
make build-all
```

该命令依次执行三个步骤：前端构建 → Python 后端打包 → Electron 应用打包，完成后无需安装 Python 或 Node.js，用户直接双击 exe 即可运行。

**输出文件**：`dist/electron/` 目录下的便携版 exe

---

## 手动逐步打包

如需单独执行某一步骤，或排查某一环节的问题：

```bash
# 第一步：构建前端（Vue 3 → 静态文件）
make build-frontend
# 或：./scripts/build/build-frontend.sh

# 第二步：打包 Python 后端为 exe
make build-backend
# 或：./scripts/build/build-backend.sh

# 第三步：打包 Electron 桌面应用（前两步都完成后再执行）
make package-electron
# 或：./scripts/build/package-electron.sh
```

`package-electron.sh` 执行前会检查以下两项是否存在，缺少任意一项会报错退出：
- `frontend/dist/`（前端构建产物）
- `backend/dist/justfit_backend.exe`（后端构建产物）

---

## Makefile 命令一览

| 命令 | 作用 |
| :--- | :--- |
| `make build-all` | 一键完整打包（前端 + 后端 + Electron）⭐ 推荐 |
| `make build-frontend` | 仅构建前端 |
| `make build-backend` | 仅打包 Python 后端为 exe |
| `make package-electron` | 基于已有前后端产物打包 Electron |
| `make install` | 安装所有依赖（Python / 前端 / Electron） |
| `make clean` | 清理所有构建文件 |

---

## 打包配置说明

`package-electron.sh` 进入 `electron/` 目录执行 `electron-builder`，**实际生效的打包配置在 `electron/package.json` 的 `build` 字段**。

排查打包白屏、资源路径、`extraResources` 或输出文件名等问题时，应以 `electron/package.json` 为准。

打包链路会将后端 exe 复制到 `resources/backend/`，前端构建产物由 Electron 在生产模式下从 `frontend/dist/` 加载。

---

## 输出文件

```text
dist/electron/
└── JustFit-x.x.x-portable.exe   # 便携版（单文件，免安装）
```

**使用方法**：双击 exe 直接运行，无需安装。

---

## 常见问题

### 1. pyinstaller 未找到

```bash
pip install pyinstaller
```

### 2. 脚本无法执行（权限错误）

在 Windows Git Bash 中以**管理员身份**运行终端。

### 3. 想重新打包

先清理再打包，避免旧产物干扰：

```bash
make clean && make build-all
```

手动清理：

```bash
rm -rf frontend/dist backend/dist backend/build electron/dist dist/electron resources/backend
```

---

## 系统要求

**开发 / 打包环境**：
- Windows 10/11 (x64)
- Node.js（含 npm）
- Python（含 pip / pyinstaller）

**用户运行环境**：
- Windows 10/11 (x64)
- 无需安装 Python 或 Node.js
