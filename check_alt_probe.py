"""探针：在微信里按住 Alt 0.6 秒，看有没有出现「录音中」的界面。

0.6 秒不到 1 秒，微信会判「说话时间太短」不发消息 —— 所以这个探针是安全的。
只做观察，不发任何消息。
"""
import sys
import time

sys.path.insert(0, ".")
import voice_ptt as V


def windows_now():
    import win32gui

    out = {}
    def _cb(h, _):
        out[h] = win32gui.GetWindowText(h)
        return True

    win32gui.EnumWindows(_cb, None)
    return out


def visible_set():
    import win32gui

    s = set()
    def _cb2(h, _):
        if win32gui.IsWindowVisible(h):
            s.add(h)
        return True

    win32gui.EnumWindows(_cb2, None)
    return s


hwnd, title = V.find_wechat_window()
print("  微信窗口: %s (hwnd=%s)" % (title, hwnd))
if not hwnd:
    sys.exit("  没找到微信")

print("  切到前台…")
ok = V.focus_window(hwnd)
print("  前台成功:", ok)
if not ok:
    sys.exit("  没法切前台，放弃（不盲按）")

before = visible_set()
names_before = windows_now()

print("  按住 Alt 0.6s …")
try:
    V.alt_down()
    time.sleep(0.6)
    V.alt_up()
finally:
    V.key_up_safe()

time.sleep(0.6)
after = visible_set()
new = after - before

print("  新增可见窗口:", len(new))
for h in list(new)[:8]:
    try:
        import win32gui

        print("    hwnd=%s title=%r class=%r" % (h, win32gui.GetWindowText(h), win32gui.GetClassName(h)))
    except Exception:
        pass

# 微信主窗口内部的子控件变化（录音浮层可能是子窗口）
import win32gui

children = []


def cb(h, _):
    children.append(h)
    return True


try:
    win32gui.EnumChildWindows(hwnd, cb, None)
except Exception:
    pass
print("  微信主窗口子控件数:", len(children))
