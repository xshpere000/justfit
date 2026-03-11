# 任务 #5 修改报告：评估功能 Tab 界面重构

## 任务概述

重构 `TaskDetail.vue` 的四个评估功能 Tab 界面，使其直接使用后端 API 返回的字段结构，消除字段映射层。

## 修改时间

2025-03-09

## 修改文件

### 1. `frontend/src/api/analysis.ts`

#### 新增类型定义

```typescript
// 闲置检测分析结果
export interface IdleResult {
    vmName: string;
    cluster: string;
    hostIp: string;
    isIdle: boolean;
    idleType: string;
    confidence: number;
    riskLevel: string;
    daysInactive: number;
    lastActivityTime: string | null;
    recommendation: string;
}

// 资源配置优化分析结果
export interface RightSizeResult {
    vmName: string;
    cluster: string;
    hostIp: string;
    currentCpu: number;
    suggestedCpu: number;
    currentMemory: number;
    suggestedMemory: number;
    cpuP95: number;
    memoryP95: number;
    adjustmentType: string;
    confidence: number;
}

// 使用模式分析结果
export interface UsagePatternResult {
    vmName: string;
    datacenter: string;
    cluster: string;
    hostIp: string;
    optimizationType: string;
    usagePattern: string;
    volatilityLevel: string;
    coefficientOfVariation: number;
    peakHour: number | null;
    peakDay: string | null;
    recommendation: string;
}

// 资源错配分析结果
export interface MismatchResult {
    vmName: string;
    cluster: string;
    hostIp: string;
    mismatchType: string;
    currentConfig: { cpu: number; memoryGb: number };
    suggestedConfig: { cpu: number; memoryGb: number };
    recommendation: string;
}

// 资源分析完整响应
export interface ResourceAnalysisResponse {
    rightSize: RightSizeResult[];
    usagePattern: UsagePatternResult[];
    mismatch: MismatchResult[];
    summary: {
        rightSizeCount: number;
        usagePatternCount: number;
        mismatchCount: number;
        totalVmsAnalyzed: number;
    };
}

// 健康评分分析结果
export interface HealthScoreResult {
    overallScore: number;
    grade: string;
    subScores: {
        overcommit: number;
        balance: number;
        hotspot: number;
    };
    clusterCount: number;
    hostCount: number;
    vmCount: number;
    overcommitResults: Array<{...}>;
    balanceResults: Array<{...}>;
    hotspotHosts: Array<{...}>;
    overcommitScore: number;
    balanceScore: number;
    hotspotScore: number;
    findings: Array<{
        severity: string;
        category: string;
        cluster?: string;
        host?: string;
        description: string;
        details: Record<string, unknown>;
    }>;
    recommendations: string[];
}
```

#### 新增 API 函数

```typescript
// 获取闲置检测分析结果
export async function getIdleResults(taskId: number): Promise<IdleResult[]>

// 运行闲置检测分析
export async function runIdleAnalysis(taskId: number, config?: Record<string, unknown>): Promise<IdleResult[]>

// 获取资源分析结果
export async function getResourceResults(taskId: number): Promise<ResourceAnalysisResponse>

// 运行资源分析
export async function runResourceAnalysis(taskId: number, config?: Record<string, unknown>): Promise<ResourceAnalysisResponse>

// 获取健康评分分析结果
export async function getHealthResults(taskId: number): Promise<HealthScoreResult>

// 运行健康评分分析
export async function runHealthAnalysis(taskId: number, config?: Record<string, unknown>): Promise<HealthScoreResult>
```

### 2. `frontend/src/views/TaskDetail.vue`

#### 数据结构更新

**修改前**：
```typescript
const analysisData = reactive<{
  zombie: any[]
  rightsize: any[]
  tidal: any[]
  health: any | null
}>({
  zombie: [],
  rightsize: [],
  tidal: [],
  health: null
})
```

**修改后**：
```typescript
const analysisData = reactive<{
  idle: AnalysisAPI.IdleResult[]
  rightSize: AnalysisAPI.RightSizeResult[]
  usagePattern: AnalysisAPI.UsagePatternResult[]
  health: AnalysisAPI.HealthScoreResult | null
}>({
  idle: [],
  rightSize: [],
  usagePattern: [],
  health: null
})
```

#### 计算属性更新

```typescript
// 闲置检测 (Idle) Tab 过滤
const filteredIdleData = computed(() => {
  return analysisData.idle.filter((row) =>
    matchByKeyword(row, zombieSearch.value, ['vmName', 'cluster', 'hostIp', 'recommendation'])
  )
})

// 资源配置优化 (Right Size) Tab 过滤
const filteredRightSizeData = computed(() => {
  return analysisData.rightSize.filter((row) =>
    matchByKeyword(row, rightsizeSearch.value, ['vmName', 'cluster', 'hostIp'])
  )
})

// 使用模式分析 (Usage Pattern) Tab 过滤
const filteredUsagePatternData = computed(() => {
  return analysisData.usagePattern.filter((row) =>
    matchByKeyword(row, tidalSearch.value, ['vmName', 'cluster', 'usagePattern', 'recommendation'])
  )
})
```

#### 模板 Tab 更新

| Tab 名称 | 修改前标签 | 修改后标签 | 主要字段 |
|---------|----------|----------|---------|
| 闲置检测 | "僵尸VM" | "闲置检测" | vmName, cluster, hostIp, idleType, riskLevel, daysInactive, confidence, recommendation |
| 资源配置优化 | "Right Size" | "资源配置优化" | vmName, cluster, hostIp, currentCpu, suggestedCpu, currentMemory, suggestedMemory, adjustmentType, confidence |
| 使用模式 | "潮汐检测" | "使用模式" | vmName, cluster, hostIp, usagePattern, volatilityLevel, peakHour, peakDay, recommendation |
| 健康评分 | "健康评分" | "健康评分" | overallScore, grade, balanceScore, overcommitScore, hotspotScore, clusterCount, hostCount, vmCount, findings[], recommendations[] |

#### 新增辅助函数

```typescript
// 闲置类型相关
getIdleTypeText(type: string): string
getIdleTypeTagType(type: string): string

// 风险等级相关
getRiskLevelText(level: string): string
getRiskLevelTagType(level: string): string

// 内存格式化
formatMemoryGB(value: number): string

// 调整类型相关
getAdjustmentTypeText(type: string): string
getAdjustmentTypeTagType(type: string): string

// 使用模式相关
getUsagePatternText(pattern: string): string
getUsagePatternTagType(pattern: string): string

// 波动性相关
getVolatilityLevelText(level: string): string
getVolatilityLevelTagType(level: string): string

// 健康评分相关
getHealthGradeText(grade: string): string
getHealthGradeTagType(grade: string): string
getHealthScoreClass(score: number): string
getScoreColor(score: number): string
getOvercommitScoreColor(score: number): string
getHotspotScoreColor(score: number): string

// 发现问题相关
getFindingCategoryText(category: string): string
getFindingCategoryTagType(category: string): string

// 严重程度相关
getSeverityText(severity: string): string
getSeverityTagType(severity: string): string
```

#### 新增样式类

```scss
// 健康评分样式
.health-score-header { ... }
.health-score-value { ... }
.score-excellent { ... }
.score-good { ... }
.score-fair { ... }
.score-poor { ... }

.health-findings { ... }
.health-recommendations { ... }

// 文字颜色辅助类
.text-success { ... }
.text-warning { ... }
.text-danger { ... }
```

#### 删除的代码

- 废弃的 `runHealthAnalysis()` 函数（使用 connectionId 的旧版本）
- 废弃的 `fetchAnalysisResultWithRetry()` 函数
- 废弃的 `checkHasData()` 函数
- 重复的 `getHealthGradeText()` 函数定义

## API 变更

### 后端接口映射

| 前端 Tab | 后端 API | 数据路径 |
|---------|---------|---------|
| 闲置检测 | GET /api/analysis/tasks/{id}/idle | 直接返回数组 |
| 资源配置优化 | GET /api/analysis/tasks/{id}/resource | .rightSize |
| 使用模式 | GET /api/analysis/tasks/{id}/resource | .usagePattern |
| 健康评分 | GET /api/analysis/tasks/{id}/health | 直接返回对象 |

## 测试验证

### 编译状态
```bash
cd frontend && npm run build
```
✅ 编译成功，无错误无警告

### 功能验证点

1. **闲置检测 Tab**
   - 显示闲置 VM 列表
   - 闲置类型标签正确显示
   - 风险等级颜色正确

2. **资源配置优化 Tab**
   - 显示资源配置建议
   - 缩减建议显示绿色高亮
   - 扩容建议显示橙色高亮

3. **使用模式 Tab**
   - 显示使用模式分析
   - 模式标签正确显示
   - 波动性标签正确显示

4. **健康评分 Tab**
   - 显示综合评分和等级
   - 显示子评分（资源均衡、超配风险、热点集中）
   - 显示集群/主机/VM 数量
   - 显示发现的问题列表
   - 显示改进建议列表

## 注意事项

1. **无字段映射**：所有 Tab 直接使用后端返回的字段名，没有转换层
2. **API 变更**：废弃了旧的 `/zombie`, `/rightsize`, `/tidal` 接口
3. **新接口**：统一使用 `/idle`, `/resource`, `/health` 接口
4. **数据结构**：resource 接口返回结构化数据，包含 rightSize, usagePattern, mismatch 三个子项

## 回滚方案

如需回滚，恢复以下文件：
- `frontend/src/api/analysis.ts`
- `frontend/src/views/TaskDetail.vue`
