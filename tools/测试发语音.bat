@echo off
setlocal
chcp 936 >nul 2>nul
cd /d "%~dp0"
title 测试微信发语音入口

REM ============================================
REM  做两件事：
REM    1. 点一下微信的麦克风图标（切到语音模式）
REM    2. 再点回来（切回文字模式）
REM  全程截图，不会录音、不会发消息。
REM
REM  必须管理员：普通权限连鼠标都动不了微信的窗口。
REM ============================================

net session >nul 2>&1
if %errorlevel% equ 0 goto run

echo.
echo  需要管理员权限（不然驱动不了微信窗口）
echo  正在请求提权，请点"是"
echo.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:run
set "PY=%~dp0..\..\jingjing\runtime\python\python.exe"
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
echo   测试：点麦克风图标，看界面怎么变
echo  ============================================
echo.
echo  注意：
echo    · 请先把微信主窗口打开（别最小化）
echo    · 运行过程中鼠标会被移动到微信上，别去抢
echo    · 不会录音、不会发任何消息
echo.
pause

"%PY%" try_voice_mode.py

echo.
echo  截图已保存到 data\tmp\：
echo    voice-before.png  点之前（文字模式）
echo    voice-after.png   点之后（应该是语音模式）
echo    voice-back.png    再点回来（文字模式）
echo.
echo  把这三张图或者它们的路径发我，我看一下。
echo.
pause
endlocal
