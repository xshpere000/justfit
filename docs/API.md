# JustFit API 文档

## 基础信息

- **Base URL**: `http://localhost:22631`
- **Content-Type**: `application/json`

## 统一响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

## API 端点

### 连接管理

#### 创建连接

```http
POST /api/connections
Content-Type: application/json

{
  "name": "生产环境 vCenter",
  "platform": "vcenter",
  "host": "192.168.1.100",
  "port": 443,
  "username": "administrator@vsphere.local",
  "password": "password",
  "insecure": true
}
```

#### 连接列表

```http
GET /api/connections
```

#### 获取连接详情

```http
GET /api/connections/{id}
```

#### 更新连接

```http
PUT /api/connections/{id}
Content-Type: application/json

{
  "name": "新名称",
  "host": "192.168.1.101"
}
```

#### 删除连接

```http
DELETE /api/connections/{id}
```

#### 测试连接

```http
POST /api/connections/{id}/test
```

### 资源查询

#### 获取集群列表

```http
GET /api/resources/connections/{id}/clusters
```

#### 获取主机列表

```http
GET /api/resources/connections/{id}/hosts
```

#### 获取虚拟机列表

```http
GET /api/resources/connections/{id}/vms
```

#### 数据采集

```http
POST /api/resources/connections/{id}/collect
```

### 任务管理

#### 创建任务

```http
POST /api/tasks
Content-Type: application/json

{
  "name": "评估任务",
  "type": "collection",
  "connectionId": 1,
  "config": {
    "collectMetrics": true,
    "days": 7
  }
}
```

#### 任务列表

```http
GET /api/tasks?status=running&limit=20
```

#### 获取任务详情

```http
GET /api/tasks/{id}
```

#### 取消任务

```http
POST /api/tasks/{id}/cancel
```

#### 删除任务

```http
DELETE /api/tasks/{id}
```

#### 获取任务日志

```http
GET /api/tasks/{id}/logs
```

#### 获取 VM 快照

```http
GET /api/tasks/{id}/vm-snapshots
```

### 分析

#### 获取分析模式

```http
GET /api/analysis/modes
```

#### 获取特定模式

```http
GET /api/analysis/modes/{mode}
```

模式值: `safe`, `saving`, `aggressive`, `custom`

#### 更新自定义模式

```http
PUT /api/analysis/modes/custom
Content-Type: application/json

{
  "analysisType": "zombie",
  "config": {
    "days": 14,
    "cpuThreshold": 10
  }
}
```

#### 运行僵尸 VM 分析

```http
POST /api/analysis/tasks/{taskId}/zombie
Content-Type: application/json

{
  "mode": "saving"
}
```

#### 获取僵尸 VM 结果

```http
GET /api/analysis/tasks/{taskId}/zombie
```

#### 运行 Right Size 分析

```http
POST /api/analysis/tasks/{taskId}/rightsize
```

#### 运行潮汐模式分析

```http
POST /api/analysis/tasks/{taskId}/tidal
```

#### 运行健康评分分析

```http
POST /api/analysis/tasks/{taskId}/health
```

#### 获取健康评分结果

```http
GET /api/analysis/tasks/{taskId}/health
```

### 报告

#### 生成报告

```http
POST /api/reports/tasks/{taskId}/reports
Content-Type: application/json

{
  "format": "excel"
}
```

格式: `excel`, `pdf`

#### 获取任务报告列表

```http
GET /api/reports/tasks/{taskId}/reports
```

#### 下载报告

```http
GET /api/reports/{reportId}/download
```

#### 删除报告

```http
DELETE /api/reports/{reportId}
```

### 系统

#### 健康检查

```http
GET /api/system/health
```

#### 版本信息

```http
GET /api/system/version
```

#### 统计数据

```http
GET /api/system/stats
```

## WebSocket

### 任务进度推送

```
WS /ws/tasks/{taskId}/progress
```

推送消息格式：

```json
{
  "taskId": 1,
  "status": "running",
  "progress": 45.5,
  "message": "正在采集虚拟机指标...",
  "timestamp": "2025-03-05T13:00:00Z"
}
```

## 错误代码

| 代码 | 说明 |
|------|------|
| `CONNECTION_NOT_FOUND` | 连接不存在 |
| `INVALID_CREDENTIALS` | 连接凭据无效 |
| `TASK_NOT_FOUND` | 任务不存在 |
| `INVALID_MODE` | 无效的分析模式 |
| `ANALYSIS_ERROR` | 分析执行失败 |
| `REPORT_NOT_FOUND` | 报告不存在 |
| `FILE_NOT_FOUND` | 文件不存在 |
