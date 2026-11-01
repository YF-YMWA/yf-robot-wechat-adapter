@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
setlocal
cd /d "%~dp0"

set "PY=%~dp0..\YF-Robot\runtime\python\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" check_uia.py
echo.
pause
