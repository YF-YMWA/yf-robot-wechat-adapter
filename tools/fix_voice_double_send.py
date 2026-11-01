"""修两处：
1. ptt 成功后仍发文件（`_vp = ""` 是假值 → 又被 core_tts 覆盖 → 发文件）
2. 按住 Alt 的时机：微信打开录音面板需要一点时间，先把静音头拉长
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

# 1. 用明确的布尔量记住「已经发过语音条」，不要靠空字符串
old = '''                            if _res.get("ok"):
                                log("[语音] 已按住 Alt %.1fs，验证=%s（None=没读到消息，不能确认是语音条）"
                                    % (_res.get("seconds") or 0, _res.get("verified")))
                                _vp = ""   # 已经发过了，别再当文件发一遍'''
new = '''                            if _res.get("ok"):
                                log("[语音] 已按住 Alt %.1fs，验证=%s（None=没读到消息，不能确认是语音条）"
                                    % (_res.get("seconds") or 0, _res.get("verified")))
                                # 这里必须用布尔量：以前写 _vp = ""，
                                # 空字符串是假值，下面 if not _vp 又会重新合成并发成文件
                                _voice_sent = True'''
assert old in s, "锚点1未命中"
s = s.replace(old, new, 1)

old2 = '''                    if not _vp:
                        _vp = core_tts(_ctx)'''
new2 = '''                    if not _voice_sent and not _vp:
                        _vp = core_tts(_ctx)'''
assert old2 in s, "锚点2未命中"
s = s.replace(old2, new2, 1)

# 初始化 _voice_sent
old3 = '''                    _vp = None   # 每条消息重新算，别沿用上一条的值'''
new3 = '''                    _vp = None   # 每条消息重新算，别沿用上一条的值
                    _voice_sent = False'''
assert old3 in s
s = s.replace(old3, new3, 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已修：语音条成功后再发文件的问题")
