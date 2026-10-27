@echo off
setlocal
chcp 936 >nul 2>nul
cd /d "%~dp0"
title YF-Robot 微信适配器

REM ============================================
REM  这个适配器违反微信用户协议，有封号风险。
REM  仅供个人学习研究，风险自负。
REM ============================================

net session >nul 2>&1
if %errorlevel% equ 0 goto run

echo.
echo  ============================================
echo   需要管理员权限（读取微信进程、操作窗口）
echo  ============================================
echo.
echo  正在请求提权，请在弹窗点"是"
echo.

powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:run
echo.
echo  ============================================
echo   YF-Robot 微信适配器
echo  ============================================
echo.
echo  提示：微信窗口请保持可见，不要最小化到托盘
echo        否则发送会失败
echo.
echo  [!] 违反微信用户协议，有封号风险，仅供学习研究
echo.

set "PY="
for %%p in (python.exe) do if not defined PY set "PY=%%~$PATH:p"
if not defined PY (
    for %%d in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) do if not defined PY if exist %%d set "PY=%%~d"
)

if not defined PY (
    echo [错误] 找不到 Python
    echo        请先安装 Python 3.10+，或手动运行 python wechatauto_bridge.py
    pause
    exit /b 1
)

if not exist "config.json" (
    echo [提示] 没有 config.json，正在从 config.example.json 复制
    copy /y "config.example.json" "config.json" >nul
    echo        请先填好 gateway.wechat.inboundToken 和 persona.master.wxids
    echo.
    pause
    exit /b 1
)

set "TRIES=0"
:restart
"%PY%" wechatauto_bridge.py
set "RC=%errorlevel%"

REM 退出码 0 = 正常退出（含「已有实例在跑」「用户 Ctrl+C」），不重启
if "%RC%"=="0" goto done

set /a TRIES+=1
echo.
echo ============================================
echo   适配器异常退出（代码 %RC%）
echo   5 秒后自动重启（第 %TRIES%/8 次）
echo   崩溃现场：data\bridge-crash.log
echo ============================================
echo.
if %TRIES% GEQ 8 goto gaveup
timeout /t 5 /nobreak >nul
goto restart

:gaveup
echo.
echo [supervisor] 连续异常退出 8 次，停止自动重启。
echo 请把 data\bridge-crash.log 最后一段发出来。
echo.
pause
goto done

:done
pause
endlocal
