#!/bin/bash
# 检查数据库中的任务和分析结果

DB_PATH="${JUSTFIT_DATA_DIR:-.justfit}/justfit.db"

if [ ! -f "$DB_PATH" ]; then
    echo "数据库文件不存在: $DB_PATH"
    echo "检查其他可能的位置..."
    find ~ -name "justfit.db" -type f 2>/dev/null | head -5
    exit 1
fi

echo "=== 数据库位置: $DB_PATH ==="
echo ""
echo "=== 任务表 ==="
sqlite3 "$DB_PATH" "SELECT id, type, status, created_at FROM tasks ORDER BY id DESC LIMIT 10;"
echo ""
echo "=== 分析结果表 ==="
sqlite3 "$DB_PATH" "SELECT id, task_id, analysis_type, substr(data, 1, 50) as data_preview, created_at FROM task_analysis_results ORDER BY id DESC LIMIT 10;"
echo ""
echo "=== 任务快照表 ==="
sqlite3 "$DB_PATH" "SELECT task_id, COUNT(*) as vm_count FROM task_vm_snapshots GROUP BY task_id ORDER BY task_id DESC LIMIT 5;"
