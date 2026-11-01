"""改 check_uia.py：以「真的能切聊天」为判定标准。"""
import io

p = "check_uia.py"
s = io.open(p, encoding="utf-8").read()

start = s.index("probe = (")
end = s.index(")\n", s.index("print('INIT_OK')\\n")) + 2

new_probe = '''probe = (
    "from wechatauto import WeChatGUI\\n"
    "g = WeChatGUI()\\n"
    "print('INIT_OK')\\n"
    "try:\\n"
    "    ok = g.open_chat('文件传输助手')\\n"
    "    print('OPEN_CHAT', bool(ok))\\n"
    "except Exception as e:\\n"
    "    print('OPEN_CHAT', False, repr(e))\\n"
)
'''

s = s[:start] + new_probe + s[end:]

s = s.replace(
    'blocked = "控件树拿不到" in allout',
    'chat_ok = "OPEN_CHAT True" in allout\nblocked = ("控件树拿不到" in allout) or (not chat_ok)',
)

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("已改：以 open_chat 结果判定")
