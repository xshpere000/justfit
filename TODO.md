# JustFit 统一 TODO

> 更新时间：2026-02-24

## v0.0.2 已完成 ✅

### 架构重构
- [x] DTO 层设计 (15 个文件)
- [x] Mapper 层实现 (6 个映射器)
- [x] Logger 结构化日志系统 (5 个文件)
- [x] Errors 统一错误处理
- [x] Service v2 层 (3 个服务)
- [x] appdir 简化 (统一数据目录管理)

### 测试
- [x] Logger 单元测试 (12 个测试用例)
- [x] Errors 单元测试 (12 个测试用例)

### 文档
- [x] docs/0.0.2/ 系列文档 (12 个文档)
- [x] CLAUDE.md 代码审查检查点
- [x] manual.md 手动测试指南
- [x] problems.md 问题跟踪

### 问题修复
- [x] appdir 开发/生产模式区分简化
- [x] 日志系统初始化
- [x] 数据目录统一管理
- [x] 移除前端 localStorage 缓存，统一使用后端存储

## 待完成 ⏳

### P0 - 前端适配 (高优先级)

#### 1) 前端类型定义迁移
- [ ] 将 `frontend/src/api/index.ts` 等文件中的类型引用更新为使用 `types/v2.ts`
- [ ] 确保 API 响应处理与新的 DTO 结构兼容

#### 2) 任务状态刷新问题
- [ ] 修复历史评估数据为空的问题 (前端状态管理)
- [ ] 确保任务详情进入时重新调用 API 获取最新数据

### P1 - 功能集成 (中优先级)

#### 3) Service v2 集成到 app.go
- [ ] 逐步将 `app.go` 中的方法迁移到使用 v2 service 层
- [ ] 替换 `fmt.Printf` 为新的 logger 系统
- [ ] 使用统一的错误处理

#### 4) 连接器接口完善
- [ ] 抽象并完善 `connector.Connector` 接口
- [ ] 确保 vCenter 和 H3C UIS 实现一致

### P2 - 测试补充 (低优先级)

#### 5) 集成测试
- [ ] Service 层集成测试
- [ ] API 端到端测试
- [ ] 数据采集流程测试

#### 6) 性能测试
- [ ] 大数据量场景测试 (1000+ VM)
- [ ] 并发任务测试

## 废弃内容

以下内容已在 v0.0.2 重构中废弃：

- ~~开发/生产模式区分~~ (统一使用平台标准目录)
- ~~旧的类型转换方式~~ (使用 DTO + Mapper)
- ~~fmt.Printf 日志方式~~ (使用 structured logger)

## 备注

- 数据目录统一管理：
  - Windows: `%APPDATA%\justfit`
  - macOS: `~/Library/Application Support/justfit`
  - Linux: `~/.local/share/justfit`
- 可通过 `JUSTFIT_DATA_DIR` 环境变量自定义数据目录
