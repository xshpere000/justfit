# JustFit v0.0.2 开发文档

## 快速开始

```bash
# 开发模式
wails dev

# 生产构建
wails build

# 运行测试
go test ./...
```

## 核心变更 (v0.0.2)

### 1. 命名规范统一

**问题**：前后端字段名不一致导致数据丢失

**解决**：统一使用驼峰命名（首字母小写）

```typescript
// ✅ 正确
vmCount: number
selectedVMs: string[]
cpuMhz: number
memoryMb: number

// ❌ 错误
VMCount: number
selectedVms: string[]
cpuMHz: number
memoryMB: number
```

### 2. 修改文件

- 前端：11 个文件
- 后端：9 个文件
- 总计：20 个文件

详见 `CHANGELOG.md`

## API 快速参考

### 连接管理

```typescript
// 获取所有连接
ConnectionAPI.listConnections()

// 创建连接
ConnectionAPI.createConnection({
  name: string,
  platform: 'vcenter' | 'h3c-uis',
  host: string,
  port: number,
  username: string,
  password: string,
  insecure: boolean
})
```

### 任务管理

```typescript
// 创建采集任务
TaskAPI.createCollectTask({
  name: string,
  connectionId: number,
  connectionName: string,
  platform: string,
  dataTypes: ['clusters', 'hosts', 'vms', 'metrics'],
  metricsDays: number,
  vmCount: number,
  selectedVMs: string[]
})

// 获取任务列表
TaskAPI.listTasks(status, limit, offset)

// 获取任务详情
TaskAPI.getTaskDetail(taskId)
```

### 分析功能

```typescript
// 僵尸 VM 检测
AnalysisAPI.detectZombieVMs(connectionId, {
  analysisDays: 30,
  cpuThreshold: 5,
  memoryThreshold: 10,
  minConfidence: 0.7
})

// Right Size 分析
AnalysisAPI.analyzeRightSize(connectionId, {
  analysisDays: 30,
  bufferRatio: 0.2
})
```

## 字段命名速查表

| 类型 | 正确写法 | 错误写法 |
|------|---------|---------|
| VM 数量 | `vmCount` | `VMCount`, `totalVms` |
| 选中的 VM | `selectedVMs` | `selectedVms` |
| CPU 频率 | `cpuMhz` | `cpuMHz`, `CPUMhz` |
| 内存 MB | `memoryMb` | `memoryMB` |
| 内存 GB | `memoryGb` | `memoryGB` |
| 连接 ID | `connectionId` | `ConnectionID` |

## 常见问题

### Q: 数据不显示怎么办？

1. 打开浏览器控制台（F12）
2. 查看是否有字段名错误
3. 确认后端日志中的字段名

### Q: 如何添加新的分析类型？

1. 后端：在 `internal/analyzer/` 添加分析器
2. 后端：在 `app.go` 注册 API
3. 前端：在 `types/api.ts` 添加类型定义
4. 前端：创建对应的分析组件

### Q: 字段命名规范？

查看 `CLAUDE.md` 中的"强制命名规范"章节。

## 版本历史

- v0.0.2 (2026-02-26): 命名规范统一
- v0.0.1 (2026-02-20): 初始版本
