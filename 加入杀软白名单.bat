@echo off
setlocal
cd /d "%~dp0"

rem 用 PowerShell 自提权运行白名单脚本（会弹一次 UAC）
set "PS1=%~dp0tools\whitelist-av.ps1"

if not exist "%PS1%" (
  echo [X] 找不到 tools\whitelist-av.ps1
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','\"%PS1%\"'"

echo.
echo 已申请管理员权限，请在弹出窗口里点「是」，然后按提示操作。
timeout /t 3 >nul
