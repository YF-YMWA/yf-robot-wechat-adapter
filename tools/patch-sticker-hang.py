"""一次性补丁：修「重复收入卡进程」+ GIF 发送卡死。

用户报：
  · 重复收入卡进程（收同一个表情反复走一遍，进程就卡住）
  · 动图发送失败

日志证据（20:37:35 之后完全没动静）：
  hang 转储里主线程停在
    guia.py:2422 _verify_attachment_sent
    ← send_image(verify=True)
  而 DB 工作线程在 db.py:3088 的空等里 —— 校验循环等 DB 永远等不到，进程就挂死。

两处改动：
  1. GIF 发送不再做数据库校验（verify=False）。
     校验本来是「确认真的发出去了」，代价是可能永久卡死；
     卡死的代价比误判大得多，所以改成不校验 + 记日志。
  2. 同一个表情（XML 里带 md5）已经收录过就直接跳过整段截图/连拍。
     以前每收到一次就重新连拍 8 帧 + 识别 + 入库，既慢又重复。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'skip_by_md5' in src:
    print('已打过补丁')
    raise SystemExit(0)

# ---------- 1. GIF 不做数据库校验 ----------
old = '                            return gui.send_image(p, chat_display_name, verify=is_gif)'
new = '''                            # 不做数据库校验：wechatauto 的 _verify_attachment_sent
                            # 在 DB 线程停摆时会无限等待，实测把整个桥接卡死
                            # （20:37 之后一条日志都没有）。误判好过卡死。
                            return gui.send_image(p, chat_display_name, verify=False)'''
if old not in src:
    print('没找到 send_image(verify=...) 调用')
    raise SystemExit(1)
src = src.replace(old, new, 1)

# ---------- 2. 已收录过的表情直接跳过 ----------
anchor = '''            path = _find_sticker_file(md5)'''
helper = '''            # 已经收过这张（同一个 md5）就不要再走一遍截图/连拍/识别 ——
            # 用户反馈「重复收入卡进程」就是这条路：每来一次重拍 8 帧，
            # 全程占着 gui_lock，发送那边就卡住了。
            try:
                _skip_by_md5 = False
                _sdir = os.path.join(ROOT, "data", "stickers")
                if md5 and os.path.isdir(_sdir):
                    for _fn in os.listdir(_sdir):
                        if _fn.startswith("stk_" + md5):
                            _skip_by_md5 = True
                            break
                if _skip_by_md5:
                    log("表情包：这张已经收过（md5=%s），跳过重复收录" % md5[:12])
                    return _sticker_label(content)
            except Exception:
                pass

            path = _find_sticker_file(md5)'''

if anchor not in src:
    print('没找到 _find_sticker_file 调用点')
    raise SystemExit(1)
src = src.replace(anchor, helper, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已改：GIF 不校验 + 重复表情跳过')
