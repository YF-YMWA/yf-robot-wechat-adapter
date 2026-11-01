"""修：启动时读 voiceMode 的代码写在 _cfg 定义之前 → 一直静默失败。

现象：config.json 里明明是 ptt，日志却打印「启动语音模式：file」。
原因：那段 try 里用了 _cfg，而 _cfg 在第 536 行才加载，这时还是 undefined，
      被 except 吞掉 → 保持默认 file。

改：直接从同目录 config.json 读，不依赖 _cfg 的加载顺序。
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

old = '''  # 启动时把当前语音模式打出来，方便确认「配置有没有生效」
  try:
      _vm_cfg = ((_cfg.get("wechat") or {}).get("voiceMode") or "file")
      if _vm_cfg in ("file", "ptt"):
          VOICE_MODE = _vm_cfg
      _vod = (_cfg.get("wechat") or {}).get("voiceOutDevice")
      if isinstance(_vod, int):
          VOICE_OUT_DEVICE = _vod
  except Exception:
      pass'''

new = '''  # 启动时读一次语音模式（这里不能用 _cfg —— 它在下面才加载，
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
      print("[语音] 读取 config.json 的 voiceMode 失败：%r" % (_e2,))'''

if old not in s:
    print("未命中（可能已改过）")
    raise SystemExit(0)

s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)

# 顺带在启动自检那行前面也打印（确认日志能看到）
print("已改：启动时直接读 config.json")
