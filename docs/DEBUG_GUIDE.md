# Debug 模式启动指南

## 快速启动 Debug

```bash
# 1. 清理环境（如有需要）
make clean

# 2. 启动开发模式
make dev
```

## 分别启动前后端

### 后端单独调试

```bash
cd backend
uvicorn app.main:app --reload --port 22631 --log-level debug
```

- API 文档: http://localhost:22631/docs
- 健康检查: http://localhost:22631/api/system/health

### 前端单独调试

```bash
cd frontend
npm run dev
```

- 前端地址: http://localhost:22632

## 常见 Debug 场景

### 1. 连接问题

```bash
# 检查 vCenter 连接
curl -X POST http://localhost:22631/api/connections/1/test
```

### 2. 数据库问题

```bash
# 查看数据库（Linux/macOS）
sqlite3 ~/.local/share/justfit/justfit.db

# 查看数据库（Windows，在 Git Bash 中）
sqlite3 "$LOCALAPPDATA/justfit/justfit.db"

# 查看所有表
.tables

# 查看连接
SELECT * FROM connections;

# 查看任务
SELECT * FROM assessment_tasks ORDER BY id DESC LIMIT 5;
```

### 3. Python 断点调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用 ipdb（需要安装）
import ipdb; ipdb.set_trace()
```

### 4. 查看日志

```bash
# 后端日志（如果启动了）
tail -f logs/backend.log

# Electron 日志
tail -f logs/electron.log
```

## 重置数据

```bash
# 删除数据库重新开始（Linux/macOS）
rm ~/.local/share/justfit/justfit.db

# 删除数据库重新开始（Windows，在 Git Bash 中）
rm "$LOCALAPPDATA/justfit/justfit.db"

# 删除加密凭据（Linux/macOS）
rm ~/.local/share/justfit/credentials.enc
rm ~/.local/share/justfit/.key

# 删除加密凭据（Windows，在 Git Bash 中）
rm "$LOCALAPPDATA/justfit/credentials.enc"
rm "$LOCALAPPDATA/justfit/.key"
```

## 测试覆盖

```bash
# 运行特定测试
pytest tests/backend/integration/test_connectors.py -v -s

# E2E 测试
PYTHONPATH=backend pytest tests/backend/e2e/ -v -s
```
