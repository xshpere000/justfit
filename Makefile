.PHONY: dev build package clean test help package-backend package-all setup

# 默认目标
help:
	@echo "JustFit - 构建命令"
	@echo ""
	@echo "使用方法:"
	@echo "  make dev           - 启动开发模式"
	@echo "  make build         - 生产构建"
	@echo "  make package       - 打包 Electron 应用（不含 Python exe）"
	@echo "  make package-backend - 仅打包 Python 后端为 exe"
	@echo "  make package-all   - 完整打包（Python exe + Electron）⭐"
	@echo "  make setup         - 一键设置打包环境"
	@echo "  make clean         - 清理构建文件"
	@echo "  make test          - 运行测试"
	@echo ""

# 开发模式
dev:
	@echo ">>> 启动开发环境..."
	@./scripts/dev.sh

# 生产构建
build:
	@echo ">>> 生产构建..."
	@./scripts/build.sh

# 打包应用（基础版本，不含 Python exe）
package:
	@echo ">>> 打包 Electron 应用..."
	@./scripts/package.sh

# 打包 Python 后端
package-backend:
	@echo ">>> 打包 Python 后端..."
	@./scripts/build_backend.sh

# 完整打包（Python exe + Electron）
package-all:
	@echo ">>> 完整打包（Python + Electron）..."
	@./scripts/build_all.sh

# 清理
clean:
	@echo ">>> 清理构建文件..."
	rm -rf frontend/dist
	rm -rf electron/dist
	rm -rf dist/electron
	@echo "清理完成"

# 运行测试
test:
	@echo ">>> 运行后端测试..."
	@python3.14 -m pytest tests/ -v

# 设置打包环境
setup:
	@echo ">>> 设置打包环境..."
	@./scripts/setup_packaging.sh

# 运行前端测试
test-frontend:
	@echo ">>> 运行前端测试..."
	@cd frontend && npm test

# 安装依赖
install:
	@echo ">>> 安装依赖..."
	@echo "Python 依赖:"
	@cd backend && uv pip install -e 1>/dev/null || echo "  (跳过，可能用其他方式管理)"
	@echo "前端依赖:"
	@cd frontend && npm install 1>/dev/null || echo "  (跳过，可能用其他方式管理)"
	@echo "Electron 依赖:"
	@cd electron && npm install 1>/dev/null || echo "  (跳过，可能用其他方式管理)"
	@echo "依赖安装完成"
