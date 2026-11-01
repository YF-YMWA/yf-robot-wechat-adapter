"""修 voiceMode 启动读取（按实际 4 空格缩进整段替换）。"""
import io
import os
import re

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if "_cp2" in s:
    print("已改过")
    raise SystemExit(0)

pat = re.compile(
    r"# 启动时把当前语音模式打出来，方便确认「配置有没有生效」\n"
    r"try:\n"
    r"(?:.*\n)*?"
    r"except Exception:\n"
    r"    pass\n"
)

new = '''# 启动时读一次语音模式（不能用 _cfg —— 它在下面第 530 多行才加载，
# 用了会被 except 吞掉，导致永远停在默认的 file）
try:
    import io as _io2
    import json as _json2
    _cp2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with _io2.open(_cp2, encoding="utf-8") as _f2:
        _w2 = (_json2.load(_f2) or {}).get("wechat") or {}
    _vm_cfg = _w2.get("voiceMode") or "file"
    if _vm_cfg in ("file", "ptt"):
        VOICE_MODE = _vm_cfg
    _vod = _w2.get("voiceOutDevice")
    if isinstance(_vod, int):
        VOICE_OUT_DEVICE = _vod
except Exception as _e2:
    print("[语音] 读取 config.json 的 voiceMode 失败：%r" % (_e2,))
'''

m = pat.search(s)
if not m:
    print("正则未命中")
    raise SystemExit(1)

s = s[: m.start()] + new + s[m.end():]
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已改：从 config.json 直接读（4 空格缩进版）")
