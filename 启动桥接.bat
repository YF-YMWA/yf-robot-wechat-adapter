@echo off
setlocal
chcp 936 >nul 2>nul
cd /d "%~dp0"
title YF-Robot 微信适配器

REM ============================================
REM  这个适配器违反微信用户协议，有封号风险。
REM  仅供个人学习研究，风险自负。
REM ============================================

REM --no-elevate：跳过提权（测试用；普通权限下能收消息但发不出去）
if "%~1"=="--no-elevate" goto run

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

REM ===== 找 Python =====
REM 坑：系统 PATH 里那个 C:\...\WindowsApps\python.exe 是微软商店的假壳，
REM     执行它只会弹商店或者直接失败（退出码 9009）。
REM     顺序：自带运行时 > 隔壁主项目的运行时 > 真正的 PATH python > 常见安装位置
set "PY="

if exist "%~dp0runtime\python\python.exe" set "PY=%~dp0runtime\python\python.exe"

if not defined PY if exist "%~dp0..\YF-Robot\runtime\python\python.exe" set "PY=%~dp0..\YF-Robot\runtime\python\python.exe"

if not defined PY (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PY (
            echo %%P | findstr /i /c:"WindowsApps" >nul
            if errorlevel 1 set "PY=%%P"
        )
    )
)

if not defined PY (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
    ) do if not defined PY if exist %%D set "PY=%%~D"
)

if not defined PY (
    echo.
    echo  [错误] 找不到可用的 Python
    echo.
    echo  这个适配器需要 Python 3.10 以上，并且要装几个库：
    echo      pip install wechatauto-replica requests pillow pywin32 comtypes cryptography numpy
    echo.
    echo  如果主项目 YF-Robot 就在旁边，它自带了 Python，
    echo  适配器放在它旁边（同一个父目录）就能自动找到。
    echo.
    pause
    exit /b 1
)

REM 再验一次：能不能真的跑起来（防住商店假壳那种情况）
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [错误] 找到了 %PY%
    echo         但它跑不起来（多半是微软商店的占位程序）
    echo.
    echo  请装一个真的 Python 3.10+，或者用主项目自带的运行时：
    echo      ..\YF-Robot\runtime\python\python.exe
    echo.
    pause
    exit /b 1
)

echo  使用 Python: %PY%
echo.

if not exist "config.json" (
    echo  [提示] 没有 config.json，正在从 config.example.json 复制
    copy /y "config.example.json" "config.json" >nul
    echo         请先填好 yfRobot.baseUrl 和 persona.master.wxids
    echo.
    pause
    exit /b 1
)

REM 核心地址（config.json 里的 yfRobot.baseUrl 优先；这里只是兜底）
if not defined WHALE_BOT_URL set "WHALE_BOT_URL=http://127.0.0.1:8899/api/wechat"

set "TRIES=0"
:restart
"%PY%" wechatauto_bridge.py
set "RC=%errorlevel%"

REM 退出码 0 = 正常退出（含「已有实例在跑」「用户 Ctrl+C」），不重启
if "%RC%"=="0" goto done

REM 9009 = 找不到程序，重启也没用，直接说清原因
if "%RC%"=="9009" (
    echo.
    echo  [错误] Python 启动失败（退出码 9009 = 找不到程序）
    echo         路径: %PY%
    echo.
    echo  这个路径要么不存在，要么是微软商店的占位程序。
    echo  解决办法：用主项目自带的运行时，或者装一个真正的 Python 3.10+。
    echo.
    pause
    goto done
)

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
