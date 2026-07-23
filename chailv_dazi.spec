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
hiddenimports = []
hiddenimports += collect_submodules('matplotlib.backends')
hiddenimports += collect_submodules('PySide6.QtSvg')
hiddenimports += collect_submodules('PySide6.QtSvgWidgets')
hiddenimports += ['pdfplumber', 'pypdf', 'openpyxl', 'reportlab']

# 资源文件：matplotlib 字体 + PySide6 插件
datas = []
datas += collect_data_files('matplotlib', include_py_files=False)
datas += [(('assets/manual', 'assets/manual'))]
# 确保 docs 目录也打入（操作手册等）
datas += [('docs', 'docs')]

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
        icon='assets/icon.icns', # macOS 图标（可选）
    )
    app = BUNDLE(
        exe,
        a.binaries,
        a.datas,
        name='差旅搭子.app',
        icon='assets/icon.icns',
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
        icon='assets/icon.ico' if sys.platform == 'win32' else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name='差旅搭子',
    )
