#!/bin/bash
# JustFit 一键版本号更新脚本
# 用法: ./scripts/dev/update-version.sh 0.0.x

set -e

NEW_VERSION="$1"

# 校验参数
if [ -z "$NEW_VERSION" ]; then
    echo "用法: $0 <新版本号>"
    echo "示例: $0 0.0.5"
    exit 1
fi

if ! echo "$NEW_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "错误: 版本号格式不正确，应为 x.x.x（如 0.0.5）"
    exit 1
fi

# 定位项目根目录（脚本在 scripts/dev/ 下，向上两级）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "项目根目录: $ROOT_DIR"
echo "目标版本: $NEW_VERSION"

# 读取当前版本（从 backend/__init__.py 作为基准）
CURRENT_VERSION=$(grep -oE '[0-9]+\.[0-9]+\.[0-9]+' "$ROOT_DIR/backend/app/__init__.py" | head -1)
echo "当前版本: $CURRENT_VERSION"

if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
    echo "版本号与当前版本相同，无需更新。"
    exit 0
fi

# 使用 sed 替换各文件中的版本号（兼容 Linux 和 macOS）
SED_INPLACE() {
    if sed --version 2>/dev/null | grep -q GNU; then
        sed -i "$@"
    else
        sed -i '' "$@"
    fi
}

echo ""
echo "正在更新版本号..."

# 1. backend/app/__init__.py
FILE="$ROOT_DIR/backend/app/__init__.py"
SED_INPLACE "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" "$FILE"
echo "  ✓ backend/app/__init__.py"

# 2. electron-builder.json
FILE="$ROOT_DIR/electron-builder.json"
SED_INPLACE "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" "$FILE"
echo "  ✓ electron-builder.json"

# 3. frontend/src/components/AppShell.vue
FILE="$ROOT_DIR/frontend/src/components/AppShell.vue"
SED_INPLACE "s/appVersion = ref('$CURRENT_VERSION')/appVersion = ref('$NEW_VERSION')/" "$FILE"
echo "  ✓ frontend/src/components/AppShell.vue"

# 4. frontend/src/components/VersionUpgradeDialog.vue
#    该文件展示"旧版本 → 新版本"，旧版本替换为当前版本，新版本替换为目标版本
FILE="$ROOT_DIR/frontend/src/components/VersionUpgradeDialog.vue"
SED_INPLACE "s/0\.[0-9]\+\.[0-9]\+<\/el-tag>/$NEW_VERSION<\/el-tag>/g" "$FILE"
echo "  ✓ frontend/src/components/VersionUpgradeDialog.vue"

# 5. frontend/src/types/api.ts
FILE="$ROOT_DIR/frontend/src/types/api.ts"
SED_INPLACE "s/Version: $CURRENT_VERSION/Version: $NEW_VERSION/" "$FILE"
echo "  ✓ frontend/src/types/api.ts"

echo ""
echo "版本号已从 $CURRENT_VERSION 更新为 $NEW_VERSION"
echo ""
echo "注意: 版本变更会在下次启动时触发数据库清空迁移，请提前备份数据。"
