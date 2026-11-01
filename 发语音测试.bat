@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
setlocal
cd /d "%~dp0"

set "PY=%~dp0..\YF-Robot\runtime\python\python.exe"
if not exist "%PY%" set "PY=python"

echo ==========================================
echo  Send a voice message (to File Transfer)
echo  WeChat will come to front for ~5 seconds.
echo ==========================================
echo.
"%PY%" voice_test_cli.py "这是一条测试语音，听到就说明成功了" "文件传输助手" 0
echo.
pause
