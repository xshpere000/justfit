# JustFit

JustFit 是面向多云/虚拟化平台资源优化的交互式桌面工具，基于 Wails v2（Go + Vue 3 / Vite）构建，产品覆盖:

1. 多平台连接采集、ETL 清洗与 SQLite 存储（当前聚焦 vCenter，后续陆续接入 H3C UIS、深信服 SCP 等平台）。
2. 僵尸 VM、Right Size、潮汐与平台健康等智能分析；可根据指标灵活调整算法阈值。
3. 报告生成（JSON/HTML/PDF/Excel）、任务管理与导出能力。
4. Dashboard/Connections/Tasks/Analysis/Settings 多页面，任务状态、分析与报告双向联动。

核心目标是让运维与云平台团队通过统一界面快速识别资源浪费、获得可执行建议，并持续导出可审计的报告。

## 版本管理

### 当前版本

- **版本号**: 0.0.2
- **基础底座版本**: 0.0.1

### 版本升级指南

当需要发布新版本时，只需修改以下文件：

| 文件 | 修改内容 |
|------|----------|
| `internal/version/version.go` | 修改 `Version` 常量（如 `"0.0.2"` → `"0.0.3"`） |
| `frontend/package.json` | 同步修改 `version` 字段 |
| `frontend/src/types/api.ts` | 更新注释中的版本号和日期 |

**注意**：

- 0.0.1 是基础底座版本，永远不会触发数据库重建
- 只有当数据库结构发生不兼容变更时，才需要将旧版本添加到 `MajorVersions` 数组
- 前端版本号从后端 API 获取，无需手动维护

### 版本号命名规范

- **MAJOR.MINOR.PATCH** 格式
- **MAJOR**: 重大架构变更，数据库不兼容升级
- **MINOR**: 新功能添加，向后兼容
- **PATCH**: Bug 修复，不影响功能

## 开发与构建

### 依赖

- Go 1.24+
- Node.js 18+（推荐使用 nvm 管理）
- Wails CLI（`go install github.com/wailsapp/wails/v2/cmd/wails@latest`）

### 本地调试

1. 进入项目根目录，执行 `npm install`（在 `frontend/` 内部）
2. 运行 `wails dev` 启动开发模式，前端通过 Vite 热更新，后端 Go 代码同步生效
3. 浏览器访问 `http://localhost:34115`（或默认 Wails 桌面窗口）进行联调

### 生产构建

> 该命令会构建 Go 后端与 Vue 前端，生成各平台可发布包（Windows NSIS、Linux AppImage/deb、macOS DMG）。 默认输出路径为 `build/bin/`，可通过 `-o` 参数自定义输出文件名。支持指定构建平台（如 `-platform windows/amd64`）和启用 UPX 压缩（需先安装 UPX）。示例命令如下：

```bash
# 构建当前平台的可发布包，不指定二进制输出路径会默认生成在 `build/bin/` 下
wails build

# 构建指定平台的可发布包（示例：Windows 64 位），并自定义输出文件名
wails build -platform windows/amd64 -o JustFit_0.0.2_amd64-portable.exe

# 构建指定平台的可发布包，并使用 UPX 压缩生成的二进制文件（需要先安装 UPX）
wails build -platform windows/amd64 -o JustFit_0.0.2_amd64-portable.exe -upx
```

### 目录结构

- `frontend/`：Vue 3 + Vite + Pinia 构建的 UI，包含 views、components、stores 与 api 抽象层。
- `internal/`：Go 后端核心模块（connector、etl、analyzer、storage、task 等）。
- `internal/version/`：版本管理模块，统一版本定义。
- `api/0.0.2/`：v0.0.2 API 文档与变更日志。
- `docs/0.0.2/`：v0.0.2 开发文档。

## 文档与版本

### v0.0.2 (2026-02-26)

**核心改进**：命名规范统一，修复数据丢失 BUG

- ✅ 前后端字段命名统一为驼峰（首字母小写）
- ✅ 单位字段规范化：`cpuMhz`, `memoryGb`, `memoryMb`
- ✅ 修复文件：20 个（前端 11 个 + 后端 9 个）
- ✅ 验证：824 个 JSON tag 全部符合规范

详细变更：查看 `api/0.0.2/CHANGELOG.md` 或 `docs/0.0.2/QUICKSTART.md`

### v0.0.1 (2026-02-20)

基础版本发布，包含：
- 多平台连接（vCenter）
- 数据采集与存储
- 四大分析功能
- 报告生成

参考 `docs/0.0.1/` 下的需求规范、设计方案、测试计划、部署指南与变更日志。
