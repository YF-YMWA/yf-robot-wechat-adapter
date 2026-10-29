"""一次性补丁：微信多开时防止「串号」。

典型事故：
  微信双开（大号 + 小号）时，读的是小号的库，发却发到了大号的窗口 ——
  「用大号把话发出去」，而且两边没有任何一致性校验。

我们的现状：find_weixin_hwnd() 按「标题=微信 / 主窗类名 / 最小化按钮 / 面积」
打分挑一个窗口。双开时两个窗口分数接近，可能挑错 —— 而库是按当前登录账号读的。

做法（保守，不猜）：
  · 数一下有几个「像主窗」的窗口
  · 多于一个 → 记一条明确警告，并在发送前拒绝（config 可关）
  · 只警告不阻止的话，用户会以为发出去了，其实发到另一个号 —— 更糟

配置：wechat.refuseOnMultiAccount（默认 true）
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'count_weixin_main_windows' in src:
    print('已打过补丁')
    raise SystemExit(0)

# 1. 加一个「数主窗」的函数（放在 find_weixin_hwnd 前面）
anchor = '    def find_weixin_hwnd():'

helper = '''    def count_weixin_main_windows():
        """数一下有几个「像微信主窗」的窗口。

        双开时会 ≥2。用它防串号：读的是这个号的库，绝不能发到另一个号的窗口。
        """
        try:
            import win32gui
            import win32process
            import psutil
        except Exception:
            return -1

        BAD_CLASS = ("trayicon", "messagewindow", "msctf", "sopy", "sogou", "hintwnd", "default ime", "notifyicon")
        found = []

        def cb(h, _):
            try:
                title = (win32gui.GetWindowText(h) or "").strip()
                cls = (win32gui.GetClassName(h) or "").lower()
                if any(b in cls for b in BAD_CLASS):
                    return
                if "发送" in title or "助手" in title:
                    return
                _, pid = win32process.GetWindowThreadProcessId(h)
                if pid <= 0:
                    return
                try:
                    if not psutil.Process(pid).name().lower().startswith("weixin"):
                        return
                except Exception:
                    return
                rect = win32gui.GetWindowRect(h)
                area = max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])
                if area < 300 * 250 and title != "微信":
                    return
                looks_main = title == "微信" or "qwindowicon" in cls or "mmui::mainwindow" in cls
                if looks_main:
                    found.append(h)
            except Exception:
                pass

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            return -1
        return len(found)

    def multi_account_guard():
        """多开时拒绝发送。返回 (ok, 原因)。"""
        try:
            n = count_weixin_main_windows()
        except Exception:
            return True, ""
        if n <= 1:
            return True, ""
        msg = "检测到 %d 个微信主窗（多开）：为了不把话发到别的号，这次不发送" % n
        log("[!] " + msg)
        log("    要允许发送：在 config.json 里设 wechat.refuseOnMultiAccount = false")
        return False, msg

    def find_weixin_hwnd():'''

if anchor not in src:
    print('找不到 find_weixin_hwnd')
    raise SystemExit(1)
src = src.replace(anchor, helper, 1)

# 2. 发送前过一道闸（在 send_text 的入口处）
old_guard = '''    def send_text(text, chat_display_name, chat_username="", force=False, quote_text=None):
        nonlocal gui'''
new_guard = '''    def send_text(text, chat_display_name, chat_username="", force=False, quote_text=None):
        nonlocal gui

        # 多开防串号：宁可这次不发，也别发到另一个号上
        if REFUSE_ON_MULTI_ACCOUNT:
            ok_multi, why = multi_account_guard()
            if not ok_multi:
                return False'''

if old_guard not in src:
    print('找不到 send_text 入口')
    raise SystemExit(1)
src = src.replace(old_guard, new_guard, 1)

# 3. 配置项默认值 + 热更新
src = src.replace(
    'KEYBOARD_FALLBACK = True',
    '''# 微信多开时是否拒绝发送（防串号，见 count_weixin_main_windows）
REFUSE_ON_MULTI_ACCOUNT = bool(
    # 默认开：发错号比不发严重得多
    True
)
KEYBOARD_FALLBACK = True''',
    1,
)

src = src.replace(
    '    KEYBOARD_FALLBACK = bool(_wechat.get("keyboardFallback", True))',
    '''    KEYBOARD_FALLBACK = bool(_wechat.get("keyboardFallback", True))
    global REFUSE_ON_MULTI_ACCOUNT
    REFUSE_ON_MULTI_ACCOUNT = bool(_wechat.get("refuseOnMultiAccount", True))''',
    1,
)

src = src.replace(
    '    KEYBOARD_FALLBACK = bool(w.get("keyboardFallback", True))',
    '''    KEYBOARD_FALLBACK = bool(w.get("keyboardFallback", True))
    REFUSE_ON_MULTI_ACCOUNT = bool(w.get("refuseOnMultiAccount", True))''',
    1,
)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加多开防串号')
