#!/bin/bash
# JustFit 前端打包脚本 - 打包 Vue 3 前端为静态文件

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
echo -e "${BLUE}  JustFit Frontend - Production Build${NC}"
echo -e "${BLUE}=========================================${NC}"
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

# 进入前端目录
cd frontend

# 清理旧的构建
echo -e "${GREEN}>>> 清理旧的构建文件...${NC}"
rm -rf dist/
echo ""

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo -e "${GREEN}>>> 安装前端依赖...${NC}"
    npm install
    echo ""
fi

# 执行构建
echo -e "${GREEN}>>> 开始构建前端...${NC}"
npm run build
echo ""

# 验证结果
cd "$PROJECT_ROOT"
if [ -d "frontend/dist" ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  前端构建成功！${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "  输出目录: frontend/dist/"
    echo ""
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}  前端构建失败！${NC}"
    echo -e "${RED}=========================================${NC}"
    exit 1
fi
