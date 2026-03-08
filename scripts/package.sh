#!/bin/bash
# Electron 打包脚本 - 使用 electron-builder 打包应用

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "  JustFit - Electron Packaging"
echo "========================================="
echo ""

# 确保已构建
if [ ! -d "frontend/dist" ]; then
    echo "错误: 前端未构建，请先运行 ./scripts/build.sh"
    exit 1
fi

if [ ! -d "electron/dist" ]; then
    echo "错误: Electron 未构建，请先运行 ./scripts/build.sh"
    exit 1
fi

# 检查图标
if [ ! -f "resources/icons/app.png" ]; then
    echo "错误: 应用图标不存在 (resources/icons/app.png)"
    exit 1
fi

echo ">>> 准备打包资源..."

# 创建临时配置
cat > electron-builder.json.tmp << 'BUILD_CONFIG'
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
      "from": "backend/",
      "to": "backend/",
      "filter": ["**/*", "!**/__pycache__/**", "!**/*.pyc", "!**/.pytest_cache/**"]
    }
  ],
  "win": {
    "target": ["nsis", "portable"],
    "icon": "resources/icons/app.png",
    "artifactName": "\${productName}-\${version}-\${arch}.\${ext}"
  }
}
BUILD_CONFIG

# 使用 npm run electron-builder 或直接调用
echo ">>> 开始打包 Windows 版本..."
cd electron
npx electron-builder --win --x64 --config ../electron-builder.json.tmp
cd ..

# 清理临时配置
rm -f electron-builder.json.tmp

echo ""
echo "========================================="
echo "  打包完成！"
echo "========================================="
echo ""
echo "  输出目录: dist/electron/"
echo ""
echo "  安装包:"
ls -lh dist/electron/*.exe 2>/dev/null || echo "  (未找到 .exe 文件)"
echo ""
