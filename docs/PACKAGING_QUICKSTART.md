# 📦 JustFit 打包快速开始

## 一、环境检查

你的当前环境状态：

| 检查项 | 状态 |
|--------|------|
| Node.js | ✅ v24.12.0 |
| npm | ✅ 11.6.2 |
| Python 3.14 | ✅ 3.14.3 |
| 前端依赖 | ✅ 已安装 |
| Electron 依赖 | ❌ 未安装 |
| PyInstaller | ❌ 未安装 |

---

## 二、一键设置打包环境

```bash
make setup
```

这个命令会自动安装所有打包所需的依赖。

---

## 三、开始打包

### ⭐ 推荐：完整打包

打包成独立的 exe，用户无需安装 Python：

```bash
make package-all
```

**输出位置**：`dist/electron/JustFit-Setup-0.0.3-x64.exe`

**打包内容**：
- ✅ Python 后端（独立 exe）
- ✅ Electron 前端
- ✅ 所有依赖

---

### 方式二：基础打包

仅打包 Electron，用户需要安装 Python：

```bash
make package
```

**注意**：不推荐此方式，用户需要手动安装 Python 3.14 和所有依赖。

---

## 四、详细文档

查看完整打包文档：

```bash
cat docs/PACKAGING.md
```

---

## 五、常见问题

### Q: Electron 依赖安装失败？

```bash
cd electron && npm install && cd ..
```

### Q: PyInstaller 打包失败？

```bash
pip install pyinstaller
```

### Q: 打包后 exe 太大？

正常现象：
- Python 后端 exe：~50MB
- 完整安装包：~150MB

可以使用 UPX 压缩减小体积（需要单独安装 UPX）。

---

## 六、文件说明

| 文件 | 说明 |
|------|------|
| `backend/justfit_backend.spec` | PyInstaller 配置文件 |
| `scripts/build_backend.sh` | Python 后端打包脚本 |
| `scripts/build_all.sh` | 完整打包脚本 |
| `electron/backend.ts` | 后端进程管理（已支持 exe） |
| `docs/PACKAGING.md` | 详细打包文档 |

---

## 七、下一步

1. 运行 `make setup` 设置环境
2. 运行 `make package-all` 完整打包
3. 在 `dist/electron/` 找到生成的 exe
4. 分发给用户测试！
