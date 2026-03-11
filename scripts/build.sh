#!/bin/bash
# 生产构建脚本 - 构建前端和 Electron 主进程

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - Production Build"
echo "========================================="
echo ""

# 1. 环境检查
echo ">>> 检查环境..."
if ! command -v node &> /dev/null; then
    echo "错误: Node.js 未安装"
    exit 1
fi

# 检查依赖是否安装（防止构建失败）
if [ ! -d "frontend/node_modules" ]; then
    echo "警告: 前端依赖未安装，正在安装..."
    cd frontend && npm install && cd ..
fi

if [ ! -d "electron/node_modules" ]; then
    echo "警告: Electron 依赖未安装，正在安装..."
    cd electron && npm install && cd ..
fi

echo "  Node: $(node -v)"
echo "  NPM: $(npm -v)"
echo ""

# 2. 清理旧构建
echo ">>> 清理旧构建文件..."
# 清理前端构建产物
rm -rf frontend/dist
# 清理 Electron 构建产物
rm -rf electron/dist
# 清理最终的打包输出目录（保持干净）
rm -rf dist/electron

echo "  清理完成"
echo ""

# 3. 构建前端
echo ">>> 构建前端..."
cd frontend
npm run build
if [ $? -ne 0 ]; then
    echo "错误: 前端构建失败"
    exit 1
fi
cd ..
echo "  ✅ 前端构建完成 (frontend/dist/)"
echo ""

# 4. 构建 Electron 主进程
echo ">>> 构建 Electron 主进程..."
cd electron
npm run build
if [ $? -ne 0 ]; then
    echo "错误: Electron 主进程构建失败"
    exit 1
fi
cd ..
echo "  ✅ Electron 构建完成 (electron/dist/)"
echo ""

echo "========================================="
echo "  所有构建任务完成！"
echo "========================================="
echo ""
echo "  产物目录:"
# 显示文件数量，给用户反馈
FE_COUNT=$(find frontend/dist -type f 2>/dev/null | wc -l | xargs)
EL_COUNT=$(find electron/dist -type f 2>/dev/null | wc -l | xargs)
echo "    前端: frontend/dist/ ($FE_COUNT 个文件)"
echo "    主进程: electron/dist/ ($EL_COUNT 个文件)"
echo ""
echo "  下一步操作:"
echo "    运行打包脚本: ./scripts/package.sh"
echo ""
