@echo off
setlocal
cd /d "%~dp0"

rem Need admin: Huorong blocks non-elevated cross-process module reads,
rem so without elevation we cannot get the UIA tree and cannot switch chats.
net session >nul 2>&1
if %errorlevel%==0 goto run

echo Requesting administrator privileges...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process '%~f0' -Verb RunAs"
exit /b

:run
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set "PY=%~dp0..\YF-Robot\runtime\python\python.exe"
if not exist "%PY%" set "PY=python"

echo ==========================================
echo  Send a voice message (to File Transfer)
echo  WeChat will come to front for ~5 seconds.
echo ==========================================
echo.
"%PY%" voice_test_cli.py
echo.
pause
