#!/bin/bash
# 生产构建脚本 - 构建前端和 Electron

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - Production Build"
echo "========================================="
echo ""

# 清理旧构建
echo ">>> 清理旧构建..."
rm -rf frontend/dist
rm -rf electron/dist
rm -rf dist/electron

# 1. 构建前端
echo ">>> 构建前端..."
cd frontend
npm run build
echo "  前端构建完成"
cd ..

# 2. 构建 Electron 主进程
echo ">>> 构建 Electron 主进程..."
cd electron
npm run build
echo "  Electron 构建完成"
cd ..

echo ""
echo "========================================="
echo "  构建完成！"
echo "========================================="
echo ""
echo "  输出目录:"
echo "    前端: frontend/dist/"
echo "    Electron: electron/dist/"
echo ""
echo "  下一步: 运行 ./scripts/package.sh 进行打包"
