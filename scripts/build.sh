#!/usr/bin/env bash
# 差旅搭子 - 本地打包脚本（跨平台）
# 用法：
#   bash scripts/build.sh        # 当前平台打包
#
# 前置条件：
#   pip install pyinstaller -r requirements.txt
#
# 产物：
#   Windows: dist/差旅搭子/差旅搭子.exe
#   macOS:   dist/差旅搭子.app
#   Linux:   dist/差旅搭子/差旅搭子
set -euo pipefail

cd "$(dirname "$0")/.."
echo "=== 差旅搭子打包 ==="
echo "平台: $(uname -s)"
echo "Python: $(python --version 2>&1 || python3 --version 2>&1)"

PY=${PYTHON:-python3}

# 安装依赖
echo ""
echo "[1/4] 安装依赖..."
$PY -m pip install --upgrade pip
$PY -m pip install pyinstaller
$PY -m pip install -r requirements.txt

# 清理旧产物
echo ""
echo "[2/4] 清理旧构建..."
rm -rf build dist *.spec.bak

# 打包
echo ""
echo "[3/4] PyInstaller 打包..."
$PY -m PyInstaller chailv_dazi.spec --noconfirm

# 结果
echo ""
echo "[4/4] 构建完成。产物："
if [[ "$(uname -s)" == "Darwin" ]]; then
    ls -lh dist/差旅搭子.app
    echo ""
    echo "可直接双击 dist/差旅搭子.app 运行"
    echo "制作 DMG："
    echo "  hdiutil create -volname 差旅搭子 -srcfolder dist/差旅搭子.app -ov -format UDZO dist/差旅搭子.dmg"
else
    ls -lh dist/差旅搭子/ 2>/dev/null || ls -lh dist/ 2>/dev/null
    echo ""
    if [[ "$(uname -s)" == "Linux" ]]; then
        echo "可直接运行 dist/差旅搭子/差旅搭子"
    else
        echo "可直接双击 dist/差旅搭子/差旅搭子.exe"
    fi
fi
echo ""
echo "=== 打包成功 ==="
