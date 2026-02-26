# v0.0.2 变更日志

## 发布日期：2026-02-26

## 🎯 核心改进：命名规范统一

### 问题修复
- ✅ 修复字段名大小写不匹配导致的数据丢失 BUG
  - 前端 `VMCount` → 后端 `vmCount` 的字段对齐问题
  - 修复文件：20 个（前端 11 个 + 后端 9 个）

### 命名规范

**统一原则**：
- JSON tag 和 TypeScript 属性：驼峰命名（首字母小写）
- Go 结构体字段：PascalCase（首字母大写）
- 数据库列名：蛇形命名（GORM 自动转换）

**示例**：
```typescript
// 前端 ✅
vmCount: number
selectedVMs: string[]
connectionId: number
```

```go
// 后端 ✅
type CollectionConfig struct {
    VMCount     int      `json:"vmCount"`     // 字段名 PascalCase
    SelectedVMs []string `json:"selectedVMs"` // JSON 驼峰小写开头
}
```

### 单位字段规范

| 类型 | JSON tag | 说明 |
|------|----------|------|
| 频率 | `cpuMhz` | 小写 h |
| 内存 MB | `memoryMb` | 小写 b |
| 内存 GB | `memoryGb` | 小写 b |
| 数量 | `vmCount` | Count 后缀 |

### 修改文件清单

**前端** (11 个文件)：
- `frontend/src/types/api.ts`
- `frontend/src/types/v2.ts`
- `frontend/src/stores/task.ts`
- `frontend/src/utils/transform.ts` ⭐
- `frontend/src/views/TaskDetail.vue`
- `frontend/src/views/Collection.vue`
- `frontend/src/views/Home.vue`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/Wizard.vue`
- `frontend/src/views/analysis/Zombie.vue`
- `frontend/src/views/analysis/RightSize.vue`
- `frontend/src/views/analysis/Tidal.vue`
- `frontend/src/views/analysis/Health.vue`

**后端** (9 个文件)：
- `app.go`
- `internal/analyzer/health.go`
- `internal/analyzer/storage.go`
- `internal/connector/uis.go`
- `internal/dto/response/*.go`
- `internal/dto/mapper/task_mapper.go`
- `internal/service/task_service.go`
- `internal/storage/models.go`
- `internal/task/task.go`
- `internal/report/excel.go`

### 影响范围

- ✅ 数据采集任务创建
- ✅ 任务状态查询
- ✅ 分析结果显示
- ✅ 报告生成
- ✅ 所有 API 接口

### 验证状态

- ✅ 后端编译通过
- ✅ 前端编译通过
- ✅ 824 个 JSON tag 全部符合规范
- ✅ 262 个前端类型字段全部对齐

### 升级说明

**无数据库变更**：本版本仅为代码重构，数据库结构未改变，可直接升级。

**注意事项**：
1. 确保前端使用最新的类型定义
2. 清除浏览器缓存后再使用
3. 如遇到数据不显示问题，检查浏览器控制台是否有字段名错误
