#!/bin/bash
# JustFit 开发模式启动脚本 (网络访问模式)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  JustFit 开发模式 (网络访问模式)${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""

# 获取本机 IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo -e "${YELLOW}本机 IP: $LOCAL_IP${NC}"
echo "局域网内其他电脑可通过此 IP 访问"
echo ""

# 检查 Python 依赖
echo -e "${GREEN}>>> 检查 Python 环境...${NC}"
if ! command -v python3.14 &> /dev/null; then
    echo -e "${RED}错误: python3.14 未找到${NC}"
    exit 1
fi

# 检查 Node.js 依赖
echo -e "${GREEN}>>> 检查 Node.js 环境...${NC}"
if ! command -v npm &> /dev/null; then
    echo -e "${RED}错误: npm 未找到${NC}"
    exit 1
fi

# 确保目录存在
mkdir -p dist/electron

# 函数：清理后台进程
cleanup() {
    echo ""
    echo -e "${YELLOW}>>> 清理后台进程...${NC}"
    pkill -f "uvicorn app.main:app" || true
    pkill -f "vite.*22632" || true
    pkill -f "electron.*JustFit" || true
    echo -e "${GREEN}已清理${NC}"
}

# 注册清理函数
trap cleanup EXIT

# 1. 启动 Python FastAPI 后端 (绑定 0.0.0.0)
echo -e "${GREEN}>>> 启动后端 (端口 22631, 绑定 0.0.0.0)...${NC}"
cd backend
PYTHONPATH=. python3.14 -m uvicorn app.main:app --host 0.0.0.0 --port 22631 --reload &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"
cd ..

# 等待后端启动
echo "  等待后端启动..."
sleep 3

# 2. 启动前端 Vite 开发服务器 (绑定 0.0.0.0)
echo -e "${GREEN}>>> 启动前端 (端口 22632, 绑定 0.0.0.0)...${NC}"
cd frontend
npm run dev -- --host 0.0.0.0 --port 22632 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"
cd ..

# 等待前端启动
echo "  等待前端启动..."
sleep 3

echo ""
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  开发环境已启动！${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo -e "后端 API:"
echo -e "  - 本机:  ${YELLOW}http://localhost:22631${NC}"
echo -e "  - 局域网:${YELLOW}http://$LOCAL_IP:22631${NC}"
echo -e "  - 文档:  ${YELLOW}http://$LOCAL_IP:22631/docs${NC}"
echo ""
echo -e "前端界面:"
echo -e "  - 本机:  ${YELLOW}http://localhost:22632${NC}"
echo -e "  - 局域网:${YELLOW}http://$LOCAL_IP:22632${NC}"
echo ""
echo "  日志文件: $(python3 -c 'from app.config import settings; print(settings.DATA_DIR / \"logs\" / \"justfit.log\")' 2>/dev/null || echo '~/.local/share/justfit/logs/justfit.log')"
echo ""
echo -e "  ${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

# 保持脚本运行，等待用户中断
wait
