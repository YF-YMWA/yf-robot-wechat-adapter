"""一次性补丁：长时间运行的三个稳定性措施（修正版）。

上一次插错位置：with_window_on_top 是 main() 内部的嵌套函数，
我在它前面插入模块级 def，缩进对不上，直接语法错误。

这次：
  · 模块级辅助函数插在 def main(): 之前（第 991 行前）
  · 熔断检查插在 with_window_on_top 内部（保持 8 空格缩进）
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'SEND_HEALTH' in src:
    print('已打过补丁')
    raise SystemExit(0)

# ---------- 1. 模块级辅助函数 ----------
helpers = '''# ===== 发送健康度（熔断 / 剪贴板保护）=====
SEND_HEALTH = {
    "ok": 0,
    "fail": 0,
    "streak": 0,
    "cooldown": 0.0,
    "last_error": "",
}


def send_allowed():
    """连续失败进入冷却后，就别再折腾微信窗口了。"""
    left = SEND_HEALTH["cooldown"] - time.time()
    if left > 0:
        return False, "连续失败冷却中，还剩 %d 秒" % int(left)
    return True, ""


def note_send_result(ok, err=""):
    """记一次发送结果；连败三次开始冷却，成功满 120 次重建 UIA 缓存。"""
    global SEND_HEALTH
    if ok:
        SEND_HEALTH["ok"] = SEND_HEALTH.get("ok", 0) + 1
        SEND_HEALTH["streak"] = 0
        if SEND_HEALTH["ok"] % 120 == 0:
            try:
                UIA_CACHE["u"] = None
                log("[稳定] 重建 UIA 缓存（累计成功 %d 次）" % SEND_HEALTH["ok"])
            except Exception:
                pass
    else:
        SEND_HEALTH["fail"] = SEND_HEALTH.get("fail", 0) + 1
        SEND_HEALTH["streak"] = SEND_HEALTH.get("streak", 0) + 1
        SEND_HEALTH["last_error"] = str(err)[:120]
        if SEND_HEALTH["streak"] >= 3:
            SEND_HEALTH["cooldown"] = time.time() + 60
            SEND_HEALTH["streak"] = 0
            log("[!] 连续发送失败，冷却 60 秒（%s）" % SEND_HEALTH["last_error"])
            log("    这段时间不点微信窗口了，请检查微信是否掉登录 / 在托盘")


class ClipboardGuard:
    """发图前后保住用户剪贴板。

    发图片必须走 剪贴板 → Ctrl+V，会把你复制的内容冲掉；
    还原一下，顺便减少并发剪贴板抢用导致的崩溃。
    """

    def __init__(self):
        self.text = None
        self.has = False

    def __enter__(self):
        try:
            import win32clipboard as cb

            cb.OpenClipboard()
            try:
                if cb.IsClipboardFormatAvailable(cb.CF_UNICODETEXT):
                    self.text = cb.GetClipboardData(cb.CF_UNICODETEXT)
                    self.has = True
            finally:
                cb.CloseClipboard()
        except Exception:
            pass
        return self

    def __exit__(self, *exc):
        if not self.has or not self.text:
            return False
        try:
            import win32clipboard as cb

            cb.OpenClipboard()
            try:
                cb.EmptyClipboard()
                cb.SetClipboardData(cb.CF_UNICODETEXT, self.text)
            finally:
                cb.CloseClipboard()
        except Exception:
            pass
        return False


UIA_CACHE = {"u": None}


def main():'''

if 'def main():' not in src:
    print('找不到 main()')
    raise SystemExit(1)

src = src.replace('def main():', helpers, 1)

# ---------- 2. 熔断检查插进 with_window_on_top ----------
old_head = '''        if game_running():
            return False
        SEND_STATE["active"] = True'''

new_head = '''        if game_running():
            return False

        # 连续失败冷却中就别试了，免得一直戳微信窗口
        allowed, why = send_allowed()
        if not allowed:
            log("[!] 跳过发送：%s" % why)
            return False

        SEND_STATE["active"] = True'''

if old_head not in src:
    print('没找到 with_window_on_top 里的插入点')
    raise SystemExit(1)

src = src.replace(old_head, new_head, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加：剪贴板保护 + 发送熔断 + UIA 缓存重建')
