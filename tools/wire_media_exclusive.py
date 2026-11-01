"""媒体互斥：有语音就不发文字；语音和图片不同时发。

用户要求：
  · 有语音无文字，别一起发
  · 图片可以联动，但和文字/语音的联动要优化

配置（适配器 config.json → wechat）：
  voiceOnly          有语音时不再发文字气泡（默认 false）
  mediaExclusive     一条回复只发一种主媒体（语音/图片二选一，默认 true）
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if "VOICE_ONLY" in s:
    print("已接入")
    raise SystemExit(0)

# 1. 配置项
old = '''    _vod = _w2.get("voiceOutDevice")
    if isinstance(_vod, int):
        VOICE_OUT_DEVICE = _vod'''
new = '''    _vod = _w2.get("voiceOutDevice")
    if isinstance(_vod, int):
        VOICE_OUT_DEVICE = _vod
    # 有语音就不发文字 / 语音和图片不同时发
    VOICE_ONLY = bool(_w2.get("voiceOnly", False))
    MEDIA_EXCLUSIVE = bool(_w2.get("mediaExclusive", True))'''
assert old in s
s = s.replace(old, new, 1)

# 2. 默认值（放在 VOICE_OUT_DEVICE 定义旁边）
s = s.replace(
    'VOICE_OUT_DEVICE = -1',
    'VOICE_OUT_DEVICE = -1\n\n# 有语音时不发文字；语音与图片互斥（一条回复只发一种主媒体）\nVOICE_ONLY = False\nMEDIA_EXCLUSIVE = True',
    1,
)

# 3. 先把「要不要发语音」定下来（原来是在发完文字、图片之后才算）
old2 = '''            log("回复", ("群" if is_group else "私聊"), target, "→", nickname, "：", (bubbles[0] or "")[:40])'''
new2 = '''            log("回复", ("群" if is_group else "私聊"), target, "→", nickname, "：", (bubbles[0] or "")[:40])

            # === 先决定这条要不要发语音，再决定文字/图片要不要发 ===
            # 以前语音是在文字和图片都发完之后才判断，结果「语音+文字」一起出现。
            _voice_text = ""
            try:
                _vs_spec = data.get("voice")
                if isinstance(_vs_spec, dict):
                    _voice_text = str(_vs_spec.get("text") or "").strip()
                elif isinstance(_vs_spec, str):
                    _voice_text = _vs_spec.strip()
                if not _voice_text and VOICE_CHANCE > 0 and random.random() < VOICE_CHANCE:
                    _voice_text = " ".join(str(b) for b in (data.get("bubbles") or []))[:200]
            except Exception:
                _voice_text = ""

            _will_voice = bool(_voice_text)
            # 陌生人不给语音
            if _will_voice and not _is_owner:
                try:
                    import stranger_limit as _slv

                    if not _slv.allow_voice(username, _cfg):
                        log("[陌生人] 不给 %s 发语音（设置里关了）" % target)
                        _will_voice = False
                        _voice_text = ""
                except Exception:
                    pass

            _skip_text = _will_voice and VOICE_ONLY
            _skip_images = _will_voice and MEDIA_EXCLUSIVE
            if _skip_text:
                log("[媒体] 这条只发语音，不发文字")'''

assert old2 in s
s = s.replace(old2, new2, 1)

# 4. 文字循环里跳过
old3 = '''            first = True
            for line in bubbles:
                if not line:
                    continue'''
new3 = '''            first = True
            for line in bubbles:
                if _skip_text:
                    break
                if not line:
                    continue'''
assert old3 in s
s = s.replace(old3, new3, 1)

# 5. 图片：互斥时跳过
old4 = '''                _imgs = data.get("images") or []
                if isinstance(_imgs, str):
                    _imgs = [_imgs]'''
new4 = '''                _imgs = data.get("images") or []
                if isinstance(_imgs, str):
                    _imgs = [_imgs]
                if _skip_images:
                    if _imgs:
                        log("[媒体] 这条发语音，就不发图了（%d 张）" % len(_imgs))
                    _imgs = []'''
assert old4 in s
s = s.replace(old4, new4, 1)

# 6. 后面的语音块复用已算好的 _voice_text（不再重新抽一次概率）
old5 = '''                if not _voice_text and VOICE_CHANCE > 0 and random.random() < VOICE_CHANCE:
                    # 兼容老核心：没有 voice 字段时沿用原来的做法
                    _voice_text = " ".join(str(b) for b in (data.get("bubbles") or []))[:200]

                if _voice_text:'''
new5 = '''                if _voice_text:'''
assert old5 in s
s = s.replace(old5, new5, 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已接入：语音优先 + 媒体互斥")
