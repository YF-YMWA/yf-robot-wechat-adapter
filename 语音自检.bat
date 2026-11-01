@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set PY=..\YF-Robot\runtime\python\python.exe
if not exist "%PY%" set PY=python

echo ============================================
echo   发语音条自检（不会发任何消息）
echo ============================================
echo.
"%PY%" voice_ptt.py

echo.
echo ============================================
echo   线路测试：播放到录音，看哪条通
echo   （会响 1 秒 440Hz 声音，属正常）
echo ============================================
echo.
"%PY%" check_loopback_matrix.py

echo.
echo 详细说明见 docs\VOICE.md
pause
