#!/bin/bash
set -e

export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
export ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - Electron Packaging"
echo "========================================="

# 检查构建产物
if [ ! -d "frontend/dist" ] || [ ! -d "electron/dist" ]; then
    echo "错误: 请先运行构建脚本"
    exit 1
fi

echo ">>> 开始打包..."
cd electron

# 直接使用 package.json 中的配置
npx electron-builder --win --x64

cd ..

echo ""
echo "========================================="
echo "  打包完成！"
echo "========================================="
echo "  输出目录: dist/electron/"
ls -lh dist/electron/*.exe 2>/dev/null || echo "  检查输出目录"
