"""把 voice_ptt.focus_window 换成 AttachThreadInput 那套（单用 SetForegroundWindow 会被系统拒绝）。"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voice_ptt.py")
s = io.open(P, encoding="utf-8").read()

old = '''def focus_window(hwnd):
    """把窗口提到前台。返回是否成功。"""
    import win32con
    import win32gui

    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.15)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return False'''

new = '''def focus_window(hwnd, tries=3):
    """把窗口提到前台。返回是否**真的**到了前台。

    只用 SetForegroundWindow 会被系统静默拒绝（Windows 的前台锁定），
    实测会「以为切过去了，其实键盘还在别的窗口」。这里用
    AttachThreadInput 把自己的输入队列挂到前台线程上再切。
    """
    import ctypes
    import time as _t

    user32 = ctypes.windll.user32

    for _ in range(max(1, tries)):
        try:
            if user32.GetForegroundWindow() == hwnd:
                return True

            fg = user32.GetForegroundWindow()
            tid_fg = user32.GetWindowThreadProcessId(fg, None)
            tid_me = user32.GetWindowThreadProcessId(hwnd, None)

            attached = False
            try:
                if tid_fg and tid_me and tid_fg != tid_me:
                    attached = bool(user32.AttachThreadInput(tid_fg, tid_me, True))
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetFocus(hwnd)
            finally:
                if attached:
                    try:
                        user32.AttachThreadInput(tid_fg, tid_me, False)
                    except Exception:
                        pass

            _t.sleep(0.2)
            if user32.GetForegroundWindow() == hwnd:
                return True
        except Exception:
            pass
    return False'''

if old not in s:
    print("未命中 focus_window")
    raise SystemExit(1)

s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已替换 focus_window（AttachThreadInput）")
