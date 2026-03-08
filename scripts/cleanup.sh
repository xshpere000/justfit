#!/bin/bash
# JustFit 项目清理脚本
# 清理所有临时文件、缓存文件和残留文件

set -e

PROJECT_ROOT="/home/worker/pengxin/justfit"
cd "$PROJECT_ROOT"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          JustFit 项目清理工具                                 ║"
echo "║          清理临时文件、缓存和残留                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 统计函数
count_files() {
    find "$PROJECT_ROOT" -type f "$@" 2>/dev/null | wc -l
}

echo "📊 清理前统计..."
echo ""

# Python 缓存文件
PYC_COUNT=$(count_files -name "*.pyc")
PYCACHE_DIRS=$(find "$PROJECT_ROOT" -type d -name "__pycache__" 2>/dev/null | wc -l)
echo "  Python .pyc 文件:        $PYC_COUNT"
echo "  __pycache__ 目录:       $PYCACHE_DIRS"

# 数据库文件
DB_SIZE=$(du -sh ~/.local/share/justfit/justfit.db 2>/dev/null | cut -f1)
echo "  数据库文件大小:         $DB_SIZE"

# 前端构建产物
if [ -d "frontend/dist" ]; then
    DIST_SIZE=$(du -sh frontend/dist 2>/dev/null | cut -f1)
    echo "  前端 dist 大小:         $DIST_SIZE"
fi

echo ""
echo "🧹 开始清理..."
echo ""

# 1. 清理 Python 缓存
echo "  [1/5] 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo "       ✅ Python 缓存已清理"

# 2. 清理日志文件
echo "  [2/5] 清理日志文件..."
rm -f ~/.local/share/justfit/logs/*.log 2>/dev/null || true
echo "       ✅ 日志文件已清理"

# 3. 清理前端缓存
echo "  [3/5] 清理前端缓存..."
rm -rf frontend/node_modules/.vite 2>/dev/null || true
rm -rf frontend/.eslintcache 2>/dev/null || true
echo "       ✅ 前端缓存已清理"

# 4. 清理临时文件
echo "  [4/5] 清理临时文件..."
find . -type f \( -name "*.tmp" -o -name "*.swp" -o -name "*.swo" -o -name ".DS_Store" \) -delete 2>/dev/null || true
find . -type f \( -name "*.orig" -o -name "*.bak" -o -name "*~" \) -delete 2>/dev/null || true
echo "       ✅ 临时文件已清理"

# 5. 清理测试残留
echo "  [5/5] 清理测试残留..."
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name ".coverage" -o -name "coverage.xml" \) -delete 2>/dev/null || true
echo "       ✅ 测试残留已清理"

echo ""
echo "✅ 清理完成！"
echo ""

# 显示清理后的统计
echo "📊 清理后统计..."
echo ""

# 统计清理后的文件
REMAINING_PYC=$(count_files -name "*.pyc")
REMAINING_CACHE=$(find "$PROJECT_ROOT" -type d -name "__pycache__" 2>/dev/null | wc -l)

echo "  剩余 Python .pyc:      $REMAINING_PYC"
echo "  剩余 __pycache__:       $REMAINING_CACHE"
echo ""

echo "💡 提示："
echo "  • Python 缓存会在运行时自动重建"
echo "  • 数据库文件 (~/.local/share/justfit/justfit.db) 需要手动删除"
echo "  • 前端 node_modules 如需清理: cd frontend && npm run clean"
echo ""

# 检查是否还有残留文件
REMAINING=0
if [ -f ~/.local/share/justfit/justfit.db ]; then
    echo "⚠️  数据库文件仍然存在:"
    echo "   ~/.local/share/justfit/justfit.db"
    echo "   如需删除: rm ~/.local/share/justfit/justfit.db"
    REMAINING=1
fi

if [ "$REMAINING" -eq 0 ]; then
    echo "✨ 所有临时文件已清理完成！"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
