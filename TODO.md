# JustFit 统一 TODO

> 更新时间：2026-02-25

## v0.0.2 已完成 ✅

### 架构重构
- [x] DTO 层设计 (15 个文件)
- [x] Mapper 层实现 (6 个映射器)
- [x] Logger 结构化日志系统 (5 个文件)
- [x] Errors 统一错误处理
- [x] Service v2 层 (3 个服务)
- [x] appdir 简化 (统一数据目录管理)

### 统一版本管理
- [x] internal/version/version.go - 统一版本定义文件
- [x] 版本号命名规范：MAJOR.MINOR.PATCH
- [x] MajorVersions 统一管理在 version.go
- [x] 后端所有代码从 version.go 读取版本
- [x] GetAppVersion() API - 前端获取版本信息
- [x] Home.vue 显示版本号
- [x] 只需修改 version.go 即可完成全局版本升级

### 日志系统完善
- [x] app.go - 替换所有 fmt.Printf 为结构化日志
- [x] internal/task/task.go - 添加日志器
- [x] internal/service/task_service.go - 添加日志器
- [x] internal/version/manager.go - 添加日志器
- [x] 所有日志使用适当的级别 (Debug/Info/Warn/Error)

### 命名规范统一 ⭐ (v0.0.2 核心改进)
- [x] **前后端字段命名统一为驼峰（首字母小写）**
- [x] 修复字段名大小写不匹配导致的数据丢失 BUG
- [x] 统一单位字段命名：`cpuMhz`, `memoryGb`, `memoryMb`
- [x] 修复文件：20 个（前端 11 个 + 后端 9 个）
- [x] 验证：824 个 JSON tag 全部符合规范
- [x] 详见：`api/0.0.2/CHANGELOG.md`

### Bug 修复
- [x] 修复 SQLite SET_NULL 兼容性问题 → CASCADE
- [x] AssessmentTask.TableName() 方法添加
- [x] version/manager.go 使用 storage.Settings 模型
- [x] 修复硬编码版本号问题（app.go 诊断信息）
- [x] **修复 transform.ts 数据映射 BUG（VMCount → vmCount）**

### 测试
- [x] Logger 单元测试 (12 个测试用例)
- [x] Errors 单元测试 (12 个测试用例)

### 文档
- [x] CLAUDE.md 代码审查检查点（添加单位字段命名规则）
- [x] README.md 添加版本升级指南
- [x] 版本管理规范文档
- [x] `api/0.0.2/CHANGELOG.md` - 变更日志
- [x] `docs/0.0.2/QUICKSTART.md` - 快速开始指南

### 版本管理规范
1. **版本来源**: `internal/version/version.go` 中的 `Version` 常量
2. **大版本定义**: `version.go` 中的 `MajorVersions` 数组
3. **更新方式**: 只需修改 `version.go` 文件中的 `Version` 常量
4. **后端获取**: `import "justfit/internal/version"` → `version.Version`
5. **前端获取**: 调用 `GetAppVersion()` API 获取版本信息
6. **命名规范**:
   - MAJOR: 重大架构变更，数据库不兼容升级
   - MINOR: 新功能添加，向后兼容
   - PATCH: Bug 修复，不影响功能

### 版本升级需修改的文件（3个）
| 文件 | 修改内容 |
|------|----------|
| `internal/version/version.go` | 修改 `Version` 常量 |
| `frontend/package.json` | 同步修改 `version` 字段 |
| `frontend/src/types/api.ts` | 更新注释中的版本号和日期 |

## 待完成 ⏳

### P0 - 数据采集方向 (高优先级)

#### 1) 数据采集优化
- [ ] 检查当前采集流程是否完整
- [ ] 验证性能指标采集是否正常
- [ ] 检查数据 ETL 流程

### P1 - 前端适配 (中优先级)

#### 2) 前端类型定义迁移
- [ ] 将 `frontend/src/api/index.ts` 等文件中的类型引用更新为使用 `types/v2.ts`
- [ ] 确保 API 响应处理与新的 DTO 结构兼容

#### 3) 任务状态刷新问题
- [ ] 修复历史评估数据为空的问题 (前端状态管理)
- [ ] 确保任务详情进入时重新调用 API 获取最新数据

### P2 - 功能集成 (低优先级)

#### 4) Service v2 集成到 app.go
- [ ] 逐步将 `app.go` 中的方法迁移到使用 v2 service 层
- [x] 替换 `fmt.Printf` 为新的 logger 系统
- [ ] 使用统一的错误处理

#### 5) 连接器接口完善
- [ ] 抽象并完善 `connector.Connector` 接口
- [ ] 确保 vCenter 和 H3C UIS 实现一致

### P3 - 测试补充 (低优先级)

#### 6) 集成测试
- [ ] Service 层集成测试
- [ ] API 端到端测试
- [ ] 数据采集流程测试

#### 7) 性能测试
- [ ] 大数据量场景测试 (1000+ VM)
- [ ] 并发任务测试

## 废弃内容

以下内容已在重构中废弃：

- ~~开发/生产模式区分~~ (统一使用平台标准目录)
- ~~旧的类型转换方式~~ (使用 DTO + Mapper)
- ~~fmt.Printf 日志方式~~ (使用 structured logger)
- ~~Task/TaskAnalysisResult 混用~~ (统一为 AssessmentTask/TaskAnalysisJob)
- ~~AnalysisResult/Alert 独立表~~ (合并到 AnalysisFinding)
- ~~分散的仓库文件~~ (合并到单一 repos.go)

## 备注

- 数据目录统一管理：
  - Windows: `%APPDATA%\justfit`
  - macOS: `~/Library/Application Support/justfit`
  - Linux: `~/.local/share/justfit`
- 可通过 `JUSTFIT_DATA_DIR` 环境变量自定义数据目录

- 版本信息：
  - 当前版本：0.0.2
  - 基础底座版本：0.0.1（永不触发数据库重建）
