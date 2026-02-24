#!/bin/bash
# JustFit 单元测试脚本

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
echo "  JustFit 单元测试"
echo "================================"
echo ""

# 检查 Go 环境
if ! command -v go &> /dev/null; then
    echo -e "${RED}错误: Go 未安装${NC}"
    exit 1
fi

# 创建覆盖率目录
mkdir -p coverage

echo "运行单元测试..."
echo ""

# 运行单元测试（如果有的话）
if [ -d "test/unit" ]; then
    go test -v -race -count=1 ./test/unit/... \
        -coverprofile=coverage/unit_coverage.out \
        -timeout=5m || {
        echo -e "${RED}单元测试失败${NC}"
        exit 1
    }
else
    echo -e "${YELLOW}警告: test/unit 目录不存在，跳过单元测试${NC}"
fi

echo ""
echo "生成覆盖率报告..."

# 合并覆盖率（如果有多个包）
if [ -f "coverage/unit_coverage.out" ]; then
    echo ""
    echo "总体覆盖率:"
    go tool cover -func=coverage/unit_coverage.out | grep "total:"

    # 生成 HTML 报告
    go tool cover -html=coverage/unit_coverage.out -o coverage/unit_coverage.html
    echo -e "${GREEN}覆盖率报告已生成: coverage/unit_coverage.html${NC}"
fi

echo ""
echo "运行基准测试..."
if [ -d "test/unit" ]; then
    go test -bench=. -benchmem -benchtime=1s ./test/unit/... -timeout=5m || true
fi

echo ""
echo -e "${GREEN}单元测试完成!${NC}"
