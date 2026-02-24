# JustFit 统一 TODO

> 更新时间：2026-02-24
> 说明：本文件为项目唯一待办清单；历史已完成事项已归档删除。

## 本次重构已完成项

### 1. 配置化管理基础设施

- [x] 创建测试环境配置文件 .env（包含H3C UIS和vCenter配置）
- [x] 后端配置加载模块 internal/config/config.go
- [x] 前端配置模块 frontend/src/config/index.ts

### 2. 数据库模型重构

- [x] 扩展Task模型，添加totalVMs/selectedVMs/connectionId等字段
- [x] 完善TaskAnalysisResult与TaskVMSnapshot关联关系
- [x] 数据库AutoMigrate自动迁移

### 3. 前后端数据类型统一

- [x] 定义统一API数据类型 - TaskInfo扩展
- [x] 创建类型转换工具函数 frontend/src/utils/transform.ts

### 4. 任务服务重构

- [x] 后端任务服务 - 创建任务时保存totalVMs/selectedVMs

## 后续优化目标

> 重要原则：H3C UIS优先实现，但VMware vCenter同样重要，需保证两者都能正常工作并具备扩展性。

### P0（当前优先）

#### 1) 虚拟化平台连接器重构

- [ ] **抽象连接器接口** `internal/connector/interface.go`
  - 定义统一的连接器接口（Connect, GetVMs, GetClusters, GetHosts, CollectMetrics等）
  - 接口设计需兼容H3C UIS和VMware vCenter两种实现

- [ ] **H3C UIS连接器实现**（优先）
  - 完善 `internal/connector/uis.go` 实现
  - 实现接口定义的所有方法
  - 使用Python探测脚本验证API可用性
  - 添加详细的日志记录

- [ ] **VMware vCenter连接器实现**
  - 完善 `internal/connector/vcenter.go` 实现
  - 复用现有的govmomi实现
  - 确保与UIS接口一致

- [ ] **配置化平台选择**
  - 根据.env中的DEFAULT_PLATFORM配置选择默认连接器
  - 支持通过连接管理界面动态切换平台

#### 2) 前端任务Store适配

- [ ] 修改 `frontend/src/stores/task.ts`
  - 适配新的后端TaskInfo数据结构
  - 使用 transform.ts 中的转换函数
  - 正确显示totalVMs和selectedVMs

- [ ] 任务卡片展示修复
  - 正确显示虚拟机数量
  - 历史评估结果的持久化显示

#### 3) 自动化测试

- [ ] 创建单元测试：配置模块加载
- [ ] 创建单元测试：数据库模型CRUD
- [ ] 创建单元测试：任务服务创建和查询
- [ ] 创建集成测试：完整的数据采集流程

### P1（功能完善）

#### 4) 数据采集和评估流程

- [ ] 评估结果仅包含选择的虚拟机（过滤逻辑修复）
- [ ] 评估结果的持久化存储验证
- [ ] 前后端数据一致性验证

#### 5) 连接管理

- [ ] 支持平台类型选择（h3c-uis / vcenter）
- [ ] 连接测试功能适配新接口
- [ ] 连接凭据的安全存储

### P2（优化与发布）

#### 6) 体验与稳定性

- [ ] 任务进度轮询策略优化
- [ ] 高数据量场景交互稳定性
- [ ] 错误处理和用户提示优化

## 备注

- H3C UIS优先级高于vCenter：在功能实现时，优先完成H3C UIS的对接，但两者都需要保证可用性
- 扩展性：连接器接口设计需考虑未来可能接入的新平台（如OpenStack等）
- 配置化：平台选择通过配置文件管理，支持运行时切换
