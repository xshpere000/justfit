#!/bin/bash
# JustFit 集成测试脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================"
echo "  JustFit 集成测试"
echo "================================"
echo ""

# 设置测试数据库路径
export JUSTFIT_DB_PATH="${TMPDIR:-/tmp}/justfit_test_${RANDOM}.db"

echo "测试数据库: $JUSTFIT_DB_PATH"
echo ""

# 清理函数
cleanup() {
    echo ""
    echo "清理测试数据库..."
    rm -f "$JUSTFIT_DB_PATH"
}

# 设置退出时清理
trap cleanup EXIT

echo "运行集成测试..."
echo ""

if [ -d "test/integration" ]; then
    go test -v -count=1 ./test/integration/... -timeout=10m || {
        echo -e "${RED}集成测试失败${NC}"
        exit 1
    }
else
    echo -e "${YELLOW}警告: test/integration 目录不存在，跳过集成测试${NC}"
fi

echo ""
echo -e "${GREEN}集成测试完成!${NC}"
