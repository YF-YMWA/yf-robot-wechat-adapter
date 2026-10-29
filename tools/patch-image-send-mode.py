"""发图崩溃的规避：粘贴方式不稳时自动改用文件方式发。

证据（面包屑）：
  [诊断] 今天已崩溃 10 次；上次崩溃前正在做：17:09:30  发图（剪贴板粘贴）

0xC0000005 发生在 CPython/COM 内部，Python 抓不住；每次发图崩一次进程，
用户看到的就是「卡在发那一刻」，消息永远发不出去。

做法：
  · 新增 wechat.imageSendMode: auto | paste | file（默认 auto）
  · auto：今天已因「发图」崩过 2 次以上 → 自动改为按文件发（send_file）
  · paste：老行为；file：永远按文件发
按文件发对方点开能看到图/动图，只是不是「内联图片」——但至少发得出去。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'image_send_mode' in src:
    print('已打过补丁')
    raise SystemExit(0)

# 1. 配置项
old_cfg = 'KEYBOARD_FALLBACK = True'
new_cfg = '''# 发图方式：auto / paste / file
#   paste = 剪贴板粘贴（微信里是内联图片，但实测会 0xC0000005 崩进程）
#   file  = 当文件发（稳，对方点开能看）
#   auto  = 今天因发图崩过 ≥2 次就自动切 file
IMAGE_SEND_MODE = "auto"
KEYBOARD_FALLBACK = True'''

if old_cfg not in src:
    print('找不到配置锚点')
    raise SystemExit(1)
src = src.replace(old_cfg, new_cfg, 1)

# 2. reload 时读配置
src = src.replace(
    '    KEYBOARD_FALLBACK = bool(_wechat.get("keyboardFallback", True))',
    '''    KEYBOARD_FALLBACK = bool(_wechat.get("keyboardFallback", True))
    IMAGE_SEND_MODE = str(_wechat.get("imageSendMode") or "auto").lower()''',
    1,
)

# 3. 发图前决定用哪条路
old_send = '''            SEND_STATE["active"] = True
            SEND_STATE["start"] = time.time()
            record_last_op("发图（剪贴板粘贴）")
            try:
                r = _do_send(path)
            finally:
                SEND_STATE["active"] = False'''

new_send = '''            def _use_file_mode():
                """这次该不该绕过粘贴、直接按文件发。"""
                mode = str(IMAGE_SEND_MODE or "auto").lower()
                if mode == "file":
                    return True, "配置指定按文件发"
                if mode == "paste":
                    return False, "配置指定用粘贴"
                # auto：看今天的崩溃记录
                try:
                    crashes = count_today_crashes()
                    prev = read_prev_op()
                except Exception:
                    return False, ""
                if crashes >= 2 and "发图" in prev:
                    return True, "今天因发图崩过 %d 次，自动改为按文件发" % crashes
                return False, ""

            _file_mode, _why = _use_file_mode()
            if _file_mode:
                log("[表情包] %s：%s" % (_why, "按文件发送（微信里点开可见）"))
                SEND_STATE["active"] = True
                SEND_STATE["start"] = time.time()
                record_last_op("发图（按文件）")
                try:
                    r = gui.send_file(path, chat_display_name)
                except Exception as e:               # noqa: BLE001
                    log("按文件发也失败：", repr(e))
                    r = None
                finally:
                    SEND_STATE["active"] = False
            else:
                SEND_STATE["active"] = True
                SEND_STATE["start"] = time.time()
                record_last_op("发图（剪贴板粘贴）")
                try:
                    r = _do_send(path)
                finally:
                    SEND_STATE["active"] = False'''

if old_send not in src:
    print('找不到发图块')
    raise SystemExit(1)
src = src.replace(old_send, new_send, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加：发图自动改用文件方式')
