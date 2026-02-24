# JustFit Makefile

.PHONY: all dev build test test-unit test-integration clean lint fmt help

# 变量定义
BINARY_NAME=justfit
BUILD_DIR=build
COVERAGE_DIR=coverage
GO=go
GOFLAGS=-v
WAILS=wails

# 默认目标
all: build

# 开发模式
dev:
	@echo "启动开发模式..."
	$(WAILS) dev

# 构建
build:
	@echo "构建应用..."
	$(WAILS) build

# 构建前端
build-frontend:
	@echo "构建前端..."
	cd frontend && npm run build

# 测试
test: test-unit test-integration
	@echo "所有测试完成"

# 单元测试
test-unit:
	@echo "运行单元测试..."
	@./test/scripts/test_unit.sh

# 集成测试
test-integration:
	@echo "运行集成测试..."
	@./test/scripts/test_integration.sh

# E2E 测试指导
test-e2e:
	@echo "E2E 测试指导..."
	@./test/scripts/test_e2e.sh

# 代码格式化
fmt:
	@echo "格式化代码..."
	$(GO) fmt ./...
	gofmt -w .

# 代码检查
lint:
	@echo "运行代码检查..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./...; \
	else \
		echo "golangci-lint 未安装，跳过"; \
	fi

# 代码检查（快速）
lint-fast:
	@echo "运行快速代码检查..."
	$(GO) vet ./...

# 安装依赖
deps:
	@echo "安装依赖..."
	$(GO) mod download
	$(GO) mod tidy
	cd frontend && npm install

# 清理
clean:
	@echo "清理构建文件..."
	rm -rf $(BUILD_DIR)
	rm -rf $(COVERAGE_DIR)
	rm -f coverage.out
	rm -f *.log

# 生成文档
docs:
	@echo "生成文档..."
	@echo "文档位于 docs/ 目录"

# 帮助
help:
	@echo "JustFit Makefile 命令:"
	@echo ""
	@echo "  make dev         - 启动开发模式"
	@echo "  make build       - 构建应用"
	@echo "  make test        - 运行所有测试"
	@echo "  make test-unit   - 运行单元测试"
	@echo "  make test-integration - 运行集成测试"
	@echo "  make test-e2e    - E2E 测试指导"
	@echo "  make fmt         - 格式化代码"
	@echo "  make lint        - 运行代码检查"
	@echo "  make deps        - 安装依赖"
	@echo "  make clean       - 清理构建文件"
	@echo ""
