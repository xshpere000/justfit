#!/bin/bash
set -e

export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
export ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - Electron Packaging"
echo "========================================="

# 检查并同步后端 exe 到打包资源目录
BACKEND_DIST_EXE="backend/dist/justfit_backend.exe"
BACKEND_RESOURCE_DIR="resources/backend"
BACKEND_RESOURCE_EXE="$BACKEND_RESOURCE_DIR/justfit_backend.exe"

if [ -f "$BACKEND_DIST_EXE" ]; then
    mkdir -p "$BACKEND_RESOURCE_DIR"
    cp -f "$BACKEND_DIST_EXE" "$BACKEND_RESOURCE_EXE"
    echo ">>> 已同步后端 exe 到打包资源目录"
elif [ ! -f "$BACKEND_RESOURCE_EXE" ]; then
    echo "错误: 未找到后端 exe"
    echo "请先运行 ./scripts/build_backend.sh 生成 backend/dist/justfit_backend.exe"
    exit 1
fi

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
