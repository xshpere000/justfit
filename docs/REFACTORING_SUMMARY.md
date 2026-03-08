# JustFit 重构知识总结

> 从 Wails v2 (Go + Vue 3) 重构到 Electron (Node.js + Python FastAPI + Vue 3)

## 一、架构对比

### 旧架构 (Wails v2)
```
┌─────────────────────────────────────────┐
│           Wails Desktop App             │
│  ┌─────────────┐    ┌─────────────────┐  │
│  │   Go 后端    │◄──►│  Vue 3 前端     │  │
│  │  (嵌入进程)  │    │  (WebView)      │  │
│  └─────────────┘    └─────────────────┘  │
│  ↓                                       │
│  SQLite                                  │
└─────────────────────────────────────────┘
```

### 新架构 (Electron + Python)
```
┌─────────────────────────────────────────┐
│          Electron Shell                 │
│  ┌─────────────┐    ┌─────────────────┐  │
│  │ Renderer    │    │    Main         │  │
│  │ Vue 3 前端  │◄──►│  Node.js        │  │
│  └──────┬──────┘    │  (spawn)        │  │
│         │ HTTP      │        ↓         │  │
│         ▼           │  Python 子进程   │  │
│  ┌─────────────────┐│  FastAPI        │  │
│  │  REST API       ││  (localhost:22631)│
│  └─────────────────┘└──────────────────┘  │
│                                          │
│  SQLite (独立文件)                       │
└─────────────────────────────────────────┘
```

## 二、关键差异与迁移点

### 1. 进程通信

| 方面 | Wails | Electron + Python |
|------|-------|-------------------|
| 通信方式 | 函数绑定 (Go ⇄ JS) | HTTP REST API |
| 优点 | 直接、类型安全 | 标准化、可独立测试 |
| 缺点 | 紧耦合、难扩展 | 网络开销、序列化 |

**迁移模式示例**：

```go
// Wails - 直接调用
// app.go
func GetConnections() []Connection {
    return storage.GetAll()
}

// 前端
import { GetConnections } from '../../wailsjs/go/backend/App'
const conns = await GetConnections()
```

```python
# FastAPI - REST API
# routers/connection.py
@router.get("/api/connections")
async def list_connections(db: AsyncSession = Depends(get_db)):
    connections = await service.list_connections()
    return {"success": True, "data": connections}

# 前端
import { apiClient } from './client'
const response = await apiClient.get('/api/connections')
const conns = response.data.data.items
```

### 2. 数据库

| 方面 | Wails (Go) | Electron + Python |
|------|------------|-------------------|
| ORM | GORM | SQLAlchemy |
| 迁移 | AutoMigrate | Alembic |
| 风格 | 链式调用 | 声明式 |

**模型定义对比**：

```go
// Go - GORM
type Connection struct {
    ID        uint   `gorm:"primaryKey"`
    Name      string `gorm:"size:100"`
    Platform  string `gorm:"size:20"`
    Host      string `gorm:"size:255"`
    CreatedAt time.Time
    UpdatedAt time.Time
}
```

```python
# Python - SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class Connection(Base, TimestampMixin):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(20))
    host: Mapped[str] = mapped_column(String(255))
```

### 3. 并发模型

| 方面 | Go | Python |
|------|-----|--------|
| 原语 | goroutine | asyncio |
| 同步 | WaitGroup | asyncio.gather() |
| 限制 | semaphore | asyncio.Semaphore |

**并发采集对比**：

```go
// Go
sem := make(chan struct{}, 5)
var wg sync.WaitGroup
for _, vm := range vms {
    wg.Add(1)
    go func(vm VM) {
        defer wg.Done()
        sem <- struct{}{}
        defer func() { <-sem }()
        collectVM(vm)
    }(vm)
}
wg.Wait()
```

```python
# Python
async def collect_vms(vms: list[VM]):
    semaphore = asyncio.Semaphore(5)
    async def collect_one(vm):
        async with semaphore:
            return await collect_vm(vm)
    return await asyncio.gather(*[collect_one(vm) for vm in vms])
```

### 4. 凭据安全

| 方面 | Go | Python |
|------|-----|--------|
| 加密 | crypto/aes | cryptography.hazmat |
| 密钥派生 | pbkdf2 | scrypt |
| 存储文件 | credentials.json | credentials.enc |

## 三、重构中的关键决策

### 决策 1：为什么选择 HTTP 而非 IPC？

- **标准化**：REST API 是行业标准
- **可测试性**：可以独立测试后端
- **灵活性**：未来可以拆分为微服务
- **权衡**：序列化开销（在本地可忽略）

### 决策 2：为什么使用独立 Python 进程？

- **隔离性**：后端崩溃不影响 UI
- **调试友好**：可以单独调试 FastAPI
- **部署灵活**：可以选择部署方式
- **权衡**：进程管理复杂度

### 决策 3：字段命名规范

| 层级 | 规范 | 示例 |
|------|------|------|
| 数据库 | snake_case | `connection_id` |
| Python | snake_case | `connection_id` |
| JSON API | camelCase | `connectionId` |
| TypeScript | camelCase | `connectionId` |

使用 Pydantic 的 `alias_generator` 自动转换：

```python
from pydantic import BaseModel

def to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
```

## 四、常见问题与解决

### 问题 1：数据库会话隔离

**现象**：测试中数据不可见

**原因**：每个请求创建新会话，但未正确提交

**解决**：
```python
async def override_get_db():
    async with session_maker() as session:
        try:
            yield session
            await session.commit()  # 关键！
        except Exception:
            await session.rollback()
            raise
```

### 问题 2：异步上下文丢失

**现象**：同步库在异步函数中阻塞

**解决**：使用异步版本库
- `sqlite3` → `aiosqlite`
- `requests` → `httpx`
- `open` → `aiofiles`

### 问题 3：Electron 窗口控制

**需求**：自定义窗口按钮（最小化/最大化/关闭）

**解决**：
```typescript
// preload.ts
window.electronAPI = {
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
}

// main.ts
ipcMain.on('window:minimize', () => mainWindow.minimize())
```

### 问题 4：vCenter 指标采集空值

**原因**：使用历史间隔而非实时间隔

**解决**：
```python
# 使用 20 秒实时间隔
perf_manager = si.content.perfManager
metric_id = vim.PerformanceManager.MetricId(counterId=counter_id, instance="")

# 不要用 "*"，用 ""
query_specs = [vim.PerformanceManager.QuerySpec(
    entity=vm,
    metricId=[metric_id],
    startTime=start_time,
    endTime=end_time,
    intervalId=20,  # 实时间隔
    maxSample=1000,
)]
```

## 五、调试技巧

### 1. 查看 FastAPI 自动文档

```bash
cd backend
uvicorn app.main:app --reload --port 22631
# 访问 http://localhost:22631/docs
```

### 2. 检查 Python 进程

```bash
# 查看 Python 子进程
ps aux | grep uvicorn

# 杀死僵尸进程
pkill -f uvicorn
```

### 3. 前端 API 调试

```typescript
// 在 apiClient 中添加拦截器
apiClient.interceptors.request.use(config => {
  console.log('[API Request]', config.method?.toUpperCase(), config.url)
  return config
})

apiClient.interceptors.response.use(response => {
  console.log('[API Response]', response.status, response.data)
  return response
})
```

### 4. 数据库查看

```bash
# 使用 sqlite3 命令行
sqlite3 ~/.justfit/data.db

# 常用命令
.tables
.schema connections
SELECT * FROM assessment_tasks;
```

## 六、性能优化建议

### 1. 数据库连接池

```python
engine = create_async_engine(
    f"sqlite+aiosqlite:///{db_path}",
    pool_size=10,
    max_overflow=20,
)
```

### 2. API 响应缓存

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_analysis_modes():
    return load_modes_from_db()
```

### 3. 前端代码分割

```typescript
// router/index.ts
const routes = [
  {
    path: '/task/:id',
    component: () => import('@/views/TaskDetail.vue')
  }
]
```

## 七、测试策略

### 后端测试

```bash
# 单元测试
pytest tests/backend/unit/

# 集成测试
pytest tests/backend/integration/

# E2E 测试
pytest tests/backend/e2e/
```

### 前端测试

```bash
# 组件测试
npm test

# 测试覆盖率
npm run test:coverage
```

## 八、部署检查清单

- [ ] Python 版本 >= 3.14
- [ ] Node.js 版本 >= 18
- [ ] 数据库迁移已执行
- [ ] 环境变量已配置
- [ ] 日志目录可写
- [ ] 应用图标已设置
- [ ] 打包配置正确

## 九、下一步（Debug 模式）

### 可能的 Debug 场景

1. **连接失败**：检查 vCenter 凭据、网络、证书
2. **采集卡住**：检查并发限制、超时设置
3. **分析无结果**：检查指标数据是否完整
4. **报告生成失败**：检查字体文件、输出目录权限
5. **前端白屏**：检查 API 连接、控制台错误

### Debug 工具

| 工具 | 用途 |
|------|------|
| `pdb` | Python 断点调试 |
| `console.log` | 前端日志 |
| DevTools | 浏览器调试 |
| `sqlite3` | 数据库查询 |
| `pytest -vv` | 详细测试输出 |

---

**版本**: v0.0.3
**更新日期**: 2025-03-05
