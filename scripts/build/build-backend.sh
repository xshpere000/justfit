#!/bin/bash
# JustFit 后端打包脚本 - 使用 PyInstaller 打包 Python 后端为 exe

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
echo -e "${BLUE}  JustFit Backend - PyInstaller Build${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# 确定 Python 命令
PYTHON_CMD=""
if command -v python3.14 &> /dev/null; then
    PYTHON_CMD="python3.14"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}错误: 未找到 Python 安装${NC}"
    exit 1
fi

# 检查 PyInstaller
echo -e "${GREEN}>>> 检查 PyInstaller...${NC}"
if ! $PYTHON_CMD -m PyInstaller --version &> /dev/null; then
    echo -e "${YELLOW}  PyInstaller 未安装，正在安装...${NC}"
    $PYTHON_CMD -m pip install pyinstaller
fi
echo "  Python: $($PYTHON_CMD --version)"
echo "  PyInstaller: $($PYTHON_CMD -m PyInstaller --version)"
echo ""

# 进入后端目录
cd backend

# 清理旧的构建
echo -e "${GREEN}>>> 清理旧的构建文件...${NC}"
rm -rf build/ dist/
echo ""

# 执行打包
echo -e "${GREEN}>>> 开始打包后端...${NC}"
if [ -f "justfit_backend.spec" ]; then
    echo "  使用 spec 文件打包..."
    $PYTHON_CMD -m PyInstaller justfit_backend.spec --clean --noconfirm
else
    echo -e "${YELLOW}  未发现 spec 文件，使用默认参数...${NC}"
    $PYTHON_CMD -m PyInstaller -F -n justfit_backend app/main.py --clean
fi
echo ""

# 验证结果
if [ -f "dist/justfit_backend.exe" ] || [ -f "dist/justfit_backend" ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  后端打包成功！${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""

    # 显示文件大小
    if [ -f "dist/justfit_backend.exe" ]; then
        SIZE=$(ls -lh dist/justfit_backend.exe | awk '{print $5}')
        echo "  输出文件: backend/dist/justfit_backend.exe"
        echo "  文件大小: $SIZE"
    elif [ -f "dist/justfit_backend" ]; then
        SIZE=$(ls -lh dist/justfit_backend | awk '{print $5}')
        echo "  输出文件: backend/dist/justfit_backend"
        echo "  文件大小: $SIZE"
    fi
    echo ""
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}  后端打包失败！${NC}"
    echo -e "${RED}=========================================${NC}"
    echo "  未找到输出文件，请检查构建日志中的错误。"
    exit 1
fi
