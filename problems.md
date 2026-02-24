# 问题清单

所有的问题都必须遵循【记录模板】，AI 发现并提出的问题必须在【AI发现问题列表】中列出，AI 不能自行解决，必须由用户确认后才能继续。

## AI发现问题列表

> 以下问题由AI发现，可能为真实问题，也可能为误判，需人工验证。

## 人工发现问题列表

> 以下问题由人工测试发现，如果修复请勾选并在问题下面简要描述修复方案

### 时间：2026/02/24
问题描述：点击评估任务卡片进入任务详情，点击开启某些评估功能（例如僵尸VM检测），能够评估成功并显示结果，但是退出任务详情再次后再点击同一张卡片进入，历史的评估数据都为空
问题等级：P1
修复状态：✅ 已定位原因
修复建议：数据已正确保存到数据库（已验证），问题在前端状态管理
修复方案：
1. 后端验证：通过数据库检查确认数据存在
2. 前端需要检查：进入任务详情时是否重新调用 `GetTaskDetail` 和 `GetTaskAnalysisResult`
3. 检查前端 Pinia store 或组件缓存是否导致不刷新数据

### 时间：2026/02/24
问题描述：新建应用后看到历史任务
问题等级：P1
修复状态：✅ 已定位并修复
修复建议：任务数据存储在浏览器的 localStorage 中，键名为 `justfit_tasks`
修复方案：
- **数据来源**：`localStorage.getItem('justfit_tasks')`
- **修复**：已修改 `App.vue`，应用启动时先调用 `syncTasksFromBackend()` 从后端同步，而不是先读取 localStorage
- **临时清除**：在浏览器控制台执行 `localStorage.removeItem('justfit_tasks')`

### 时间：2026/02/24
问题描述：wails dev 启动后，日志目录为空
问题等级：P2
修复状态：✅ 已修复
修复建议：已初始化 logger 系统，日志会写入到平台标准数据目录的 logs 子目录
修复方案：
- 日志文件位置：`~/.local/share/justfit/logs/app.log` (Linux)
- Windows: `%APPDATA%\justfit\logs\app.log`
- macOS: `~/Library/Application Support/justfit/logs/app.log`

### 时间：2026/02/24
问题描述：appdir 模块的开发/生产模式区分导致混乱
问题等级：P1
修复状态：✅ 已修复
修复建议：已简化 appdir，统一使用平台标准数据目录
修复方案：
- 去除了 `IsDevMode()` 检测
- 所有平台统一使用标准的用户数据目录
- Linux: `~/.local/share/justfit/`
- Windows: `%APPDATA%\justfit`
- macOS: `~/Library/Application Support/justfit`

### 时间：2026/02/24
问题描述：历史任务显示问题 - 项目根目录删除 .justfit 后仍然显示历史任务
问题等级：P2
修复状态：✅ 已解决
修复建议：之前的开发模式检测不稳定，导致数据库位置不确定
修复方案：
- 现在统一使用平台标准目录，不会再出现这个问题
- 如需清除数据，删除对应平台的目录即可：
  - Linux: `rm -rf ~/.local/share/justfit/`
  - Windows: 删除 `%APPDATA%\justfit` 文件夹
  - macOS: `rm -rf ~/Library/Application Support/justfit/`

## 记录模板

时间：2026/02/23
问题描述：xxx
问题等级：P1
修复状态：未修复
修复建议：xxx
修复方案：xxx
