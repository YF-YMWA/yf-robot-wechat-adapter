@echo off
setlocal
chcp 936 >nul 2>nul
cd /d "%~dp0"
title YF-Robot 适配器 · 修复并自检

REM ============================================
REM  这个脚本做三件事：
REM    1. 确认管理员权限（没有就自己提权）
REM    2. 把微信主窗口从托盘/最小化调出来
REM    3. 跑诊断，把问题直接打印出来
REM ============================================

net session >nul 2>&1
if %errorlevel% equ 0 goto run

echo.
echo  正在请求管理员权限（诊断微信需要）...
echo  请在弹窗点"是"
echo.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:run
echo.
echo  ============================================
echo   YF-Robot 适配器 · 修复并自检
echo  ============================================
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
    echo  [错误] 找不到 Python
    pause
    exit /b 1
)

echo  [1/3] 尝试把微信窗口调出来...
"%PY%" -c "import sys; sys.path.insert(0,'.'); import win32gui, win32con, psutil; ws=[]; win32gui.EnumWindows(lambda h,_: (ws.append(h) if ('Qt5' in (win32gui.GetClassName(h) or '') and win32gui.IsWindowVisible(h)) else None), None); n=0
for h in ws:
    t=win32gui.GetWindowText(h) or ''
    if not t: continue
    if win32gui.IsIconic(h):
        win32gui.ShowWindow(h, win32con.SW_RESTORE); n+=1
    try: win32gui.SetForegroundWindow(h)
    except Exception: pass
print('      恢复了 %d 个窗口' % n)" 2>nul
echo.
echo  [2/3] 运行诊断...
echo.
"%PY%" diagnose.py
echo.
echo  ============================================
echo   诊断完成。报告已存到 data\diagnosis.txt
echo  ============================================
echo.

echo  看上面的输出：
echo    · 「微信窗口」那段如果写着「在托盘/已最小化」
echo      → 点右下角托盘的微信图标，把主窗口点出来再试
echo    · 「管理员: 否」
echo      → 右键 启动桥接.bat →「以管理员身份运行」
echo    · 都正常
echo      → 可以直接启动适配器了
echo.

set /p GO=  现在启动适配器？(y/N):
if /i not "%GO%"=="y" goto end

echo.
echo  启动适配器...
echo.
call "%~dp0启动桥接.bat"

:end
echo.
pause
endlocal
