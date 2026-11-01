"""去掉语音块里对 _voice_text 的重置（它把前面算好的结果清掉了）。"""
import io
import os
import re

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if "不能再把 _voice_text 置空" in s:
    print("已改过")
    raise SystemExit(0)

pat = re.compile(
    r"[ \t]*_voice_spec = data\.get\(\"voice\"\) if isinstance\(data, dict\) else None\n"
    r"[ \t]*_voice_text = \"\"\n"
    r"[ \t]*if isinstance\(_voice_spec, dict\):\n"
    r"[ \t]*_voice_text = str\(_voice_spec\.get\(\"text\"\) or \"\"\)\.strip\(\)\n"
    r"[ \t]*elif isinstance\(_voice_spec, str\):\n"
    r"[ \t]*_voice_text = _voice_spec\.strip\(\)\n"
)

m = pat.search(s)
if not m:
    print("正则未命中")
    raise SystemExit(1)

indent = " " * (len(m.group(0)) - len(m.group(0).lstrip()))
new = (
    indent + "# 注意：这里不能再把 _voice_text 置空重算。\n"
    + indent + "# 前面已经算好（含「陌生人不给语音」），以前这里重置一次，\n"
    + indent + "# 导致「[媒体] 这条只发语音」之后语音块被跳过 —— 文字跳过、语音没发，最后什么都没发。\n"
)

s = s[: m.start()] + new + s[m.end():]
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已修复：不再重置 _voice_text")
