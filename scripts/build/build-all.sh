#!/bin/bash
# JustFit 一键打包脚本 - 完整打包前端、后端、Electron

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  JustFit - 完整打包流程${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""
echo "  此脚本将依次执行："
echo "    1. 打包前端 (Vue 3 → 静态文件)"
echo "    2. 打包后端 (Python → exe)"
echo "    3. 打包 Electron (桌面应用)"
echo ""
echo -e "${YELLOW}按 Ctrl+C 可随时中断${NC}"
echo ""
sleep 2

# 步骤 1: 打包前端
echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  步骤 1/3: 打包前端${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""
if ! bash "$SCRIPT_DIR/build-frontend.sh"; then
    echo -e "${RED}前端打包失败，终止流程${NC}"
    exit 1
fi
echo ""

# 步骤 2: 打包后端
echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  步骤 2/3: 打包后端${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""
if ! bash "$SCRIPT_DIR/build-backend.sh"; then
    echo -e "${RED}后端打包失败，终止流程${NC}"
    exit 1
fi
echo ""

# 步骤 3: 打包 Electron
echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  步骤 3/3: 打包 Electron${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""
if ! bash "$SCRIPT_DIR/package-electron.sh"; then
    echo -e "${RED}Electron 打包失败，终止流程${NC}"
    exit 1
fi
echo ""

# 完成
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  全部打包完成！${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "  打包产物位置："
echo "    前端: frontend/dist/"
echo "    后端: backend/dist/justfit_backend.exe"
echo "    Electron: electron/dist/"
echo ""
echo -e "${GREEN}  构建成功！🎉${NC}"
echo ""
