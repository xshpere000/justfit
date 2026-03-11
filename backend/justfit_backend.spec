# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - JustFit Backend
将 Python FastAPI 后端打包成独立可执行文件
"""

import sys
from pathlib import Path

# 获取项目根目录（使用绝对路径）
# 注意：在 Windows 打包时，请确保在项目根目录执行 pyinstaller backend/justfit_backend.spec
BACKEND_ROOT = Path('./backend').resolve()
PROJECT_ROOT = BACKEND_ROOT.parent.resolve()
# 图标文件路径（Windows 需要 .ico 格式）
ICON_PATH = PROJECT_ROOT / 'resources' / 'icons' / 'app.ico'
# 如果没有 .ico 文件，使用 None（PyInstaller 会使用默认图标）
ICON_FILE = str(ICON_PATH) if ICON_PATH.exists() else None

block_cipher = None

# 收集所有导入的模块
a = Analysis(
    ['app/main.py'],  # 入口文件（相对于 pathex）
    pathex=[str(BACKEND_ROOT)],
    binaries=[],
    datas=[
        # 包含配置文件（如果有）
        # (str(BACKEND_ROOT / 'config.json'), 'app'),
    ],
    hiddenimports=[
        # FastAPI 相关
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',

        # 数据库相关
        'sqlalchemy',
        'sqlalchemy.ext',
        'sqlalchemy.ext.asyncio',
        'aiosqlite',

        # Pydantic
        'pydantic',
        'pydantic.dataclasses',

        # vCenter 连接器
        'pyvmomi',
        'pyvmomi.vim',
        'pyvmomi.soap',
        'pyvmomi.ssl',

        # HTTP 客户端
        'httpx',
        'httpx._transports.default',

        # 报告生成
        'openpyxl',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'matplotlib',
        'matplotlib.pyplot',

        # 安全
        'cryptography',
        'cryptography.fernet',

        # 日志
        'structlog',

        # WebSocket
        'websockets',
        'websockets.server',
        'websockets.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib.tests',
        'pandas',
        'numpy.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤不需要的文件
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='justfit_backend',  # 输出的 exe 文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用 UPX 压缩（需要安装 UPX）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台（调试用，发布时可改为 False）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)
