@echo off
REM 差旅搭子 - Windows 本地打包脚本
REM 用法：双击或命令行执行 scripts\build.bat
setlocal enabledelayedexpansion

cd /d "%~dp0\.."
echo === 差旅搭子打包 (Windows) ===

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 python，请先安装 Python 3.10+ 并加入 PATH
    pause
    exit /b 1
)

echo [1/4] 安装依赖...
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m pip install -r requirements.txt

echo.
echo [2/4] 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/4] PyInstaller 打包...
python -m PyInstaller chailv_dazi.spec --noconfirm

echo.
echo [4/4] 构建完成。产物在 dist\差旅搭子\
echo 可直接双击 dist\差旅搭子\差旅搭子.exe 运行
echo.
echo 制作安装包（需 NSIS）：
echo   makensis scripts\installer.nsi
echo.
pause
