#!/bin/bash
# JustFit Electron 打包脚本 - 基于已打包的前后端打包 Electron 桌面应用

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  JustFit - Electron Packaging${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# 检查前置条件
echo -e "${GREEN}>>> 检查打包产物...${NC}"

# 检查前端构建产物
if [ ! -d "frontend/dist" ]; then
    echo -e "${RED}错误: 前端构建产物不存在${NC}"
    echo "  请先运行: make build-frontend 或 ./scripts/build/build-frontend.sh"
    exit 1
fi
echo -e "${GREEN}  ✓ 前端构建产物存在${NC}"

# 检查后端构建产物
BACKEND_EXE=""
if [ -f "backend/dist/justfit_backend.exe" ]; then
    BACKEND_EXE="$(pwd)/backend/dist/justfit_backend.exe"
elif [ -f "backend/dist/justfit_backend" ]; then
    BACKEND_EXE="$(pwd)/backend/dist/justfit_backend"
else
    echo -e "${RED}错误: 后端构建产物不存在${NC}"
    echo "  请先运行: make build-backend 或 ./scripts/build/build-backend.sh"
    exit 1
fi
echo -e "${GREEN}  ✓ 后端构建产物存在${NC}"
echo ""

# 检查 Node.js 环境
echo -e "${GREEN}>>> 检查 Node.js 环境...${NC}"
if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: npm 未找到${NC}"
    exit 1
fi
echo "  Node: $(node --version)"
echo "  npm:  $(npm --version)"
echo ""

# 进入 electron 目录
cd electron

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo -e "${GREEN}>>> 安装 Electron 依赖...${NC}"
    npm install
    echo ""
fi

# 准备后端 exe 到资源目录
echo -e "${GREEN}>>> 准备后端资源...${NC}"
mkdir -p ../resources/backend
cp "$BACKEND_EXE" ../resources/backend/
echo "  已复制后端 exe 到 resources/backend/"
echo ""

# 构建 Electron 主进程
echo -e "${GREEN}>>> 构建 Electron 主进程...${NC}"
npm run build
echo ""

# 执行打包
echo -e "${GREEN}>>> 开始打包 Electron 应用...${NC}"
npm run package
echo ""

# 验证结果
cd "$PROJECT_ROOT"
if [ -d "dist/electron" ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  Electron 打包成功！${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "  输出目录: dist/electron/"
    echo ""

    # 显示安装包信息
    if ls dist/electron/*.{exe,AppImage,dmg,deb,rpm} 1> /dev/null 2>&1; then
        echo "  安装包:"
        ls -lh dist/electron/*.{exe,AppImage,dmg,deb,rpm} 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}'
    fi
    echo ""
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}  Electron 打包失败！${NC}"
    echo -e "${RED}=========================================${NC}"
    exit 1
fi

