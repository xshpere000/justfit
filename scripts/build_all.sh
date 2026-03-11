#!/bin/bash
# 完整打包脚本 - Python 后端 + Electron 前端

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - 完整打包流程"
echo "========================================="
echo ""

# 1. 检查环境
echo ">>> 检查环境..."

if ! command -v node &> /dev/null; then
    echo "错误: Node.js 未安装"
    exit 1
fi

if ! command -v python3.14 &> /dev/null && ! command -v python &> /dev/null; then
    echo "错误: Python 未安装"
    exit 1
fi

if ! command -v pyinstaller &> /dev/null; then
    echo "警告: PyInstaller 未安装，将跳过 Python 后端打包"
    echo "      如需打包 Python，请运行: pip install pyinstaller"
    PYTHON_BUILD=false
else
    PYTHON_BUILD=true
fi

echo "  环境检查完成"
echo ""

# 2. 安装依赖
echo ">>> 检查依赖..."

if [ ! -d "electron/node_modules" ]; then
    echo "  安装 Electron 依赖..."
    cd electron && npm install && cd ..
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "  安装前端依赖..."
    cd frontend && npm install && cd ..
fi

echo "  依赖检查完成"
echo ""

# 3. 打包 Python 后端
if [ "$PYTHON_BUILD" = true ]; then
    echo ">>> 打包 Python 后端..."
    ./scripts/build_backend.sh
    echo ""

    # 将打包好的 exe 复制到 resources 目录
    if [ -f "backend/dist/justfit_backend.exe" ]; then
        echo ">>> 复制 Python 后端到资源目录..."
        mkdir -p resources/backend
        cp backend/dist/justfit_backend.exe resources/backend/
        echo "  后端已复制到 resources/backend/justfit_backend.exe"
    fi
    echo ""
fi

# 4. 构建前端
echo ">>> 构建前端..."
cd frontend
npm run build
echo "  前端构建完成"
cd ..
echo ""

# 5. 构建 Electron 主进程
echo ">>> 构建 Electron 主进程..."
cd electron
npm run build
echo "  Electron 构建完成"
cd ..
echo ""

# 6. 打包 Electron 应用
echo ">>> 打包 Electron 应用..."

# 修改 electron-builder 配置以包含打包好的 Python 后端
if [ "$PYTHON_BUILD" = true ] && [ -f "resources/backend/justfit_backend.exe" ]; then
    # 使用包含 Python exe 的配置
    cat > electron-builder-full.json << 'BUILD_CONFIG'
{
  "appId": "com.justfit.app",
  "productName": "JustFit",
  "directories": {
    "output": "dist/electron"
  },
  "files": [
    "electron/dist/**/*",
    "frontend/dist/**/*"
  ],
  "extraResources": [
    {
      "from": "resources/backend/justfit_backend.exe",
      "to": "justfit_backend.exe"
    }
  ],
  "win": {
    "target": ["nsis"],
    "icon": "resources/icons/app.png",
    "artifactName": "${productName}-Setup-${version}-${arch}.${ext}"
  },
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true,
    "perMachine": true,
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true
  }
}
BUILD_CONFIG

    cd electron
    npx electron-builder --win --x64 --config ../electron-builder-full.json
    cd ..
    rm -f electron-builder-full.json
else
    # 使用原始配置（不包含 Python exe）
    cd electron
    npx electron-builder --win --x64
    cd ..
fi

echo ""
echo "========================================="
echo "  打包完成！"
echo "========================================="
echo ""
echo "  输出目录: dist/electron/"
echo ""

# 显示生成的文件
if [ -d "dist/electron" ]; then
    echo "  生成的文件:"
    ls -lh dist/electron/*.exe 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}'
fi

echo ""
echo "  安装包可以分发给用户使用！"
echo ""
