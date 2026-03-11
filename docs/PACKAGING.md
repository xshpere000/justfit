# JustFit 打包指南

本文档说明如何将 JustFit 打包成独立的 Windows exe **便携版**程序

---

## 🚀 快速打包（Makefile 方式）

### 一键完整打包

生成包含 Python 后端的独立 exe，用户无需安装 Python 环境即可运行。

```bash
# 1. 首次使用或环境变动时，设置打包环境
make setup
# 2. 执行完整打包
make package-all
```

**输出文件**：`dist/electron/JustFit-0.0.3-portable.exe`

---

## 🛠️ 手动打包（执行脚本）

如果你不想使用 Makefile，或者需要手动排查问题，可以按顺序执行以下脚本。

### 1. 环境初始化（仅首次需要）

确保已安装 Node.js 和 Python，然后运行：

```bash
# 安装 PyInstaller
pip install pyinstaller
# 安装前端依赖
cd frontend && npm install && cd ..
# 安装 Electron 依赖
cd electron && npm install && cd ..
```

### 2. 完整打包流程

依次执行以下三条命令：

```bash
# 第一步：打包 Python 后端为 exe
./scripts/build_backend.sh
# 第二步：构建前端代码和 Electron 主进程
./scripts/build.sh
# 第三步：打包成最终便携版程序
./scripts/package.sh
```

`./scripts/package.sh` 在打包前会自动检查 `backend/dist/justfit_backend.exe`，如果存在会同步复制到 `resources/backend/` 后再执行 Electron 打包。

**输出位置**：`dist/electron/JustFit-0.0.3-portable.exe`

---

## 📦 命令说明

### 当前实际生效的打包配置

当前 `./scripts/package.sh` 会进入 `electron/` 目录执行 `electron-builder`，因此**实际生效的打包配置在 `electron/package.json` 的 `build` 字段**。

根目录的 `electron-builder.json` 目前**不会被这条打包链路读取**，排查打包白屏、资源路径、extraResources 或 portable 输出名时，应以 `electron/package.json` 为准。

### Makefile 命令

| 命令 | 作用 | 说明 |
| :--- | :--- | :--- |
| **`make package-all`** | **完整打包** | 编译前端 + 打包 Python 后端 + 生成便携版 exe (推荐) |
| `make setup` | 环境初始化 | 安装依赖和工具 |
| `make clean` | 清理产物 | 删除所有构建生成文件 |

### 手动脚本对应关系

| Makefile 命令 | 对应脚本 | 作用 |
| :--- | :--- | :--- |
| `make package-backend` | `./scripts/build_backend.sh` | 打包 Python 后端 |
| `make build` | `./scripts/build.sh` | 构建前端和主进程 |
| `make package` | `./scripts/package.sh` | 生成便携版 exe |

---

## 📂 输出文件

打包完成后，文件位于项目根目录下的 `dist/electron/` 文件夹：

```text
dist/electron/
└── JustFit-0.0.3-portable.exe   # 便携版 (单文件，免安装)
```

**使用方法**：双击 `JustFit-0.0.3-portable.exe` 即可直接运行，无需安装

---

## ⚠️ 常见问题

### 1. 提示 `pyinstaller` 未找到

运行 `pip install pyinstaller` 手动安装。

### 2. 脚本无法执行

在 Windows Git Bash 中，如果提示权限错误，请以**管理员身份**运行终端。

### 3. 想重新打包

建议先清理再打包：

```bash
# Makefile 方式
make clean && make package-all
# 手动方式
rm -rf frontend/dist electron/dist dist/electron
./scripts/build_backend.sh
./scripts/build.sh
./scripts/package.sh
```

---

## 📤 系统要求

**用户运行环境**：

- Windows 10/11 (x64)
- 无需安装 Python 或 Node.js
