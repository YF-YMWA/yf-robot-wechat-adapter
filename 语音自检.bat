@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0..\YF-Robot\runtime\python\python.exe"
if not exist "%PY%" set "PY=python"

echo ==========================================
echo  Voice self-check (no message will be sent)
echo ==========================================
echo.
"%PY%" voice_ptt.py

echo.
echo ==========================================
echo  Loopback test: which playback -^> mic works
echo  (a 1s 440Hz tone will sound, that is normal)
echo ==========================================
echo.
"%PY%" check_loopback_matrix.py

echo.
echo Docs: docs\VOICE.md
pause
