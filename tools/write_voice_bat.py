"""重写「发语音测试.bat」：自提权 + 正确路径（避免 \\r 转义坑）。"""
import io

lines = [
    "@echo off",
    "setlocal",
    'cd /d "%~dp0"',
    "",
    "rem Need admin: Huorong blocks non-elevated cross-process module reads,",
    "rem so without elevation we cannot get the UIA tree and cannot switch chats.",
    "net session >nul 2>&1",
    "if %errorlevel%==0 goto run",
    "",
    "echo Requesting administrator privileges...",
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process \'%~f0\' -Verb RunAs"',
    "exit /b",
    "",
    ":run",
    "chcp 65001 >nul",
    "set PYTHONIOENCODING=utf-8",
    "set PYTHONUTF8=1",
    "",
    'set "PY=%~dp0..\\YF-Robot\\runtime\\python\\python.exe"',
    'if not exist "%PY%" set "PY=python"',
    "",
    "echo ==========================================",
    "echo  Send a voice message (to File Transfer)",
    "echo  WeChat will come to front for ~5 seconds.",
    "echo ==========================================",
    "echo.",
    '"%PY%" voice_test_cli.py "这是一条测试语音，听到就说明成功了" "文件传输助手" 0',
    "echo.",
    "pause",
]

data = ("\r\n".join(lines) + "\r\n").encode("gbk")
open("发语音测试.bat", "wb").write(data)

# 回读校验：路径必须完整留在同一行
back = open("发语音测试.bat", "rb").read().decode("gbk")
py_line = [l for l in back.splitlines() if l.startswith('set "PY=')]
assert py_line and py_line[0].endswith("python.exe\""), py_line
print("  OK:", py_line[0])
print("  行数:", len(back.splitlines()), "| 提权:", "RunAs" in back)
