# PDF 字体文件

请将中文字体文件放在此目录下。

## ⚠️ 重要提示：字体格式要求

**当前使用的 `gopdf` 库只支持标准 TTF (TrueType Font) 格式，不支持 TTC (TrueType Collection) 格式。**

- ✅ **支持**: `.ttf` 文件（单个字体）
- ❌ **不支持**: `.ttc` 文件（字体集合）

**检查字体格式**：
```bash
# 查看文件头部
head -c 4 simhei.ttf | od -A x -t x1z
# 输出 "ttcf" 表示 TTC 格式（不支持）
# 输出 "0001" 等其他值表示 TTF 格式（支持）
```

## 当前使用的字体

- **文件名**: `simhei.ttf` (黑体)
- **大小**: 约 9.7MB
- **格式**: 标准 TTF（非 TTC 集合）
- **状态**: ✅ 已验证可用

## 支持的其他字体文件

如果需要更换字体，可以使用以下任一字体文件（必须是 TTF 格式）：

1. **SimHei.ttf** - 黑体（Windows 标准）
2. **STSONG.TTF** - 华文宋体（macOS）
3. **WQY-ZenHei.ttf** - 文泉驿正黑（Linux 开源）

## 获取字体文件

### Windows
从 `C:\Windows\Fonts\` 复制以下任一文件：
- `simhei.ttf`（黑体，通常是 TTF 格式）
- `msyh.ttf`（微软雅黑，如果存在）
- ⚠️ 避免使用 `simsun.ttc`、`msyh.ttc`（TTC 格式不支持）

### macOS
从 `/System/Library/Fonts/` 或 `/Library/Fonts/` 复制：
- `STSONG.TTF`
- `STHeiti Light.ttf`（注意是 .ttf 不是 .ttc）
- `PingFang.ttf`（如果存在）

### Linux
安装字体包：
```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei

# 字体文件位于
/usr/share/fonts/truetype/wqy/
```

推荐的 Linux 开源字体：
- `WQY-ZenHei.ttf` - 文泉驿正黑
- `wqy-microhei.ttc` - ⚠️ 这是 TTC 格式，不支持

## 更换字体

如果要使用不同的字体文件：

1. 将新的 TTF 字体文件复制到此目录（`internal/report/fonts/`）
2. 重命名为 `simhei.ttf`，或修改 `pdf.go` 中的 `fontFilePath` 常量
3. 重新编译项目：`go build`
4. 字体将自动嵌入到二进制文件中

## 注意事项

- ⚠️ **TTC 字体集合不受支持**：gopdf 库无法识别 TTC 格式
- 字体文件会被嵌入到可执行文件中，会增加文件大小（约 10-20MB）
- 建议使用单个 `.ttf` 文件，避免使用 `.ttc` 集合文件
- 如果没有有效的 TTF 字体文件，PDF 生成会失败，测试会自动跳过

## 当前状态

- ✅ Markdown 模板系统已实现
- ✅ goldmark MD → HTML 转换已实现
- ✅ gopdf HTML → PDF 渲染已实现
- ✅ 中文字体已配置（simhei.ttf）
- ✅ PDF 生成功能完全可用
