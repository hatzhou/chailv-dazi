# -*- mode: python ; coding: utf-8 -*-
"""
差旅搭子 - PyInstaller 打包配置
用法：
    pyinstaller chailv_dazi.spec

产物：
    - Windows: dist/差旅搭子/差旅搭子.exe（目录模式，启动快）
    - macOS:   dist/差旅搭子.app（标准 .app 包）
    - Linux:   dist/差旅搭子/差旅搭子（目录模式）

说明：
    采用目录模式（onedir）而非单文件（onefile），
    避免每次启动解压临时文件导致的启动慢和杀软误报。
"""
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 隐式导入：matplotlib 后端 + PySide6 模块
# 注意：不显式列 pypdf（pdfplumber 会按需拉入，显式列会导致 CI 上找不到时报错）
hiddenimports = []
hiddenimports += collect_submodules('matplotlib.backends')
hiddenimports += collect_submodules('PySide6.QtSvg')
hiddenimports += collect_submodules('PySide6.QtSvgWidgets')
hiddenimports += ['pdfplumber', 'openpyxl', 'reportlab']

# 资源文件：matplotlib 字体 + 手册截图 + 文档
datas = []
datas += collect_data_files('matplotlib', include_py_files=False)
# 仅当目录存在时打入，避免 CI 报错
if os.path.isdir('assets/manual'):
    datas += [('assets/manual', 'assets/manual')]
if os.path.isdir('docs'):
    datas += [('docs', 'docs')]

# 图标（可选，不存在则用默认）
_icon_win = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else None
_icon_mac = 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None

# 入口
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=datas,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',           # 用 PySide6，不需要 tkinter
        'PyQt5', 'PyQt6',    # 避免冲突
        'test', 'tests',
        'unittest',
        'pydoc',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 平台相关：macOS 生成 .app
if sys.platform == 'darwin':
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name='差旅搭子',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,           # GUI 应用，不显示终端
        icon=_icon_mac,          # macOS 图标（可选）
    )
    app = BUNDLE(
        exe,
        a.binaries,
        a.datas,
        name='差旅搭子.app',
        icon=_icon_mac,
        bundle_identifier='com.chailv-dazi.app',
        info_plist={
            'CFBundleName': '差旅搭子',
            'CFBundleDisplayName': '差旅搭子',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSAppleEventsUsageDescription': '用于发票邮件导入功能',
        },
    )
else:
    # Windows / Linux：目录模式
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name='差旅搭子',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,           # GUI 应用
        icon=_icon_win,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name='差旅搭子',
    )
