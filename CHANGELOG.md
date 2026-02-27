# JustFit 变更日志

本文档记录 JustFit 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 待办
- 检查当前采集流程是否完整
- 验证性能指标采集是否正常
- 前端类型定义迁移到 v2.ts
- 修复任务状态刷新问题
- Service v2 集成到 app.go
- 完善连接器接口
- 添加集成测试和性能测试

---

## [0.0.2] - 2026-02-27

### Added
- **数据隔离架构**: VMMetric 模型添加 TaskID 字段，支持按任务隔离指标数据
- **按任务查询**: 新增 `ListByTaskAndVMAndType` 和 `DeleteByTaskID` 方法
- **H3C UIS 平台支持**: 兼容 H3C UIS 平台，与 vCenter 统一处理
- **6 种完整指标采集**: CPU、内存、磁盘读写、网络收发全部可用

### Changed
- **vCenter 指标采集**: 修改为 20 秒实时模式，使用空字符串获取聚合数据
- **采集流程传递 TaskID**: `CollectMetrics` 和 `ProcessVMMetrics` 添加 taskID 参数
- **分析引擎使用 TaskID**: 所有分析（僵尸 VM、Right Size、潮汐模式）使用任务隔离查询
- **任务删除 CASCADE**: 删除任务时自动清理关联指标数据

### Fixed
- **2026-02-27**: 修复指标数据任务隔离问题 - 不同任务的指标数据混在一起
- **2026-02-26**: 修复字段名大小写不匹配导致的数据丢失 BUG
  - 统一所有字段为驼峰命名（首字母小写）
  - 修复文件：20 个（前端 11 个 + 后端 9 个）
- 前后端字段命名统一为驼峰（首字母小写）
- 单位字段规范化：`cpuMhz`, `memoryGb`, `memoryMb`

### Architecture
- DTO 层设计 (15 个文件)
- Mapper 层实现 (6 个映射器)
- Logger 结构化日志系统 (5 个文件)
- Errors 统一错误处理
- Service v2 层 (3 个服务)
- appdir 简化 (统一数据目录管理)

### Testing
- Logger 单元测试 (12 个测试用例)
- Errors 单元测试 (12 个测试用例)

### Documentation
- CLAUDE.md 代码审查检查点
- 版本管理规范文档

---

## [0.0.1] - 2026-02-20

### Added
- 基础版本发布
- 多平台连接（vCenter）
- 数据采集与存储
- 四大分析功能（僵尸 VM、Right Size、潮汐模式、健康评分）
- 报告生成

---

## 版本说明

- **[Unreleased]**: 即将发布但尚未发布的变更
- **[0.0.2]**: 当前生产版本
- **[0.0.1]**: 基础底座版本（永不触发数据库重建）

### 变更类型
- **Added**: 新增功能
- **Changed**: 功能变更
- **Deprecated**: 即将废弃的功能
- **Removed**: 已移除的功能
- **Fixed**: Bug 修复
- **Security**: 安全问题修复
