# JustFit API 端到端测试文档

## 启动后端

```bash
# 方式一：手动启动后端
cd backend
python -m uvicorn app.main:app --reload --port 22631

# 方式二：使用开发脚本（同时启动前后端）
./scripts/dev/dev-linux.sh    # Linux/macOS
./scripts/dev/dev-windows.sh  # Windows Git Bash

# 方式三：使用 Makefile
make dev

# 启动成功后，API 服务地址为：
# http://localhost:22631
#
# API 文档地址：
# http://localhost:22631/docs
```

## 测试环境配置

详见项目根目录 .env 配置文件

## 测试流程概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整测试流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1] 创建连接           →   [2] 验证连接                        │
│       ↓                                                      │
│  [3] 获取连接列表       →   [4] 创建采集任务                    │
│       ↓                                                      │
│  [5] 等待采集完成       →   [6] 获取采集结果                    │
│       ↓                                                      │
│  [7] 闲置检测分析       →   [8] 资源分析                       │
│       ↓                                                      │
│  [9] 健康评分分析       →   [10] 生成报告                      │
│       ↓                                                      │
│  [11] 删除连接                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 测试用例

## 用例 1：创建连接

### 描述
创建一个新的平台连接配置

### API 端点
```
POST /api/connections/
```

### vCenter 请求示例

**请求头**
```
Content-Type: application/json
```

**请求体**
```json
{
  "name": "测试_vCenter_001",
  "platform": "vcenter",
  "host": "10.103.116.116",
  "port": 443,
  "username": "administrator@vsphere.local",
  "password": "Admin@123.",
  "insecure": true
}
```

### H3C UIS 请求示例

**请求体**
```json
{
  "name": "测试_UIS_001",
  "platform": "uis",
  "host": "<UIS服务器IP>",
  "port": 8089,
  "username": "<用户名>",
  "password": "<密码>",
  "insecure": true
}
```

### 预期响应

**成功响应** (201)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "测试_vCenter_001",
    "platform": "vcenter",
    "host": "10.103.116.116",
    "port": 443,
    "username": "administrator@vsphere.local",
    "status": "disconnected",
    "createdAt": "2026-03-09T10:00:00Z"
  },
  "message": "连接创建成功"
}
```

**失败响应** (400)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "缺少必填字段: host"
  }
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 201
- [ ] `success` 为 `true`
- [ ] `data.id` 为正整数
- [ ] `data.platform` 与请求一致
- [ ] `data.status` 为 `"disconnected"` 或 `"connected"`

---

## 用例 2：验证连接

### 描述
测试已保存的连接配置是否能成功连接到平台

### API 端点
```
POST /api/connections/{connection_id}/test
```

### 路径参数
| 参数 | 类型 | 说明 |
|------|------|------|
| connection_id | integer | 连接 ID（用例 1 返回的 id）|

### 预期响应

**成功响应** (200)
```json
{
  "success": true,
  "data": {
    "connected": true,
    "version": "7.0.3",
    "datacenterCount": 1
  },
  "message": "连接成功"
}
```

**失败响应** (401)
```json
{
  "success": false,
  "error": {
    "code": "AUTH_FAILED",
    "message": "认证失败: 用户名或密码错误"
  }
}
```

**超时响应** (408)
```json
{
  "success": false,
  "error": {
    "code": "TIMEOUT",
    "message": "连接超时，请检查网络和服务器地址"
  }
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data.connected` 为 `true`
- [ ] 能获取到平台版本信息

---

## 用例 3：获取连接列表

### 描述
获取所有已保存的连接配置

### API 端点
```
GET /api/connections/
```

### 预期响应

**成功响应** (200)
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "测试_vCenter_001",
      "platform": "vcenter",
      "host": "10.103.116.116",
      "status": "connected",
      "lastSync": "2026-03-09T10:05:00Z"
    }
  ],
  "message": "获取成功"
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data` 为数组，包含刚创建的连接
- [ ] 每个连接包含 `id`, `name`, `platform`, `status` 字段

---

## 用例 4：获取连接详情

### 描述
获取指定连接的详细信息

### API 端点
```
GET /api/connections/{connection_id}
```

### 路径参数
| 参数 | 类型 | 说明 |
|------|------|------|
| connection_id | integer | 连接 ID |

### 预期响应

**成功响应** (200)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "测试_vCenter_001",
    "platform": "vcenter",
    "host": "10.103.116.116",
    "port": 443,
    "username": "administrator@vsphere.local",
    "status": "connected",
    "lastSync": "2026-03-09T10:05:00Z",
    "createdAt": "2026-03-09T10:00:00Z"
  }
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] 返回完整的连接信息

---

## 用例 5：创建采集任务

### 描述
创建资源采集任务，采集集群、主机、虚拟机信息

### API 端点
```
POST /api/tasks/
```

### 请求体
```json
{
  "name": "采集任务_001",
  "type": "collection",
  "connectionId": 1,
  "config": {
    "collectClusters": true,
    "collectHosts": true,
    "collectVMs": true,
    "collectMetrics": true,
    "metricDays": 7
  }
}
```

### 字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 任务名称 |
| type | string | 固定值 `"collection"` |
| connectionId | integer | 连接 ID（用例 1 返回的 id）|
| config.collectClusters | boolean | 是否采集集群 |
| config.collectHosts | boolean | 是否采集主机 |
| config.collectVMs | boolean | 是否采集虚拟机 |
| config.collectMetrics | boolean | 是否采集性能指标 |
| config.metricDays | integer | 采集最近 N 天的指标 |

### 预期响应

**成功响应** (201)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "采集任务_001",
    "type": "collection",
    "status": "pending",
    "progress": 0,
    "connectionId": 1,
    "createdAt": "2026-03-09T10:10:00Z"
  },
  "message": "任务创建成功"
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 201
- [ ] `success` 为 `true`
- [ ] 返回任务 ID (`data.id`)
- [ ] `data.status` 为 `"pending"` 或 `"running"`

---

## 用例 6：等待采集完成

### 描述
轮询任务状态，等待采集任务完成

### API 端点
```
GET /api/tasks/{task_id}
```

### 轮询逻辑
```
每 2 秒轮询一次，最多等待 300 秒（5分钟）
```

### 预期响应 - 执行中

**响应** (200)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "采集任务_001",
    "type": "collection",
    "status": "running",
    "progress": 45,
    "startedAt": "2026-03-09T10:10:05Z"
  }
}
```

### 预期响应 - 完成

**响应** (200)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "采集任务_001",
    "type": "collection",
    "status": "completed",
    "progress": 100,
    "startedAt": "2026-03-09T10:10:05Z",
    "completedAt": "2026-03-09T10:12:30Z",
    "result": "{\"clusterCount\":2,\"hostCount\":8,\"vmCount\":150}"
  }
}
```

### 状态值说明
| 状态 | 说明 |
|------|------|
| pending | 等待执行 |
| running | 执行中 |
| completed | 执行完成 |
| failed | 执行失败 |

### 验收条件
- [ ] 最终 `status` 为 `"completed"`
- [ ] `progress` 为 `100`
- [ ] `result` 包含采集统计数据
- [ ] 解析 `result` 可获得 `clusterCount`, `hostCount`, `vmCount`

---

## 用例 7：获取采集结果

### 描述
获取采集到的集群、主机、虚拟机列表

### API 端点

**获取集群列表**
```
GET /api/connections/{connection_id}/clusters
```

**获取主机列表**
```
GET /api/connections/{connection_id}/hosts
```

**获取虚拟机列表**
```
GET /api/connections/{connection_id}/vms
```

### 预期响应 - 集群列表

**响应** (200)
```json
{
  "success": true,
  "data": [
    {
      "name": "Cluster-01",
      "datacenter": "Datacenter-01",
      "totalCpu": 384000,
      "totalMemory": 2147483648000,
      "numHosts": 4,
      "numVMs": 85
    }
  ]
}
```

### 预期响应 - 主机列表

**响应** (200)
```json
{
  "success": true,
  "data": [
    {
      "name": "esxi-01.example.com",
      "datacenter": "Datacenter-01",
      "ipAddress": "10.0.0.101",
      "cpuCores": 24,
      "cpuMhz": 2400,
      "memoryBytes": 137438953472,
      "numVMs": 22,
      "powerState": "poweredOn",
      "overallStatus": "green"
    }
  ]
}
```

### 预期响应 - 虚拟机列表

**响应** (200)
```json
{
  "success": true,
  "data": [
    {
      "name": "vm-web-01",
      "datacenter": "Datacenter-01",
      "cpuCount": 2,
      "memoryBytes": 4294967296,
      "powerState": "poweredOn",
      "guestOs": "CentOS Linux 7",
      "ipAddress": "10.0.1.50",
      "hostIp": "10.0.0.101",
      "connectionState": "connected",
      "overallStatus": "green"
    }
  ]
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data` 为数组，至少包含一条数据
- [ ] 数据字段完整，无空值

---

## 用例 8：闲置检测分析

### 描述
检测闲置虚拟机（长期关机、开机闲置、低活跃度）

### API 端点
```
POST /api/analysis/tasks/{task_id}/idle
```

### 路径参数
| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 采集任务 ID |

### 请求体
```json
{
  "mode": "saving"
}
```

### 请求参数说明
| 参数 | 类型 | 可选值 | 说明 |
|------|------|--------|------|
| mode | string | safe / saving / aggressive | 分析模式 |

### 预期响应

**响应** (200)
```json
{
  "success": true,
  "data": [
    {
      "vmName": "vm-test-01",
      "cluster": "Cluster-01",
      "hostIp": "10.0.0.101",
      "cpuCores": 2,
      "memoryGb": 4.0,
      "idleType": "powered_off",
      "confidence": 95,
      "riskLevel": "high",
      "recommendation": "该虚拟机已关机超过 30 天，建议删除或归档"
    },
    {
      "vmName": "vm-idle-01",
      "cluster": "Cluster-01",
      "hostIp": "10.0.0.102",
      "cpuCores": 4,
      "memoryGb": 8.0,
      "idleType": "idle_powered_on",
      "confidence": 88,
      "riskLevel": "medium",
      "recommendation": "该虚拟机 CPU 和内存使用率长期低于 10%，建议缩减配置或关机"
    }
  ],
  "message": "闲置检测完成，发现 2 台闲置VM"
}
```

### 闲置类型说明
| idleType | 说明 |
|----------|------|
| powered_off | 长期关机（超过阈值天数）|
| idle_powered_on | 开机但资源使用率极低 |
| low_activity | 活跃度低于阈值 |

### 风险等级说明
| riskLevel | 说明 |
|-----------|------|
| low | 低风险 |
| medium | 中等风险 |
| high | 高风险 |
| critical | 严重风险 |

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data` 为数组（可能为空）
- [ ] 每条记录包含 `vmName`, `idleType`, `confidence`, `riskLevel`

---

## 用例 9：资源分析

### 描述
综合资源分析（Right Size + 使用模式 + 配置错配）

### API 端点
```
POST /api/analysis/tasks/{task_id}/resource
```

### 请求体
```json
{
  "mode": "saving"
}
```

### 预期响应

**响应** (200)
```json
{
  "success": true,
  "data": {
    "rightSize": [
      {
        "vmName": "vm-oversize-01",
        "cluster": "Cluster-01",
        "currentConfig": {
          "cpu": 8,
          "memory": 16384
        },
        "recommendedConfig": {
          "cpu": 4,
          "memory": 8192
        },
        "wasteRatio": 0.5,
        "recommendation": "建议缩减 CPU 从 8 到 4，内存从 16GB 到 8GB"
      }
    ],
    "usagePattern": [
      {
        "vmName": "vm-tidal-01",
        "cluster": "Cluster-01",
        "usagePattern": "tidal",
        "volatilityLevel": "high",
        "coefficientOfVariation": 0.55,
        "peakValleyRatio": 3.2,
        "tidalDetails": {
          "patternType": "tidal",
          "dayAvg": 75.5,
          "nightAvg": 15.2,
          "hourlyAvg": {
            "00:00": 10,
            "09:00": 85,
            "14:00": 80
          }
        },
        "recommendation": "检测到潮汐模式：白天高负载，夜间低负载，建议动态调度"
      }
    ],
    "mismatch": [
      {
        "vmName": "vm-mismatch-01",
        "cluster": "Cluster-01",
        "mismatchType": "cpu_rich_memory_poor",
        "cpuUtilization": 15.0,
        "memoryUtilization": 85.0,
        "recommendation": "CPU富裕但内存紧张，建议增加内存配置或减少CPU配置"
      }
    ],
    "summary": {
      "rightSizeCount": 5,
      "usagePatternCount": 3,
      "mismatchCount": 2,
      "totalVmsAnalyzed": 50
    }
  }
}
```

### 使用模式类型说明
| usagePattern | 说明 |
|--------------|------|
| stable | 稳定型，负载波动小 |
| burst | 突发型，偶发高负载 |
| tidal | 潮汐型，周期性波动 |

### 配置错配类型说明
| mismatchType | 说明 |
|--------------|------|
| cpu_rich_memory_poor | CPU富裕内存紧张 |
| cpu_poor_memory_rich | CPU紧张内存富裕 |
| both_underutilized | 双重过剩 |
| both_overutilized | 双重紧张 |

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data` 包含 `rightSize`, `usagePattern`, `mismatch` 三个数组
- [ ] `data.summary` 包含统计数量
- [ ] 各数组记录字段完整

---

## 用例 10：健康评分分析

### 描述
对整个平台进行健康度评分

### API 端点
```
POST /api/analysis/tasks/{task_id}/health
```

### 请求体
```json
{
  "mode": "saving"
}
```

### 预期响应

**响应** (200)
```json
{
  "success": true,
  "data": {
    "overallScore": 78.5,
    "grade": "good",
    "balanceScore": 75.0,
    "overcommitScore": 82.0,
    "hotspotScore": 80.0,
    "clusterCount": 2,
    "hostCount": 8,
    "vmCount": 150,
    "findings": [
      {
        "type": "hotspot",
        "severity": "high",
        "title": "主机负载不均",
        "description": "主机 esxi-03 负载过高 (85%)，而其他主机负载较低，存在热点风险"
      },
      {
        "type": "overcommit",
        "severity": "medium",
        "title": "资源超配偏高",
        "description": "Cluster-01 内存超配率达 1.8，建议关注"
      }
    ]
  }
}
```

### 等级说明
| grade | 分数范围 | 说明 |
|-------|----------|------|
| excellent | 90-100 | 优秀 |
| good | 75-89 | 良好 |
| fair | 60-74 | 一般 |
| poor | 40-59 | 较差 |
| critical | 0-39 | 危急 |

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `overallScore` 为 0-100 之间的数值
- [ ] `grade` 为有效等级值
- [ ] `findings` 数组包含问题列表（可能为空）

---

## 用例 11：生成 Excel 报告

### 描述
生成 Excel 格式的评估报告

### API 端点
```
POST /api/tasks/{task_id}/reports
```

### 请求体
```json
{
  "format": "excel"
}
```

### 预期响应

**响应** (200)
```json
{
  "success": true,
  "data": {
    "id": 1,
    "format": "excel",
    "status": "completed",
    "filePath": "/home/user/.local/share/justfit/reports/task_1_report_20260309.xlsx",
    "fileSize": 52480,
    "generatedAt": "2026-03-09T10:30:00Z"
  },
  "message": "Excel 报告生成成功"
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data.filePath` 为有效路径
- [ ] 文件实际存在于文件系统
- [ ] 文件大小大于 0

---

## 用例 12：生成 PDF 报告

### 描述
生成 PDF 格式的评估报告

### API 端点
```
POST /api/tasks/{task_id}/reports
```

### 请求体
```json
{
  "format": "pdf"
}
```

### 预期响应

**响应** (200)
```json
{
  "success": true,
  "data": {
    "id": 2,
    "format": "pdf",
    "status": "completed",
    "filePath": "/home/user/.local/share/justfit/reports/task_1_report_20260309.pdf",
    "fileSize": 102400,
    "generatedAt": "2026-03-09T10:31:00Z"
  },
  "message": "PDF 报告生成成功"
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] `data.filePath` 为有效路径
- [ ] 文件实际存在于文件系统
- [ ] PDF 文件可正常打开

---

## 用例 13：删除连接

### 描述
删除测试创建的连接

### API 端点
```
DELETE /api/connections/{connection_id}
```

### 预期响应

**响应** (200)
```json
{
  "success": true,
  "message": "连接删除成功"
}
```

### 验收条件
- [ ] 返回 HTTP 状态码 200
- [ ] `success` 为 `true`
- [ ] 再次获取连接列表，该连接不存在

---

## 附录 A：通用错误响应格式

所有 API 在失败时返回统一格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述信息"
  }
}
```

### 常见错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| UNAUTHORIZED | 401 | 未授权 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| TIMEOUT | 408 | 请求超时 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 附录 B：测试检查表

### vCenter 平台测试

| 用例 | 测试项 | 状态 | 备注 |
|------|--------|------|------|
| 1 | 创建连接 | ☐ | |
| 2 | 验证连接 | ☐ | |
| 3 | 获取连接列表 | ☐ | |
| 4 | 获取连接详情 | ☐ | |
| 5 | 创建采集任务 | ☐ | |
| 6 | 等待采集完成 | ☐ | |
| 7 | 获取采集结果 | ☐ | |
| 8 | 闲置检测分析 | ☐ | |
| 9 | 资源分析 | ☐ | |
| 10 | 健康评分分析 | ☐ | |
| 11 | 生成 Excel 报告 | ☐ | |
| 12 | 生成 PDF 报告 | ☐ | |
| 13 | 删除连接 | ☐ | |

### H3C UIS 平台测试

| 用例 | 测试项 | 状态 | 备注 |
|------|--------|------|------|
| 1 | 创建连接 | ☐ | |
| 2 | 验证连接 | ☐ | |
| 3 | 获取连接列表 | ☐ | |
| 4 | 获取连接详情 | ☐ | |
| 5 | 创建采集任务 | ☐ | |
| 6 | 等待采集完成 | ☐ | |
| 7 | 获取采集结果 | ☐ | |
| 8 | 闲置检测分析 | ☐ | |
| 9 | 资源分析 | ☐ | |
| 10 | 健康评分分析 | ☐ | |
| 11 | 生成 Excel 报告 | ☐ | |
| 12 | 生成 PDF 报告 | ☐ | |
| 13 | 删除连接 | ☐ | |

---

## 附录 C：测试工具推荐

### cURL 示例

```bash
# 创建连接
curl -X POST http://localhost:22631/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试_vCenter",
    "platform": "vcenter",
    "host": "10.103.116.116",
    "port": 443,
    "username": "administrator@vsphere.local",
    "password": "Admin@123.",
    "insecure": true
  }'

# 验证连接
curl -X POST http://localhost:22631/api/connections/1/test

# 获取连接列表
curl http://localhost:22631/api/connections/
```

### Postman 导入

可使用上述 API 定义创建 Postman Collection，快速进行测试。

---

## 文档变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0 | 2026-03-09 | 初始版本 | Claude |
