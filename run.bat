@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM 差旅搭子 - Windows 启动脚本
python -c "import PySide6" 2>nul || pip install -r requirements.txt
python main.py
pause
