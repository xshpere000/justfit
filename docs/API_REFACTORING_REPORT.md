# JustFit API 重构报告

## 概述

本次重构将原有的三个独立分析 API（zombie、rightsize、tidal）整合为三个新的分析 API（idle、resource、health），简化了 API 结构，提高了可维护性。

**重构日期**: 2026-03-09
**版本**: v0.0.3

---

## 1. 已删除的 API

### 1.1 闲置检测 API (Zombie)

| 项目 | 详情 |
|------|------|
| **端点** | `POST /api/analysis/zombie` |
| **分析器** | `ZombieAnalyzer` |
| **文件** | `app/analyzers/zombie.py` (已删除) |
| **原因** | 功能合并到新的 `idle` 分析 |

### 1.2 潮汐模式 API (Tidal)

| 项目 | 详情 |
|------|------|
| **端点** | `POST /api/analysis/tidal` |
| **分析器** | `TidalAnalyzer` |
| **文件** | `app/analyzers/tidal.py` (已删除) |
| **原因** | 功能合并到新的 `resource` 分析 |

### 1.3 独立资源配置优化 API

| 项目 | 详情 |
|------|------|
| **端点** | `POST /api/analysis/rightsize` |
| **分析器** | `RightSizeAnalyzer` (保留为内部组件) |
| **变化** | 不再作为独立端点，合并到 `resource` 分析 |

---

## 2. 新的 API

### 2.1 闲置检测 API

```http
POST /api/analysis/tasks/{task_id}/idle
```

**描述**: 检测闲置虚拟机（长期关机、开机闲置、低活跃度）

**请求参数**:
```json
{
  "mode": "saving",           // safe | saving | aggressive | custom
  "taskId": 123
}
```

**响应结构**:
```json
{
  "success": true,
  "data": [
    {
      "vmName": "vm-001",
      "cluster": "cluster-01",
      "hostIp": "10.0.0.1",
      "cpuCores": 2,
      "memoryGb": 4.0,
      "idleType": "powered_off",      // powered_off | idle_powered_on | low_activity
      "confidence": 95,
      "riskLevel": "high",            // low | medium | high | critical
      "recommendation": "建议删除或归档此闲置VM"
    }
  ],
  "message": "闲置检测完成，发现 5 台闲置VM"
}
```

**闲置类型说明**:
| 类型 | 描述 |
|------|------|
| `powered_off` | 长期关机（超过阈值天数） |
| `idle_powered_on` | 开机但资源使用率极低 |
| `low_activity` | 活跃度低于阈值 |

---

### 2.2 资源分析 API

```http
POST /api/analysis/tasks/{task_id}/resource
```

**描述**: 综合资源分析（Right Size + 使用模式 + 配置错配）

**请求参数**:
```json
{
  "mode": "saving",
  "taskId": 123,
  "config": {
    "right_size": {
      "days": 7,
      "cpu_buffer_percent": 20.0,
      "memory_buffer_percent": 20.0
    },
    "usage_pattern": {
      "cv_threshold": 0.4,
      "peak_valley_ratio": 2.5
    },
    "mismatch": {
      "cpu_low_threshold": 30.0,
      "cpu_high_threshold": 70.0
    }
  }
}
```

**响应结构**:
```json
{
  "success": true,
  "data": {
    "rightSize": [
      {
        "vmName": "vm-001",
        "cluster": "cluster-01",
        "currentConfig": {
          "cpu": 4,
          "memory": 8192
        },
        "recommendedConfig": {
          "cpu": 2,
          "memory": 4096
        },
        "wasteRatio": 0.5,
        "recommendation": "建议缩减 CPU 和内存配置"
      }
    ],
    "usagePattern": [
      {
        "vmName": "vm-002",
        "cluster": "cluster-01",
        "usagePattern": "stable",          // stable | burst | tidal
        "volatilityLevel": "low",
        "coefficientOfVariation": 0.15,
        "peakValleyRatio": 1.5,
        "recommendation": "使用模式稳定"
      }
    ],
    "mismatch": [
      {
        "vmName": "vm-003",
        "cluster": "cluster-01",
        "mismatchType": "cpu_rich_memory_poor",
        "cpuUtilization": 15.0,
        "memoryUtilization": 85.0,
        "recommendation": "CPU富裕但内存紧张，建议调整配置"
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

---

### 2.3 健康评分 API

```http
POST /api/analysis/tasks/{task_id}/health
```

**描述**: 平台健康度评分（资源均衡、超配风险、热点分布）

**请求参数**:
```json
{
  "mode": "saving",
  "taskId": 123
}
```

**响应结构**:
```json
{
  "success": true,
  "data": {
    "overallScore": 78.5,
    "grade": "good",                    // excellent | good | fair | poor | critical
    "balanceScore": 75.0,
    "overcommitScore": 82.0,
    "hotspotScore": 80.0,
    "clusterCount": 3,
    "hostCount": 12,
    "vmCount": 150,
    "findings": [
      {
        "type": "hotspot",
        "severity": "high",
        "title": "主机负载不均",
        "description": "部分主机负载过高，存在热点风险"
      }
    ]
  }
}
```

---

## 3. 模式配置 API

### 获取所有模式

```http
GET /api/analysis/modes
```

**响应**:
```json
{
  "success": true,
  "data": {
    "safe": {
      "description": "安全模式 - 保守阈值，适合生产环境",
      "idle": {...},
      "resource": {...},
      "health": {...}
    },
    "saving": {...},
    "aggressive": {...},
    "custom": {...}
  }
}
```

### 更新自定义模式

```http
PUT /api/analysis/modes/custom
```

**请求**:
```json
{
  "analysisType": "idle",    // idle | resource | health
  "config": {
    "days": 14,
    "cpu_threshold": 10.0,
    "memory_threshold": 20.0
  }
}
```

---

## 4. 数据库模型变化

### TaskAnalysisJob.job_type

| 旧值 | 新值 |
|------|------|
| `zombie` | `idle` |
| `rightsize` | (合并到 `resource`) |
| `tidal` | (合并到 `resource`) |
| `health` | `health` (不变) |

### AnalysisFinding.job_type

| 旧值 | 新值 |
|------|------|
| `zombie` | `idle` |
| `rightsize` | `rightsize` (作为 resource 的子类型) |
| `tidal` | `usage_pattern` (作为 resource 的子类型) |
| (无) | `mismatch` (新增) |
| `health` | `health` (不变) |

---

## 5. 评估模式配置

### idle（闲置检测）

```python
{
    "days": 14,                    # 检测天数
    "cpu_threshold": 10.0,         # CPU使用率阈值(%)
    "memory_threshold": 20.0,      # 内存使用率阈值(%)
    "min_confidence": 60.0         # 最小置信度
}
```

### resource（资源分析）

```python
{
    "rightsize": {
        "days": 7,
        "cpu_buffer_percent": 20.0,
        "memory_buffer_percent": 20.0,
        "min_confidence": 60.0
    },
    "usage_pattern": {
        "cv_threshold": 0.4,       # 变异系数阈值
        "peak_valley_ratio": 2.5    # 峰谷比阈值
    },
    "mismatch": {
        "cpu_low_threshold": 30.0,  # CPU低使用率阈值
        "cpu_high_threshold": 70.0, # CPU高使用率阈值
        "memory_low_threshold": 30.0,
        "memory_high_threshold": 70.0
    }
}
```

### health（健康评分）

```python
{
    "overcommit_threshold": 1.5,   # 超配阈值
    "hotspot_threshold": 7.0,      # 热点阈值
    "balance_threshold": 0.6       # 均衡阈值
}
```

---

## 6. 迁移指南

### 前端更新

**旧代码**:
```typescript
// 调用僵尸VM分析
const response = await api.post(`/api/analysis/zombie`, {
  taskId: task.id,
  mode: 'saving'
});
```

**新代码**:
```typescript
// 调用闲置检测
const response = await api.post(`/api/analysis/tasks/${task.id}/idle`, {
  mode: 'saving'
});

// 响应数据结构变化
const findings = response.data.data;
// findings[0].idleType 替代 findings[0].zombieType
// findings[0].riskLevel 新增字段
```

**Right Size 迁移**:
```typescript
// 旧: POST /api/analysis/rightsize
// 新: POST /api/analysis/tasks/{id}/resource

// 响应变化
const result = response.data.data;
// result.rightSize[] 替代原 result[]
// 新增 result.usagePattern[]
// 新增 result.mismatch[]
```

**Tidal 迁移**:
```typescript
// 旧: POST /api/analysis/tidal
// 新: POST /api/analysis/tasks/{id}/resource

// 潮汐模式现在是 usagePattern 的一部分
const patterns = result.usagePattern.filter(p => p.usagePattern === 'tidal');
```

---

## 7. 代码变更总结

### 删除的文件
- `app/analyzers/zombie.py`
- `app/analyzers/tidal.py`

### 新增的分析器
- `app/analyzers/idle_detector.py` - IdleDetector
- `app/analyzers/resource_analyzer.py` - ResourceAnalyzer (整合了 rightsize 和 usage_pattern)

### 保留的内部组件
- `app/analyzers/rightsize.py` - RightSizeAnalyzer (被 ResourceAnalyzer 内部调用)
- `app/analyzers/health.py` - HealthAnalyzer

### 更新的文件
- `app/analyzers/__init__.py` - 更新导出
- `app/analyzers/modes.py` - 更新模式配置结构
- `app/routers/analysis.py` - 更新 API 端点
- `app/services/analysis.py` - 更新服务方法
- `app/schemas/analysis.py` - 更新 schema
- `app/models/finding.py` - 更新注释
- `app/models/task.py` - 更新注释
- `app/report/builder.py` - 更新报告构建
- `app/report/excel.py` - 更新 Excel 报告
- `app/report/pdf.py` - 更新 PDF 报告

---

## 8. 测试验证

所有分析器相关测试通过：
- 单元测试: 44 个通过
- 集成测试: 57 个通过
- 总计: **101 个测试通过**

测试覆盖：
- IdleDetector (闲置检测)
- ResourceAnalyzer (资源分析)
- HealthAnalyzer (健康评分)
- API 端点验证
- 模式配置管理

---

## 9. 后续工作

1. **需要删除旧数据重新测试**: 由于 API 结构变化，建议删除历史数据重新运行分析
2. **前端适配**: 前端需要更新 API 调用和响应数据处理
3. **文档更新**: 更新用户文档和 API 文档
