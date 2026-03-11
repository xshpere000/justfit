# JustFit API 文档

## 基础信息

- **Base URL**: `http://localhost:22631`
- **Content-Type**: `application/json`
- **API 版本**: `v0.0.3`

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

---

# 连接管理 API

## 创建连接

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

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 连接名称 |
| platform | string | 是 | 平台类型: `vcenter` 或 `h3c-uis` |
| host | string | 是 | 主机地址 |
| port | integer | 否 | 端口，默认 443 |
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| insecure | boolean | 否 | 是否跳过SSL验证，默认 false |

**响应:**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "生产环境 vCenter",
    "platform": "vcenter",
    "host": "192.168.1.100",
    "port": 443,
    "username": "administrator@vsphere.local",
    "insecure": true,
    "status": "disconnected",
    "lastSync": null,
    "createdAt": "2025-03-09T10:00:00Z",
    "updatedAt": "2025-03-09T10:00:00Z"
  }
}
```

## 连接列表

```http
GET /api/connections
```

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "生产环境 vCenter",
        "platform": "vcenter",
        "host": "192.168.1.100",
        "port": 443,
        "username": "administrator@vsphere.local",
        "insecure": true,
        "status": "connected",
        "lastSync": "2025-03-09T12:00:00Z",
        "createdAt": "2025-03-09T10:00:00Z",
        "updatedAt": "2025-03-09T12:00:00Z"
      }
    ],
    "total": 1
  }
}
```

## 获取连接详情

```http
GET /api/connections/{connection_id}
```

## 更新连接

```http
PUT /api/connections/{connection_id}
Content-Type: application/json

{
  "name": "新名称",
  "host": "192.168.1.101"
}
```

**请求参数:** 所有字段都是可选的

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 连接名称 |
| host | string | 主机地址 |
| port | integer | 端口 |
| username | string | 用户名 |
| password | string | 密码 |
| insecure | boolean | 是否跳过SSL验证 |

## 删除连接

```http
DELETE /api/connections/{connection_id}
```

## 测试连接

```http
POST /api/connections/{connection_id}/test
```

**响应:**

```json
{
  "success": true,
  "data": {
    "status": "connected",
    "message": "连接成功",
    "version": "7.0.3",
    "reachable": true
  }
}
```

## 测试连接并获取VM列表

```http
POST /api/connections/{connection_id}/test-and-fetch-vms
```

此端点用于向导中验证连接并获取VM列表，不执行完整的资源采集。

**响应:**

```json
{
  "success": true,
  "data": {
    "status": "connected",
    "message": "成功连接，获取到 15 台虚拟机",
    "vms": [
      {
        "id": 0,
        "name": "vm-001",
        "datacenter": "DC01",
        "uuid": "5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "vmKey": "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "cpuCount": 4,
        "memoryGb": 16.0,
        "powerState": "poweredOn",
        "guestOs": "CentOS 7",
        "ipAddress": "192.168.1.10",
        "hostIp": "192.168.1.100",
        "connectionState": "connected"
      }
    ],
    "total": 15
  }
}
```

---

# 任务管理 API

## 创建任务

```http
POST /api/tasks
Content-Type: application/json

{
  "name": "评估任务",
  "type": "collection",
  "connectionId": 1,
  "mode": "saving",
  "metricDays": 7,
  "config": {
    "platform": "vcenter",
    "connectionName": "生产环境 vCenter",
    "connectionHost": "192.168.1.100",
    "selectedVMs": [
      "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
      "conn1:uuid:6028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e"
    ],
    "selectedVMCount": 2
  }
}
```

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 任务名称 |
| type | string | 是 | 任务类型: `collection` |
| connectionId | integer | 是 | 连接ID |
| mode | string | 否 | 分析模式：`safe`/`saving`/`aggressive`/`custom`，默认 `saving` |
| baseMode | string | 否 | 仅 mode=custom 时有效，基础预设模式，默认 `saving` |
| metricDays | integer | 否 | 指标采集天数(1-90)，默认 30 |
| config | object | 否 | 任务配置 |

**config 配置:**

| 字段 | 类型 | 说明 |
|------|------|------|
| platform | string | 平台类型 |
| connectionName | string | 连接名称 |
| connectionHost | string | 连接主机 |
| selectedVMs | array | 选中的VM key列表 |
| selectedVMCount | integer | 选中VM数量 |
| customConfig | object | **仅 mode=custom 时有效**，自定义分析参数 |

**customConfig 结构:**

```json
{
  "customConfig": {
    "idle": {
      "days": 30,
      "cpu_threshold": 10.0,
      "memory_threshold": 20.0,
      "min_confidence": 60.0
    },
    "resource": {
      "rightsize": {
        "days": 7,
        "cpu_buffer_percent": 20.0,
        "memory_buffer_percent": 20.0,
        "min_confidence": 60.0
      },
      "usage_pattern": {
        "cv_threshold": 0.4,
        "peak_valley_ratio": 2.5
      },
      "mismatch": {
        "cpu_low_threshold": 30.0,
        "cpu_high_threshold": 70.0,
        "memory_low_threshold": 30.0,
        "memory_high_threshold": 70.0
      }
    },
    "health": {
      "overcommit_threshold": 1.5,
      "hotspot_threshold": 7.0,
      "balance_threshold": 0.6
    }
  }
}
```

**响应 (Lite 版本):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "评估任务",
    "type": "collection",
    "status": "running",
    "progress": 0,
    "error": null,
    "connectionId": 1,
    "currentStep": "正在采集资源...",
    "analysisResults": {
      "idle": false,
      "resource": false,
      "health": false
    },
    "platform": "vcenter",
    "connectionName": "生产环境 vCenter",
    "connectionHost": "192.168.1.100",
    "selectedVMCount": 2,
    "collectedVMCount": 0,
    "createdAt": "2025-03-09T10:00:00Z",
    "startedAt": "2025-03-09T10:00:01Z",
    "completedAt": null
  }
}
```

任务创建后会自动在后台执行完整的采集和分析流程。

## 任务列表

```http
GET /api/tasks?status=running&limit=20
```

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选: `pending`, `running`, `completed`, `failed`, `cancelled` |
| limit | integer | 否 | 返回数量，默认 100 |

**响应:** 返回 Lite 版本任务数据（仅卡片显示必要字段）

## 获取任务详情

```http
GET /api/tasks/{task_id}
```

**响应 (完整版本):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "评估任务",
    "type": "collection",
    "status": "completed",
    "progress": 100,
    "error": null,
    "connectionId": 1,
    "currentStep": "评估任务全部完成",
    "analysisResults": {
      "idle": true,
      "resource": true,
      "health": true
    },
    "createdAt": "2025-03-09T10:00:00Z",
    "startedAt": "2025-03-09T10:00:01Z",
    "completedAt": "2025-03-09T10:05:30Z",
    "platform": "vcenter",
    "connectionName": "生产环境 vCenter",
    "connectionHost": "192.168.1.100",
    "selectedVMCount": 2,
    "collectedVMCount": 15,
    "selectedVMs": [
      "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e"
    ],
    "config": {
      "platform": "vcenter",
      "connectionName": "生产环境 vCenter",
      "connectionHost": "192.168.1.100",
      "selectedVMs": [...],
      "selectedVMCount": 2
    }
  }
}
```

## 取消任务

```http
POST /api/tasks/{task_id}/cancel
```

## 删除任务

```http
DELETE /api/tasks/{task_id}
```

## 重试任务

```http
POST /api/tasks/{task_id}/retry
```

创建一个新任务，使用与失败任务相同的配置。

## 修改任务模式

```http
PUT /api/tasks/{task_id}/mode
Content-Type: application/json

{
  "mode": "aggressive"
}
```

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | string | 否 | 分析模式，默认 `saving` |

**响应:**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "评估任务",
    "mode": "aggressive",
    ...
  }
}
```

## 重新评估任务

```http
POST /api/tasks/{task_id}/re-evaluate
Content-Type: application/json

{
  "mode": "safe"
}
```

使用指定模式或任务保存的模式重新运行所有分析（闲置检测、资源分析、健康评分）。

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | string | 否 | 分析模式，默认使用任务当前保存的模式 |

**响应:**

```json
{
  "success": true,
  "message": "重新评估已启动"
}
```

分析将在后台异步执行，可以通过获取任务详情或日志查看进度。

## 获取任务日志

```http
GET /api/tasks/{task_id}/logs
```

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "level": "info",
        "message": "任务已创建，准备开始执行...",
        "timestamp": "2025-03-09T10:00:00Z"
      },
      {
        "id": 2,
        "level": "info",
        "message": "闲置检测完成，发现 3 台闲置VM",
        "timestamp": "2025-03-09T10:03:15Z"
      }
    ],
    "total": 15
  }
}
```

## 获取任务VM快照

```http
GET /api/tasks/{task_id}/vm-snapshots
```

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "vmName": "vm-001",
        "vmKey": "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "datacenter": "DC01",
        "cpuCount": 4,
        "memoryGb": 16.0,
        "powerState": "poweredOn",
        "hostIp": "192.168.1.100"
      }
    ],
    "total": 15
  }
}
```

## 获取任务VM列表

```http
GET /api/tasks/{task_id}/vms?limit=50&offset=0&keyword=
```

**查询参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | integer | 否 | 每页数量，默认 50，最大 200 |
| offset | integer | 否 | 偏移量，默认 0 |
| keyword | string | 否 | 搜索关键字（VM名称模糊匹配） |

**响应:**

```json
{
  "success": true,
  "data": {
    "vms": [
      {
        "id": 1,
        "name": "vm-001",
        "datacenter": "DC01",
        "vmKey": "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "cpuCount": 4,
        "memoryGb": 16.0,
        "powerState": "poweredOn",
        "connectionState": "connected",
        "hostIp": "192.168.1.100"
      }
    ],
    "total": 15
  }
}
```

---

# 资源管理 API

## 获取集群列表

```http
GET /api/resources/connections/{connection_id}/clusters
```

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "Cluster01",
        "datacenter": "DC01",
        "totalCpu": 512,
        "totalMemory": 2048,
        "numHosts": 3,
        "numVms": 50
      }
    ],
    "total": 1
  }
}
```

## 获取主机列表

```http
GET /api/resources/connections/{connection_id}/hosts
```

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "esxi-01.example.com",
        "datacenter": "DC01",
        "ipAddress": "192.168.1.100",
        "cpuCores": 64,
        "cpuMhz": 2400,
        "memoryGb": 256.0,
        "numVms": 18,
        "powerState": "poweredOn"
      }
    ],
    "total": 3
  }
}
```

## 获取虚拟机列表

```http
GET /api/resources/connections/{connection_id}/vms
```

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "vm-001",
        "datacenter": "DC01",
        "uuid": "5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "vmKey": "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "cpuCount": 4,
        "memoryGb": 16.0,
        "powerState": "poweredOn",
        "guestOs": "CentOS 7",
        "ipAddress": "192.168.1.10",
        "hostIp": "192.168.1.100"
      }
    ],
    "total": 50
  }
}
```

## 采集资源

```http
POST /api/resources/connections/{connection_id}/collect
```

启动资源采集任务，采集集群、主机、虚拟机的基础信息。

**响应:**

```json
{
  "success": true,
  "data": {
    "taskId": 1,
    "clusters": 1,
    "hosts": 3,
    "vms": 50
  }
}
```

## 获取可采集的VM列表

```http
GET /api/resources/connections/{connection_id}/vms/list
```

获取可用于性能指标采集的虚拟机列表（已开启的虚拟机）。

**响应:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "vmKey": "conn1:uuid:5028b6b5-7c7a-4f3e-8a1d-2f3e4b5c6d7e",
        "name": "vm-001",
        "datacenter": "DC01",
        "cpuCount": 4,
        "memoryGb": 16.0,
        "powerState": "poweredOn"
      }
    ],
    "total": 45
  }
}
```

---

# 分析 API

## 获取分析模式

```http
GET /api/analysis/modes
```

获取所有可用的分析模式配置。

**响应:**

```json
{
  "success": true,
  "data": {
    "safe": {
      "description": "安全模式 - 保守阈值，适合生产环境",
      "idle": {
        "days": 30,
        "cpuThreshold": 5.0,
        "memoryThreshold": 10.0,
        "minConfidence": 80.0
      },
      "resource": {
        "rightsize": {
          "days": 14,
          "cpuBufferPercent": 30.0,
          "memoryBufferPercent": 30.0,
          "highUsageThreshold": 85.0,
          "lowUsageThreshold": 15.0,
          "minConfidence": 70.0
        },
        "usagePattern": {
          "cvThreshold": 0.3,
          "peakValleyRatio": 2.0
        },
        "mismatch": {
          "cpuLowThreshold": 25.0,
          "cpuHighThreshold": 75.0,
          "memoryLowThreshold": 25.0,
          "memoryHighThreshold": 75.0
        }
      },
      "health": {
        "overcommitThreshold": 1.2,
        "hotspotThreshold": 5.0,
        "balanceThreshold": 0.5
      }
    },
    "saving": {
      "description": "节省模式 - 平衡阈值，默认推荐",
      "idle": {
        "days": 14,
        "cpuThreshold": 10.0,
        "memoryThreshold": 20.0,
        "minConfidence": 60.0
      },
      "resource": {
        "rightsize": {
          "days": 7,
          "cpuBufferPercent": 20.0,
          "memoryBufferPercent": 20.0,
          "highUsageThreshold": 90.0,
          "lowUsageThreshold": 30.0,
          "minConfidence": 60.0
        },
        "usagePattern": {
          "cvThreshold": 0.4,
          "peakValleyRatio": 2.5
        },
        "mismatch": {
          "cpuLowThreshold": 30.0,
          "cpuHighThreshold": 70.0,
          "memoryLowThreshold": 30.0,
          "memoryHighThreshold": 70.0
        }
      },
      "health": {
        "overcommitThreshold": 1.5,
        "hotspotThreshold": 7.0,
        "balanceThreshold": 0.6
      }
    },
    "aggressive": {
      "description": "激进模式 - 最大化优化机会",
      "idle": {
        "days": 7,
        "cpuThreshold": 15.0,
        "memoryThreshold": 25.0,
        "minConfidence": 50.0
      },
      "resource": {
        "rightsize": {
          "days": 7,
          "cpuBufferPercent": 10.0,
          "memoryBufferPercent": 10.0,
          "highUsageThreshold": 95.0,
          "lowUsageThreshold": 40.0,
          "minConfidence": 50.0
        },
        "usagePattern": {
          "cvThreshold": 0.5,
          "peakValleyRatio": 3.0
        },
        "mismatch": {
          "cpuLowThreshold": 40.0,
          "cpuHighThreshold": 60.0,
          "memoryLowThreshold": 40.0,
          "memoryHighThreshold": 60.0
        }
      },
      "health": {
        "overcommitThreshold": 2.0,
        "hotspotThreshold": 10.0,
        "balanceThreshold": 0.7
      }
    },
    "custom": {
      "description": "自定义模式 - 用户自定义配置",
      "idle": {},
      "resource": {
        "rightsize": {},
        "usagePattern": {},
        "mismatch": {}
      },
      "health": {}
    }
  }
}
```

**配置结构说明:**

| 一级字段 | 说明 |
|----------|------|
| idle | 闲置检测配置 |
| resource | 资源分析配置（包含三个子配置） |
| health | 健康评分配置 |

**resource 子配置:**

| 字段 | 说明 |
|------|------|
| rightsize | 资源配置优化（Right Size） |
| usagePattern | 使用模式分析（潮汐检测） |
| mismatch | 配置错配分析 |

## 获取特定模式

```http
GET /api/analysis/modes/{mode}
```

**模式值:** `safe`, `saving`, `aggressive`, `custom`

## 更新自定义模式

```http
PUT /api/analysis/modes/custom
Content-Type: application/json

{
  "analysisType": "idle",
  "config": {
    "days": 30,
    "cpuThreshold": 5.0,
    "memoryThreshold": 10.0,
    "minConfidence": 80.0
  },
  "taskId": 1
}
```

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| analysisType | string | 是 | 分析类型: `idle`, `resource`, `health` |
| config | object | 否 | 自定义配置（使用 camelCase 字段名） |
| taskId | integer | 否 | 任务ID（用于日志记录） |

**示例 - 更新闲置检测配置:**

```json
{
  "analysisType": "idle",
  "config": {
    "days": 30,
    "cpuThreshold": 5.0,
    "memoryThreshold": 10.0,
    "minConfidence": 80.0
  }
}
```

**示例 - 更新资源配置优化 (Right Size):**

```json
{
  "analysisType": "resource",
  "config": {
    "rightsize": {
      "days": 14,
      "cpuBufferPercent": 30.0,
      "memoryBufferPercent": 30.0
    }
  }
}
```

**示例 - 更新使用模式分析:**

```json
{
  "analysisType": "resource",
  "config": {
    "usagePattern": {
      "cvThreshold": 0.3,
      "peakValleyRatio": 2.0
    }
  }
}
```

**示例 - 更新健康评分:**

```json
{
  "analysisType": "health",
  "config": {
    "overcommitThreshold": 1.5,
    "hotspotThreshold": 7.0,
    "balanceThreshold": 0.6
  }
}
```

## 运行闲置检测分析

```http
POST /api/analysis/tasks/{task_id}/idle
Content-Type: application/json

{
  "mode": "saving"
}
```

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | string | 否 | 分析模式，默认 `saving` |
| config | object | 否 | 自定义配置（优先级高于mode） |

**响应:**

```json
{
  "success": true,
  "data": [
    {
      "vmName": "vm-001",
      "vmId": 1,
      "cluster": "Cluster01",
      "hostIp": "192.168.1.100",
      "isIdle": true,
      "idleType": "powered_off",
      "confidence": 95.0,
      "riskLevel": "high",
      "daysInactive": 45,
      "lastActivityTime": "2025-01-23T10:00:00Z",
      "downtimeDuration": 3888000,
      "recommendation": "建议关机或迁移此虚拟机以释放资源",
      "details": {}
    },
    {
      "vmName": "vm-002",
      "vmId": 2,
      "cluster": "Cluster01",
      "hostIp": "192.168.1.101",
      "isIdle": true,
      "idleType": "idle_powered_on",
      "confidence": 85.0,
      "riskLevel": "medium",
      "cpuCores": 4,
      "memoryGb": 16.0,
      "uptimeDuration": 2592000,
      "activityScore": 15,
      "cpuUsageP95": 5.2,
      "memoryUsageP95": 18.5,
      "diskIoP95": 2.1,
      "networkP95": 0.5,
      "dataQuality": "high",
      "recommendation": "虚拟机长期低负载运行，建议缩减配置或迁移到低配主机",
      "details": {}
    }
  ]
}
```

**闲置检测类型:**

| idleType | 说明 |
|----------|------|
| powered_off | 关机型 - 虚拟机已关机且长期未活动 |
| idle_powered_on | 开机闲置型 - 虚拟机开启但使用率极低 |
| low_activity | 低活动型 - 虚拟机有活动但明显不足 |

## 获取闲置检测结果

```http
GET /api/analysis/tasks/{task_id}/idle
```

## 运行资源分析

```http
POST /api/analysis/tasks/{task_id}/resource
Content-Type: application/json

{
  "mode": "saving"
}
```

资源分析包含三个子分析：Right Size（资源配置优化）、Usage Pattern（使用模式）、Mismatch（配置错配）。

**响应:**

```json
{
  "success": true,
  "data": {
    "rightSize": [
      {
        "vmName": "vm-001",
        "cluster": "Cluster01",
        "hostIp": "192.168.1.100",
        "currentCpu": 8,
        "suggestedCpu": 4,
        "currentMemory": 32.0,
        "suggestedMemory": 16.0,
        "cpuP95": 28.5,
        "cpuMax": 45.2,
        "cpuAvg": 22.1,
        "memoryP95": 45.2,
        "memoryMax": 52.1,
        "memoryAvg": 38.5,
        "adjustmentType": "shrink",
        "riskLevel": "low",
        "confidence": 85.0,
        "recommendation": "建议缩减CPU配置：8核→4核，内存配置：32GB→16GB",
        "details": {}
      }
    ],
    "usagePattern": [
      {
        "vmName": "vm-002",
        "datacenter": "DC01",
        "cluster": "Cluster01",
        "hostIp": "192.168.1.101",
        "optimizationType": "usage_pattern",
        "usagePattern": "tidal_day_night",
        "volatilityLevel": "high",
        "coefficientOfVariation": 0.65,
        "peakValleyRatio": 4.5,
        "tidalDetails": {
          "patternType": "day_night_tidal",
          "dayAvg": 65.2,
          "nightAvg": 14.5,
          "hourlyAvg": {
            "0": 12.5, "1": 10.2, ..., "14": 72.1, "15": 68.5
          }
        },
        "recommendation": "检测到潮汐模式：白天高负载、夜间低负载，建议配置调度策略",
        "details": {}
      }
    ],
    "mismatch": [
      {
        "vmName": "vm-003",
        "datacenter": "DC01",
        "cluster": "Cluster01",
        "hostIp": "192.168.1.102",
        "hasMismatch": true,
        "mismatchType": "cpu_high_memory_low",
        "cpuUtilization": 85.5,
        "memoryUtilization": 15.2,
        "currentCpu": 4,
        "currentMemory": 32.0,
        "recommendation": "CPU使用率高但内存使用率低，存在配置错配。建议增加CPU或减少内存",
        "details": {}
      }
    ],
    "summary": {
      "rightSizeCount": 12,
      "usagePatternCount": 8,
      "mismatchCount": 5,
      "totalVmsAnalyzed": 50
    }
  }
}
```

**调整类型 (adjustmentType):**

| 类型 | 说明 |
|------|------|
| shrink | 缩减配置 - 资源过剩 |
| expand | 扩展配置 - 资源不足 |
| no_change | 无需调整 - 配置合理 |

**使用模式 (usagePattern):**

| 模式 | 说明 |
|------|------|
| stable | 稳定型 - 负载平稳 |
| tidal_day_night | 日夜潮汐型 - 白天高夜间低 |
| tidal_work_week | 工作日潮汐型 - 工作日高周末低 |
| volatile | 不稳定型 - 负载波动大且无规律 |

**配置错配类型 (mismatchType):**

| 类型 | 说明 |
|------|------|
| cpu_high_memory_low | CPU高内存低 |
| cpu_low_memory_high | CPU低内存高 |
| both_high | CPU和内存都高 |
| both_low | CPU和内存都低 |

## 获取资源分析结果

```http
GET /api/analysis/tasks/{task_id}/resource
```

## 运行健康评分分析

```http
POST /api/analysis/tasks/{task_id}/health
Content-Type: application/json

{
  "mode": "saving"
}
```

**响应:**

```json
{
  "success": true,
  "data": {
    "overallScore": 78.5,
    "grade": "good",
    "balanceScore": 72.0,
    "overcommitScore": 85.0,
    "hotspotScore": 78.5,
    "clusterCount": 1,
    "hostCount": 3,
    "vmCount": 50,
    "subScores": {
      "balance": 72.0,
      "overcommit": 85.0,
      "hotspot": 78.5
    },
    "overcommitResults": [
      {
        "clusterName": "Cluster01",
        "physicalCpuCores": 192.0,
        "physicalMemoryGb": 768.0,
        "allocatedCpu": 400,
        "allocatedMemoryGb": 1600.0,
        "cpuOvercommit": 2.08,
        "memoryOvercommit": 2.08,
        "cpuRisk": "medium",
        "memoryRisk": "medium"
      }
    ],
    "balanceResults": [
      {
        "clusterName": "Cluster01",
        "hostCount": 3,
        "vmCounts": [15, 18, 17],
        "meanVmCount": 16.67,
        "stdDev": 1.25,
        "coefficientOfVariation": 0.075,
        "balanceLevel": "excellent",
        "balanceScore": 92.0
      }
    ],
    "hotspotHosts": [
      {
        "hostName": "esxi-02.example.com",
        "ipAddress": "192.168.1.101",
        "vmCount": 18,
        "cpuCores": 64,
        "memoryGb": 256.0,
        "vmDensity": 0.28,
        "riskLevel": "low",
        "recommendation": "VM密度适中，当前配置合理"
      }
    ],
    "avgVmDensity": 0.26,
    "findings": [
      {
        "severity": "warning",
        "category": "overcommit",
        "cluster": "Cluster01",
        "description": "内存超配倍数略高，建议监控",
        "details": {}
      }
    ],
    "recommendations": [
      "建议关注Cluster01的内存超配情况",
      "当前VM负载分布均衡，无需调整"
    ]
  }
}
```

**评分等级 (grade):**

| 等级 | 分数范围 |
|------|----------|
| excellent | 90-100 |
| good | 75-89 |
| fair | 60-74 |
| poor | 40-59 |
| critical | 0-39 |
| no_data | 无数据 |

## 获取健康评分结果

```http
GET /api/analysis/tasks/{task_id}/health
```

---

# 报告 API

## 生成报告

```http
POST /api/reports/tasks/{task_id}/reports
Content-Type: application/json

{
  "format": "xlsx",
  "includeRawData": false
}
```

**请求参数:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| format | string | 是 | 报告格式: `xlsx` (Excel) 或 `pdf` |
| includeRawData | boolean | 否 | 是否包含原始数据，默认 false |

**响应:**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "taskId": 1,
    "format": "xlsx",
    "filePath": "/path/to/report.xlsx",
    "fileSize": 245800,
    "createdAt": "2025-03-09T10:10:00Z"
  }
}
```

## 获取任务报告列表

```http
GET /api/reports/tasks/{task_id}/reports
```

**响应:**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "taskId": 1,
      "format": "xlsx",
      "filePath": "/path/to/report.xlsx",
      "fileSize": 245800,
      "createdAt": "2025-03-09T10:10:00Z"
    },
    {
      "id": 2,
      "taskId": 1,
      "format": "pdf",
      "filePath": "/path/to/report.pdf",
      "fileSize": 512000,
      "createdAt": "2025-03-09T10:12:00Z"
    }
  ]
}
```

## 获取报告详情

```http
GET /api/reports/{report_id}
```

## 下载报告

```http
GET /api/reports/{report_id}/download
```

返回报告文件下载。

## 删除报告

```http
DELETE /api/reports/{report_id}
```

---

# 系统 API

## 健康检查

```http
GET /api/system/health
```

**响应:**

```json
{
  "status": "healthy",
  "version": "0.0.3"
}
```

## 版本信息

```http
GET /api/system/version
```

**响应:**

```json
{
  "version": "0.0.3",
  "name": "JustFit"
}
```

---

# WebSocket

任务进度推送暂未实现，当前使用 HTTP 轮询方式获取任务进度。

---

# 错误代码

| 代码 | 说明 |
|------|------|
| `CONNECTION_NOT_FOUND` | 连接不存在 |
| `INVALID_CREDENTIALS` | 连接凭据无效 |
| `CONNECTION_FAILED` | 连接失败 |
| `FETCH_VMS_FAILED` | 获取虚拟机列表失败 |
| `TASK_NOT_FOUND` | 任务不存在 |
| `INVALID_MODE` | 无效的分析模式 |
| `ANALYSIS_ERROR` | 分析执行失败 |
| `REPORT_NOT_FOUND` | 报告不存在 |
| `FILE_NOT_FOUND` | 文件不存在 |
| `INTERNAL_ERROR` | 服务器内部错误 |

---

# 数据字段命名规范

## 后端 → 前端 (JSON 响应)

所有 API 响应字段使用 **camelCase** 命名：

```json
{
  "connectionId": 1,
  "selectedVMs": [],
  "collectedVMCount": 15,
  "overallScore": 78.5,
  "balanceScore": 72.0
}
```

## 前端开发规则

1. **直接使用后端字段**：前端不得创建字段映射或转换层
2. **字段不匹配时**：检查后端 API 返回的字段名，确保前端直接使用
3. **禁止适配层**：不要在前端做字段兼容处理

```typescript
// ✅ 正确
const score = result.overallScore

// ❌ 错误
const score = result.score  // 后端没有这个字段
```
