"""检查微信控件树（UIA）通不通。

这是「能不能切聊天 / 能不能验证语音条」的前提。
通 → 什么都能做；不通 → 只能操作当前打开的窗口。

用法：python check_uia.py
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

probe = (
    "from wechatauto import WeChatGUI\n"
    "g = WeChatGUI()\n"
    "print('INIT_OK')\n"
    "try:\n"
    "    ok = g.open_chat('文件传输助手')\n"
    "    print('OPEN_CHAT', bool(ok))\n"
    "except Exception as e:\n"
    "    print('OPEN_CHAT', False, repr(e))\n"
)

print("  正在初始化微信 GUI（约 10~20 秒）…")
try:
    p = subprocess.run(
        [PY, "-c", probe],
        capture_output=True,
        timeout=120,
        cwd=HERE,
        creationflags=0x08000000,
    )
except subprocess.TimeoutExpired:
    print("  [X] 初始化超时")
    sys.exit(2)

out = (p.stdout or b"").decode("utf-8", "ignore")
err = (p.stderr or b"").decode("utf-8", "ignore")
allout = out + err

if "INIT_OK" not in out:
    print("  [X] 初始化失败")
    tail = [l for l in allout.splitlines() if l.strip()][-4:]
    for l in tail:
        print("     " + l[:150])
    sys.exit(2)

chat_ok = "OPEN_CHAT True" in allout
blocked = ("控件树拿不到" in allout) or (not chat_ok)
ocr_only = "UIA 树不可用" in allout

print("")
if blocked or ocr_only:
    print("  [X] 控件树拿不到 —— 现在只能用 OCR 驱动")
    print("      影响：切聊天可能失败；发完读不到消息，无法确认是不是语音条")
    print("")
    print("  常见原因与处理：")
    print("    1) 安全软件拦了「模块枚举/进程读取」")
    print("       → 火绒：防护中心 → 信任区 → 添加文件/目录，加入：")
    print("         " + os.path.normpath(os.path.join(HERE, "..", "YF-Robot", "runtime", "python", "python.exe")))
    print("         " + os.path.normpath(os.path.join(HERE, "..", "YF-Robot")))
    print("         " + HERE)
    print("    2) 适配器用管理员运行（微信不是管理员）→ 改成普通双击启动")
    sys.exit(1)

print("  [OK] 控件树可用 —— 可以切聊天、可以验证语音条")
sys.exit(0)
