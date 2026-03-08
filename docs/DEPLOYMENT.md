# JustFit 部署指南

## 开发环境部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd justfit
```

### 2. 安装依赖

```bash
# Python 依赖
cd backend
pip install -e .
# 或使用 uv
uv pip install -e .

# Node.js 依赖
cd ../frontend
npm install
```

### 3. 启动开发模式

```bash
# 使用 Makefile（推荐）
make dev

# 或直接运行脚本
./scripts/dev.sh
```

## 生产构建

### 1. 构建前端

```bash
cd frontend
npm run build
```

输出：`frontend/dist/`

### 2. 构建后端

后端使用 Python，无需编译，确保依赖已安装：

```bash
cd backend
uv pip install -r requirements.txt  # 或使用 pip install -e .
```

### 3. 构建 Electron

```bash
cd electron
npm run build
```

### 4. 打包应用

```bash
make package
# 或
./scripts/package.sh
```

输出：`dist/electron/`

## 平台特定部署

### Windows

#### 开发环境

1. 安装 Python 3.14（从 python.org）
2. 安装 Node.js 18+（从 nodejs.org）
3. 安装 uv（可选）：`pip install uv`
4. 按上述步骤安装依赖并启动

#### 生产部署

1. 运行 `make package` 生成 NSIS 安装包
2. 运行生成的 `.exe` 安装程序
3. 或使用便携版直接运行

### Linux

#### Debian/Ubuntu

```bash
# 安装依赖
sudo apt update
sudo apt install python3.14 python3.14-venv nodejs npm

# 安装 uv
pip install uv

# 构建并运行
make dev  # 开发模式
make package  # 打包
```

#### Red Hat/CentOS

```bash
# 安装依赖
sudo dnf install python3.14 nodejs npm

# 其余步骤同上
```

### macOS

#### 开发环境

```bash
# 使用 Homebrew
brew install python@3.14 node
pip install uv

# 其余步骤同上
```

#### 生产部署

1. 运行 `make package` 生成 DMG 文件
2. 打开 DMG 并拖拽到 Applications 文件夹

## Docker 部署（规划中）

```dockerfile
# Dockerfile 示例（待实现）
FROM python:3.14-slim

# 安装依赖
# ...
```

## 配置

### 环境变量

创建 `.env` 文件：

```env
# 数据库
DB_PATH=/path/to/database.db

# API 服务
API_HOST=127.0.0.1
API_PORT=22631

# 日志
LOG_LEVEL=INFO
```

### 数据目录

应用数据存储在：

- Windows: `%APPDATA%/JustFit/`
- Linux: `~/.local/share/JustFit/`
- macOS: `~/Library/Application Support/JustFit/`

包含：
- `data.db` - SQLite 数据库
- `.key` - 加密密钥
- `credentials.enc` - 加密凭据

## 更新

### 自动更新（规划中）

应用将支持检查更新并自动下载新版本。

### 手动更新

1. 下载新版本安装包
2. 卸载旧版本（数据目录会保留）
3. 安装新版本

## 故障排查

### 端口被占用

```bash
# 查找占用 22631 端口的进程
lsof -i :22631  # Linux/macOS
netstat -ano | findstr :22631  # Windows

# 杀死进程
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows
```

### 数据库错误

```bash
# 检查数据库文件
ls -la ~/.local/share/JustFit/

# 重置数据库（警告：会丢失所有数据）
rm ~/.local/share/JustFit/data.db
```

### Python 依赖问题

```bash
# 重新安装依赖
cd backend
pip install -e . --force-reinstall
```

## 性能优化

### 后端

- 调整数据库连接池大小
- 启用 API 响应缓存
- 并发控制：调整信号量限制

### 前端

- 构建时启用代码分割
- 启用 Gzip 压缩
- 使用 CDN 加载静态资源

## 安全建议

1. **不要暴露 API 端口**：API 仅监听 localhost
2. **加密存储凭据**：使用内置的 AES-256-GCM 加密
3. **定期更新**：及时安装安全补丁
4. **备份数据**：定期备份数据库文件
