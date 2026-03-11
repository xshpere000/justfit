#!/bin/bash
# JustFit 后端启动脚本（无 reload 模式）

echo "======================================"
echo "JustFit 后端启动（无 reload 模式）"
echo "======================================"
echo ""
echo "启动时间: $(date)"
echo "工作目录: $(pwd)"
echo ""

# 检查 Python 版本
python3.14 --version

echo ""
echo "启动后端..."
echo "如果后端自动关闭，请按 Ctrl+C 并查看上面的日志"
echo ""

# 不使用 reload 模式启动
PYTHONPATH=. python3.14 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 22631 \
    --log-level info \
    --access-log \
    --no-date-header

echo ""
echo "后端已停止"
echo "停止时间: $(date)"
