# JustFit 打包指南

本文档说明如何将 JustFit 项目打包成 Windows exe 安装程序。

---

## 📋 打包方案对比

| 方案 | 命令 | Python 后端 | 用户需要安装 Python | exe 大小 | 推荐度 |
|------|------|------------|-------------------|---------|--------|
| **基础打包** | `make package` | 源代码 | ✅ 是（3.14 + 依赖） | ~50MB | ⭐⭐ |
| **完整打包** | `make package-all` | 独立 exe | ❌ 否 | ~150MB | ⭐⭐⭐⭐⭐ |

---

## 🚀 快速开始

### 方案一：完整打包（推荐）⭐

**一步到位，打包所有组件**

```bash
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 完整打包
make package-all
```

**输出位置**：`dist/electron/JustFit-Setup-0.0.3-x64.exe`

**优点**：
- ✅ 用户无需安装 Python
- ✅ 开箱即用
- ✅ 所有依赖已包含

---

### 方案二：基础打包

**仅打包 Electron，Python 后端需要用户环境**

```bash
# 1. 安装 Electron 依赖
cd electron && npm install && cd ..

# 2. 打包
make package
```

**输出位置**：`dist/electron/JustFit-0.0.3-x64.exe`

**缺点**：
- ❌ 用户需要安装 Python 3.14
- ❌ 用户需要安装所有 Python 依赖
- ❌ 不适合分发给普通用户

---

## 🔧 详细步骤

### 完整打包流程

#### 1. 环境准备

```bash
# 确保已安装 Node.js 和 Python
node --version    # 应该 >= v18
python3.14 --version

# 安装 PyInstaller（用于打包 Python）
pip install pyinstaller

# 安装 Electron 依赖
cd electron && npm install && cd ..

# 安装前端依赖（如果还没装）
cd frontend && npm install && cd ..
```

#### 2. 打包 Python 后端

```bash
# 使用 PyInstaller 打包
cd backend
pyinstaller justfit_backend.spec --clean --noconfirm

# 检查输出
ls -lh dist/justfit_backend.exe
```

**输出**：`backend/dist/justfit_backend.exe` (~50MB)

#### 3. 打包 Electron 应用

```bash
# 回到项目根目录
cd ..

# 构建前端和 Electron
make build

# 打包
make package
```

**输出**：`dist/electron/JustFit-Setup-0.0.3-x64.exe`

---

## 📦 PyInstaller 配置说明

后端打包配置文件：`backend/justfit_backend.spec`

### 关键配置项

```python
# 入口文件
['app/main.py']

# 输出的 exe 文件名
name='justfit_backend'

# 是否显示控制台（调试时设为 True，发布时设为 False）
console=True

# 使用 UPX 压缩（减小体积）
upx=True
```

### 修改配置

如果需要修改打包行为，编辑 `justfit_backend.spec`：

```bash
vim backend/justfit_backend.spec
```

常见修改：
- **隐藏控制台**：`console=False`
- **添加图标**：修改 `icon` 参数
- **排除模块**：修改 `excludes` 列表

---

## 🎯 一键打包脚本

项目提供了自动化脚本，简化打包流程：

### `make package-all`

完整打包，包含：
1. ✅ 检查环境
2. ✅ 安装依赖
3. ✅ 打包 Python 后端
4. ✅ 构建前端
5. ✅ 构建 Electron
6. ✅ 打包成 exe

```bash
make package-all
```

### 其他命令

```bash
# 仅打包 Python 后端
make package-backend

# 仅打包 Electron（不含 Python exe）
make package

# 清理构建产物
make clean
```

---

## 📂 输出文件结构

打包后的目录结构：

```
dist/electron/
├── JustFit-Setup-0.0.3-x64.exe    # NSIS 安装程序（推荐分发）
└── JustFit-0.0.3-x64.exe          # Portable 版本（免安装）
```

### 用户安装后的目录

```
C:\Users\<用户>\AppData\Local\Programs\justfit\
├── justfit_backend.exe    # Python 后端
├── resources\
│   └── app.asar          # Electron 主进程
└── ...
```

---

## 🔍 调试打包后的应用

### 启用控制台

在 `justfit_backend.spec` 中设置：

```python
console=True  # 显示 Python 控制台
```

### 查看日志

应用日志位置：

```
~/.local/share/justfit/logs/justfit.log
```

或在 Windows：

```
C:\Users\<用户>\AppData\Roaming\justfit\logs\justfit.log
```

---

## ⚠️ 常见问题

### 问题 1：PyInstaller 打包失败

**错误**：`ModuleNotFoundError`

**解决**：在 `justfit_backend.spec` 的 `hiddenimports` 中添加缺失的模块

### 问题 2：exe 体积过大

**解决**：
1. 使用 UPX 压缩：`upx=True`
2. 排除不需要的模块：修改 `excludes` 列表
3. 使用虚拟环境打包

### 问题 3：打包后无法启动

**检查**：
1. 控制台是否显示错误信息
2. 防火墙是否阻止
3. 端口 22631 是否被占用

### 问题 4：前端资源缺失

**解决**：确保先执行 `make build` 构建前端

---

## 📤 分发给用户

### 安装程序（推荐）

分发给用户 `JustFit-Setup-0.0.3-x64.exe`，用户双击安装即可。

### 系统要求

- **操作系统**：Windows 10/11 (x64)
- **内存**：至少 4GB
- **磁盘**：至少 500MB
- **网络**：需要连接 vCenter/UIS 服务器

### 卸载

用户可以通过控制面板卸载，或运行：

```
C:\Users\<用户>\AppData\Local\Programs\justfit\unins000.exe
```

---

## 🔄 自动化构建

### GitHub Actions（可选）

可以在 `.github/workflows/build.yml` 中配置自动构建：

```yaml
name: Build

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - name: Install Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          pip install pyinstaller
          cd electron && npm install
          cd ../frontend && npm install
      - name: Build
        run: make package-all
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: justfit-installer
          path: dist/electron/*.exe
```

---

## 📚 参考资料

- [Electron Builder 文档](https://www.electron.build/)
- [PyInstaller 文档](https://pyinstaller.org/en/stable/)
- [Electron 打包最佳实践](https://www.electronjs.org/docs/latest/tutorial/code-signing)
