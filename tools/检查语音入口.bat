@echo off
setlocal
chcp 936 >nul 2>nul
cd /d "%~dp0"
title 检查微信有没有「发语音」入口

REM ============================================
REM  扫描微信主窗的控件树，看有没有发语音的按钮。
REM  必须管理员权限：微信是高权限进程，
REM  普通权限下 UIA 读不到它的控件（会显示 0 个控件）。
REM ============================================

net session >nul 2>&1
if %errorlevel% equ 0 goto run

echo.
echo  需要管理员权限才能读微信的控件树
echo  正在请求提权，请点"是"
echo.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:run
set "PY=%~dp0..\..\YF-Robot\runtime\python\python.exe"
if not exist "%PY%" set "PY="
if not defined PY (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) do if not defined PY if exist %%D set "PY=%%~D"
)
if not defined PY (
    echo  [错误] 找不到 Python
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   扫描微信控件树
echo  ============================================
echo.
echo  提示：微信主窗口请先打开（别最小化到托盘）
echo.

"%PY%" check_voice_entry.py

echo.
echo  ============================================
echo   看上面的结果：
echo     · 「名字带语音关键词的控件」大于 0
echo       → 有发语音的入口，可以继续做
echo     · 全是 0、控件总数也是 0
echo       → 权限还是不够，或者微信版本没这个功能
echo  ============================================
echo.
pause
endlocal
