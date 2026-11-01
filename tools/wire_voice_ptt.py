"""把「按住 Alt 发语音条」接进 bridge 的语音发送分支。

行为：
  wechat.voiceMode = "file"（默认）→ 还是当文件发（老行为）
  wechat.voiceMode = "ptt"        → 走 voice_send.send_voice 发真语音条；
                                    失败自动回退成发文件，不让回复丢
  wechat.voiceOutDevice           → 播到哪个播放设备（默认 -1 系统默认）
"""
import io
import os
import re

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if 'VOICE_MODE = "file"' in s:
    print("已改过")
    raise SystemExit(0)

# 1. 配置读取：加在 VOICE_CHANCE 附近
old_cfg = 'VOICE_CHANCE = float(os.environ.get("WHALE_VOICE_CHANCE", "0"))'
new_cfg = '''VOICE_CHANCE = float(os.environ.get("WHALE_VOICE_CHANCE", "0"))

# 语音怎么发：file = 当文件发（稳，但不显示成语音条）；
#             ptt  = 按住 Alt 录一条真语音（需要声音能进微信麦克风，见 docs/VOICE.md）
VOICE_MODE = "file"
VOICE_OUT_DEVICE = -1'''
assert old_cfg in s
s = s.replace(old_cfg, new_cfg, 1)

# 2. 从配置/policy 里读
old_apply = '''        if isinstance(j.get("voiceChance"), (int, float)):
            VOICE_CHANCE = max(0.0, min(1.0, float(j["voiceChance"])))'''
new_apply = '''        if isinstance(j.get("voiceChance"), (int, float)):
            VOICE_CHANCE = max(0.0, min(1.0, float(j["voiceChance"])))

        if j.get("voiceMode") in ("file", "ptt"):
            VOICE_MODE = j["voiceMode"]
        if isinstance(j.get("voiceOutDevice"), (int, float)):
            VOICE_OUT_DEVICE = int(j["voiceOutDevice"])'''
assert old_apply in s
s = s.replace(old_apply, new_apply, 1)

# global 声明补上
m = re.search(r"(def pull_policy\(\s*\):[\s\S]{0,400}?global )([^\n]*)", s)
if m and "VOICE_MODE" not in m.group(2):
    s = s[: m.end(2)] + ", VOICE_MODE, VOICE_OUT_DEVICE" + s[m.end(2):]

# 3. 发送分支：ptt 优先
old_send = '''                    _vp = core_tts(_ctx)
                    if _vp:
                        time.sleep(0.8)
                        # gui 可能还没建（纯文本回复不会建），这里自己兜一下。
                        # 用局部变量，不改外层 gui，避免作用域问题。
                        _g = gui if gui is not None else WeChatGUI()
                        _r = _g.send_file(_vp, who=target, verify=False)
                        _okv = getattr(_r, "success", None)
                        if _okv is None:
                            _okv = bool(_r)
                        log("[语音] 发送结果：%s" % ("成功" if _okv else "失败"))'''

new_send = '''                    if VOICE_MODE == "ptt":
                        # 发真语音条：按住 Alt 说话，把合成的声音送进麦克风
                        try:
                            import voice_send as _vs

                            _res = _vs.send_voice(
                                _ctx,
                                chat=target,
                                tts_fn=core_tts,
                                out_device=(VOICE_OUT_DEVICE if VOICE_OUT_DEVICE >= 0 else None),
                                log=log,
                            )
                            if _res.get("ok"):
                                log("[语音] 已发语音条（按住 %.1fs，验证=%s）"
                                    % (_res.get("seconds") or 0, _res.get("verified")))
                                _vp = ""   # 已经发过了，别再当文件发一遍
                            else:
                                log("[语音] 发语音条失败：%s → 回退当文件发" % _res.get("error"))
                        except Exception as _ve:          # noqa: BLE001
                            log("[语音] 发语音条异常：%r → 回退当文件发" % (_ve,))

                    _vp = core_tts(_ctx) if not locals().get("_vp") else _vp
                    if _vp:
                        time.sleep(0.8)
                        # gui 可能还没建（纯文本回复不会建），这里自己兜一下。
                        # 用局部变量，不改外层 gui，避免作用域问题。
                        _g = gui if gui is not None else WeChatGUI()
                        _r = _g.send_file(_vp, who=target, verify=False)
                        _okv = getattr(_r, "success", None)
                        if _okv is None:
                            _okv = bool(_r)
                        log("[语音] 发送结果：%s" % ("成功" if _okv else "失败"))'''

assert old_send in s
s = s.replace(old_send, new_send, 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已接入：voiceMode=ptt 时发真语音条（失败回退文件）")
