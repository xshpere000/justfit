#!/bin/bash
# Python 后端打包脚本 - 使用 PyInstaller 打包

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit Backend - PyInstaller Build"
echo "========================================="
echo ""

# 1. 确定 Python 命令
PYTHON_CMD=""
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "错误: 未找到 Python 安装"
    exit 1
fi

# 2. 检查 PyInstaller
if ! $PYTHON_CMD -m PyInstaller --version &> /dev/null; then
    echo "错误: PyInstaller 未安装"
    echo "请运行: $PYTHON_CMD -m pip install pyinstaller"
    exit 1
fi

echo ">>> 使用 Python: $($PYTHON_CMD --version 2>&1)"
echo ">>> PyInstaller 版本: $($PYTHON_CMD -m PyInstaller --version 2>&1)"
echo ""

cd backend

# 3. 清理旧的构建
echo ">>> 清理旧构建文件..."
rm -rf build/ dist/

# 4. 执行打包
echo ">>> 开始打包..."

# 检查是否有 spec 文件
if [ -f "justfit_backend.spec" ]; then
    echo "  发现 justfit_backend.spec，使用配置文件打包..."
    $PYTHON_CMD -m PyInstaller justfit_backend.spec --clean --noconfirm
else
    echo "  未发现 spec 文件，使用默认参数打包..."
    # 这里根据你的实际入口文件调整，假设入口是 main.py
    $PYTHON_CMD -m PyInstaller -F -n justfit_backend main.py --clean
fi

# 5. 验证结果
echo ""
if [ -f "dist/justfit_backend.exe" ]; then
    echo "========================================="
    echo "  打包成功！"
    echo "========================================="
    echo ""
    # 显示文件大小
    SIZE=$(ls -lh dist/justfit_backend.exe | awk '{print $5}')
    echo "  输出文件: backend/dist/justfit_backend.exe"
    echo "  文件大小: $SIZE"
    echo ""
    echo "  测试运行:"
    echo "    ./backend/dist/justfit_backend.exe"
    echo ""
else
    echo "========================================="
    echo "  打包失败！"
    echo "========================================="
    echo "  未找到输出文件，请检查构建日志中的错误。"
    exit 1
fi
