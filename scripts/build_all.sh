#!/bin/bash
# JustFit 完整打包脚本 - Python 后端 + Vue 前端 + Electron

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - 完整打包流程"
echo "========================================="
echo ""

# 1. 检查环境
echo ">>> 检查环境..."
if ! command -v node &> /dev/null; then
    echo "错误: Node.js 未安装"
    exit 1
fi

# 优先检查 python3，兼容性更好
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "错误: Python 未安装"
    exit 1
fi

# 检查 PyInstaller
if ! $PYTHON_CMD -m PyInstaller --version &> /dev/null; then
    echo "警告: PyInstaller 未安装，将跳过 Python 后端打包"
    echo "      如需打包后端，请运行: pip install pyinstaller"
    PYTHON_BUILD=false
else
    PYTHON_BUILD=true
fi

echo "  Node: $(node -v)"
echo "  Python: $($PYTHON_CMD --version 2>&1 | awk '{print $2}')"
echo "  环境检查完成"
echo ""

# 2. 安装依赖
echo ">>> 检查依赖..."
if [ ! -d "electron/node_modules" ]; then
    echo "  安装 Electron 依赖..."
    cd electron && npm install && cd ..
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "  安装前端依赖..."
    cd frontend && npm install && cd ..
fi
echo "  依赖检查完成"
echo ""

# 3. 打包 Python 后端
if [ "$PYTHON_BUILD" = true ]; then
    echo ">>> 打包 Python 后端..."
    
    # 确保打包脚本存在
    if [ ! -f "scripts/build_backend.sh" ]; then
        echo "警告: 未找到 scripts/build_backend.sh，尝试手动打包..."
        cd backend
        $PYTHON_CMD -m PyInstaller -F -n justfit_backend main.py
        cd ..
    else
        ./scripts/build_backend.sh
    fi
    
    # 确保输出目录存在
    mkdir -p resources/backend
    
    # 复制 exe 到 resources (用于 electron-builder 打包进资源)
    if [ -f "backend/dist/justfit_backend.exe" ]; then
        cp -f backend/dist/justfit_backend.exe resources/backend/
        echo "  后端已复制到 resources/backend/justfit_backend.exe"
    else
        echo "错误: 后端打包失败，未找到 .exe 文件"
        exit 1
    fi
    echo ""
fi

# 4. 构建前端
echo ">>> 构建前端..."
cd frontend
npm run build
if [ $? -ne 0 ]; then
    echo "错误: 前端构建失败"
    exit 1
fi
cd ..
echo "  前端构建完成"
echo ""

# 5. 构建 Electron 主进程
echo ">>> 构建 Electron 主进程..."
cd electron
npm run build
if [ $? -ne 0 ]; then
    echo "错误: Electron 主进程构建失败"
    exit 1
fi
cd ..
echo "  Electron 构建完成"
echo ""

# 6. 打包 Electron 应用
echo ">>> 打包 Electron 应用..."
cd electron

# 设置环境变量并打包
export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
export ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"

# 直接读取 package.json 中的 build 配置进行打包
# 此时 package.json 应配置 extraResources 指向 resources/backend/justfit_backend.exe
npx electron-builder --win --x64

cd ..

echo ""
echo "========================================="
echo "  打包完成！"
echo "========================================="
echo ""
echo "  输出目录: dist/electron/"
echo ""

# 显示生成的文件
if [ -d "dist/electron" ]; then
    echo "  生成的文件:"
    # 兼容 Windows Git Bash 和 Linux
    ls -lh dist/electron/*.exe 2>/dev/null | while read -r line; do
        # 简单的格式化输出
        file_name=$(echo "$line" | awk '{print $9}')
        file_size=$(echo "$line" | awk '{print $5}')
        echo "    - $(basename "$file_name") ($file_size)"
    done
else
    echo "  警告: 未找到输出目录"
fi

echo ""
