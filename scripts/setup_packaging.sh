#!/bin/bash
# 打包环境一键设置脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - 打包环境设置"
echo "========================================="
echo ""

# 1. 检查 Node.js
echo ">>> 检查 Node.js..."
if ! command -v node &> /dev/null; then
    echo "错误: Node.js 未安装"
    echo "请访问 https://nodejs.org/ 下载安装"
    exit 1
fi
echo "  ✓ Node.js $(node --version)"

# 2. 检查 Python
echo ">>> 检查 Python..."
if ! command -v python3.14 &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "错误: Python 3.14 未安装"
    exit 1
fi
echo "  ✓ Python $(python3.14 --version 2>/dev/null || python3 --version)"

# 3. 安装 PyInstaller
echo ">>> 安装 PyInstaller..."
if ! command -v pyinstaller &> /dev/null; then
    echo "  正在安装 PyInstaller..."
    pip install pyinstaller
    echo "  ✓ PyInstaller 已安装"
else
    echo "  ✓ PyInstaller 已安装 ($(pyinstaller --version))"
fi

# 4. 安装 Electron 依赖
echo ">>> 安装 Electron 依赖..."
if [ ! -d "electron/node_modules" ]; then
    echo "  正在安装 Electron 依赖..."
    cd electron
    npm install
    cd ..
    echo "  ✓ Electron 依赖已安装"
else
    echo "  ✓ Electron 依赖已存在"
fi

# 5. 检查前端依赖
echo ">>> 检查前端依赖..."
if [ ! -d "frontend/node_modules" ]; then
    echo "  正在安装前端依赖..."
    cd frontend
    npm install
    cd ..
    echo "  ✓ 前端依赖已安装"
else
    echo "  ✓ 前端依赖已存在"
fi

# 6. 检查图标文件
echo ">>> 检查资源文件..."
if [ -f "resources/icons/app.png" ]; then
    echo "  ✓ 图标文件存在"
else
    echo "  ⚠ 图标文件缺失（resources/icons/app.png）"
fi

echo ""
echo "========================================="
echo "  环境设置完成！"
echo "========================================="
echo ""
echo "  现在你可以运行以下命令打包应用："
echo ""
echo "    make package-all    # 完整打包（推荐）"
echo "    make package        # 基础打包"
echo "    make package-backend # 仅打包 Python 后端"
echo ""
echo "  详细文档: docs/PACKAGING.md"
echo ""
