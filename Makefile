.PHONY: dev build-frontend build-backend package-electron build-all clean test help install

# 默认目标
help:
	@echo "JustFit - 构建命令"
	@echo ""
	@echo "开发命令:"
	@echo "  make dev           - 启动开发模式（前后端一起启动）"
	@echo ""
	@echo "打包命令:"
	@echo "  make build-frontend   - 仅打包前端（Vue 3 → 静态文件）"
	@echo "  make build-backend    - 仅打包后端（Python → exe）"
	@echo "  make package-electron - 基于已打包的前后端打包 Electron"
	@echo "  make build-all        - 一键完整打包（前端+后端+Electron）⭐"
	@echo ""
	@echo "其他命令:"
	@echo "  make clean         - 清理所有构建文件"
	@echo "  make test          - 运行后端测试"
	@echo "  make test-frontend - 运行前端测试"
	@echo "  make install       - 安装所有依赖"
	@echo ""

# ============================================
# 开发命令
# ============================================

dev:
	@./scripts/dev/dev.sh

# ============================================
# 打包命令
# ============================================

build-frontend:
	@./scripts/build/build-frontend.sh

build-backend:
	@./scripts/build/build-backend.sh

package-electron:
	@./scripts/build/package-electron.sh

build-all:
	@./scripts/build/build-all.sh

# ============================================
# 其他命令
# ============================================

clean:
	@echo ">>> 清理构建文件..."
	@rm -rf frontend/dist
	@rm -rf backend/dist backend/build
	@rm -rf electron/dist
	@rm -rf dist/electron
	@rm -rf resources/backend
	@echo "清理完成"

test:
	@echo ">>> 运行后端测试..."
	@python3.14 -m pytest tests/ -v

test-frontend:
	@echo ">>> 运行前端测试..."
	@cd frontend && npm test

install:
	@echo ">>> 安装依赖..."
	@echo "Python 依赖:"
	@cd backend && uv pip install -e 1>/dev/null || echo "  (跳过，可能用其他方式管理)"
	@echo "前端依赖:"
	@cd frontend && npm install 1>/dev/null || echo "  (跳过，可能用其他方式管理)"
	@echo "Electron 依赖:"
	@cd electron && npm install 1>/dev/null || echo "  (跳过，可能用其他方式管理)"
	@echo "依赖安装完成"
