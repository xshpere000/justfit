#!/bin/bash
# Python 后端打包脚本 - 使用 PyInstaller 打包

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit Backend - PyInstaller Build"
echo "========================================="
echo ""

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: PyInstaller 未安装"
    echo "请运行: pip install pyinstaller"
    exit 1
fi

echo ">>> 准备打包 Python 后端..."

cd backend

# 清理旧的构建
echo ">>> 清理旧构建..."
rm -rf build/ dist/

# 使用 PyInstaller 打包
echo ">>> 开始打包..."
pyinstaller justfit_backend.spec --clean --noconfirm

echo ""
echo "========================================="
echo "  打包完成！"
echo "========================================="
echo ""
echo "  输出文件: backend/dist/justfit_backend.exe"
echo ""
echo "  测试运行:"
echo "    ./backend/dist/justfit_backend.exe"
echo ""
