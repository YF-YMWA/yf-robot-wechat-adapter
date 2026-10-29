"""适配器加两个可诊断性改进：
  1. 操作面包屑：每次高风险 UIA 操作前写 data/last-op.txt
  2. 心跳带上今日崩溃次数，面板能看出适配器不稳定
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')
src = io.open(P, encoding='utf-8').read()

if 'record_last_op' in src:
    print('已打过补丁')
    raise SystemExit(0)

# ---------- 1. 面包屑 ----------
anchor = 'def core_pick_sticker(text="", only_gif=False):'
helper = '''def record_last_op(name):
    """记下「正在做哪个高风险操作」。

    为什么要这个：python 的 0xC0000005（访问冲突）发生在 CPython/COM 内部，
    Python 层抓不住，进程直接消失 —— 事后完全不知道死在哪个 UIA 调用上。
    这里在调用前把操作名和时间戳写进 data/last-op.txt，
    下次启动时读出来，就能定位到具体是哪一步崩的（成本几乎为零）。
    """
    try:
        import time as _t

        d = os.path.join(ROOT, "data")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "last-op.txt"), "w", encoding="utf-8") as f:
            f.write("%s\\t%s\\n" % (_t.strftime("%Y-%m-%d %H:%M:%S"), name))
    except Exception:
        pass


def read_prev_op():
    """读上一次崩溃前正在做什么（没有就是空串）。"""
    try:
        p = os.path.join(ROOT, "data", "last-op.txt")
        if not os.path.exists(p):
            return ""
        with open(p, encoding="utf-8") as f:
            return (f.read() or "").strip()
    except Exception:
        return ""


def core_pick_sticker(text="", only_gif=False):'''

if anchor not in src:
    print('找不到 core_pick_sticker')
    raise SystemExit(1)
src = src.replace(anchor, helper, 1)

# ---------- 2. 在关键 UIA 操作前埋点 ----------
marks = [
    ('            r = _do_send(path)', '发图（剪贴板粘贴）'),
    ('                path = resolve_media_path(path) or path', '解析图片路径'),
    ('            hwnd = find_weixin_hwnd()', '枚举微信窗口'),
]

for needle, label in marks:
    if needle in src:
        indent = needle[: len(needle) - len(needle.lstrip())]
        src = src.replace(
            needle,
            indent + 'record_last_op("%s")\n' % label + needle,
            1,
        )

# ---------- 3. 心跳带崩溃次数 ----------
old_hb = '''                    "send": {
                        "ok": SEND_HEALTH.get("ok", 0),'''
new_hb = '''                    # 今日崩溃次数：让面板能直接看出「适配器不稳定」
                    "crashes": count_today_crashes(),
                    "send": {
                        "ok": SEND_HEALTH.get("ok", 0),'''
if old_hb not in src:
    print('找不到心跳 send 字段')
    raise SystemExit(1)
src = src.replace(old_hb, new_hb, 1)

helper2 = '''def count_today_crashes():
    """数今天 bridge-crash.log 里出现了几次崩溃转储。

    watchdog 转储的格式里带日期（fault handler 头），所以按今天的日期串数出现次数。
    """
    try:
        import time as _t

        p = os.path.join(ROOT, "data", "bridge-crash.log")
        if not os.path.exists(p):
            return 0
        # 只看最近 200KB，避免日志很大时每次都全读
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            if size > 200 * 1024:
                f.seek(size - 200 * 1024)
            text = f.read().decode("utf-8", "ignore")
        today = _t.strftime("%Y-%m-%d")
        return text.count("Fatal Python error") + text.count(today + " ")
    except Exception:
        return 0


def record_last_op(name):'''

src = src.replace('def record_last_op(name):', helper2, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加：操作面包屑 + 崩溃次数')
