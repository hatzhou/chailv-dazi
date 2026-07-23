#!/usr/bin/env bash
# 差旅搭子 - Linux / macOS 启动脚本
set -e
cd "$(dirname "$0")"

# 若使用虚拟环境，请先激活：source venv/bin/activate
PY="${PYTHON:-python3}"
if ! "$PY" -c "import PySide6" 2>/dev/null; then
  echo "未检测到依赖，正在安装（首次运行可能需要几十秒）..."
  "$PY" -m pip install -r requirements.txt
fi

"$PY" main.py
