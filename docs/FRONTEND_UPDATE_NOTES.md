# 后端更新通知 - 任务模式与采集天数配置

## 更新时间
2026-03-10

## 概述
后端新增任务模式配置和采集天数配置功能，支持自定义分析参数，前端需要相应调整。

---

## API 变更

### 1. 创建任务 - 新增参数

**端点**: `POST /api/tasks`

**新增请求字段**:
```json
{
  "name": "任务名称",
  "type": "collection",
  "connectionId": 1,
  "mode": "saving",          // 分析模式 (safe/saving/aggressive/custom)
  "baseMode": "saving",      // 仅 mode=custom 时有效，基础预设模式
  "metricDays": 7,            // 采集天数 (1-90)
  "config": {
    "customConfig": {       // 仅 mode=custom 时有效，自定义分析参数
      "idle": { "days": 30, "cpu_threshold": 10.0, "memory_threshold": 20.0 },
      "resource": { "rightsize": { "cpu_buffer_percent": 20.0 } },
      "health": { "overcommit_threshold": 1.5 }
    }
  }
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| mode | string | 否 | "saving" | 分析模式：安全/节省/激进/自定义 |
| baseMode | string | 否 | "saving" | 仅 mode=custom 时有效，基础预设模式 |
| metricDays | integer | 否 | null | 指标采集天数，1-90天 |
| config.customConfig | object | 否 | - | 自定义分析参数，覆盖预设阈值 |

---

### 2. 修改任务模式 API - 新增

**端点**: `PUT /api/tasks/{task_id}/mode`

---

### 3. 重新评估 API - 新增

**端点**: `POST /api/tasks/{task_id}/re-evaluate`

---

## 自定义配置完整结构

当 `mode=custom` 时，可通过 `config.customConfig` 覆盖预设阈值：

```json
{
  "mode": "custom",
  "baseMode": "saving",
  "config": {
    "customConfig": {
      "idle": {
        "days": 30,              // 闲置检测天数
        "cpu_threshold": 10.0,   // CPU 阈值 %
        "memory_threshold": 20.0, // 内存阈值 %
        "min_confidence": 60.0   // 最小置信度
      },
      "resource": {
        "rightsize": {
          "days": 7,                      // 分析天数
          "cpu_buffer_percent": 20.0,    // CPU 缓冲 %
          "memory_buffer_percent": 20.0, // 内存缓冲 %
          "high_usage_threshold": 85.0,  // 高使用率阈值 %
          "low_usage_threshold": 30.0,   // 低使用率阈值 %
          "min_confidence": 60.0           // 最小置信度
        },
        "usage_pattern": {
          "cv_threshold": 0.4,          // 变异系数阈值
          "peak_valley_ratio": 2.5       // 峰谷比
        },
        "mismatch": {
          "cpu_low_threshold": 30.0,    // CPU 低阈值 %
          "cpu_high_threshold": 70.0,   // CPU 高阈值 %
          "memory_low_threshold": 30.0, // 内存低阈值 %
          "memory_high_threshold": 70.0  // 内存高阈值 %
        }
      },
      "health": {
        "overcommit_threshold": 1.5,   // 超配阈值
        "hotspot_threshold": 7.0,      // 热点阈值 (VMs/核心)
        "balance_threshold": 0.6        // 均衡阈值
      }
    }
  }
}
```

---

## 前端需要修改的地方

### 1. 任务创建表单
- **模式选择**: 下拉框（安全/节省/激进/自定义）
- **基础模式**: 当选择自定义模式时显示（默认 saving）
- **采集天数**: 数字输入框（1-90天）
- **自定义参数**: 当选择自定义模式时，展开显示各分析模块的可配置参数

### 2. 任务卡片显示
- 显示当前任务的模式
- 显示采集天数配置
- 自定义模式时显示特殊标识

### 3. 任务详情页
- 显示当前模式和配置
- 提供修改模式的入口
- 提供"重新评估"按钮

### 4. 新增交互
- 模式修改功能
- 重新评估功能

---

## 模式说明

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| safe | 安全模式 - 保守阈值 | 生产环境、高可用要求 |
| saving | 节省模式 - 平衡阈值 | 默认推荐 |
| aggressive | 激进模式 - 最大化优化 | 测试环境、最大化发现问题 |
| custom | 自定义模式 | 用户自定义配置，基于 baseMode 覆盖参数 |

---

## 注意事项

1. **向后兼容**: mode、metricDays、baseMode 均为可选参数
2. **参数传递**: customConfig 必须嵌套在 config 对象中
3. **异步执行**: 重新评估 API 是异步的，需要轮询任务状态获取结果
4. **数据格式**: 所有响应字段使用 camelCase（如 metricDays, customConfig）
