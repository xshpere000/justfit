.PHONY: dev build package clean test help

# 默认目标
help:
	@echo "JustFit - 构建命令"
	@echo ""
	@echo "使用方法:"
	@echo "  make dev       - 启动开发模式"
	@echo "  make build     - 生产构建"
	@	@echo "  make package   - 打包应用"
	@	@echo "  make clean     - 清理构建文件"
	@	@echo "  make test      - 运行测试"
	@echo ""

# 开发模式
dev:
	@echo ">>> 启动开发环境..."
	@./scripts/dev.sh

# 生产构建
build:
	@echo ">>> 生产构建..."
	@./scripts/build.sh

# 打包应用
package:
	@echo ">>> 打包应用..."
	@./scripts/package.sh

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
	@cd backend && PYTHONPATH=. python3.14 -m pytest tests/ -v

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
