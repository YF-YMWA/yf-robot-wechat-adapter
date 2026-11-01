@echo off
setlocal
cd /d "%~dp0"
set "PS1=%~dp0tools\fix-defender-service.ps1"
if not exist "%PS1%" (
  echo [X] 找不到 tools\fix-defender-service.ps1
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','\"%PS1%\"'"
echo.
echo 已申请管理员权限，请在弹窗里点「是」。
timeout /t 3 >nul
