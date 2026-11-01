"""处理「管理员运行 → 微信被挤到后面 → Alt 按到控制台」。

三件事：
  1. 检测自己是不是管理员（管理员进程操作微信窗口容易出问题，wechatauto 也会报
     「完整性级别不一致」）
  2. 发送前把自己的控制台窗口最小化，发完再还原 —— 否则一闪一闪，还抢焦点
  3. 切微信到前台后**必须真的确认**前台是微信，不是就重试，仍失败就不按键
"""
import io

P = "voice_ptt.py"
s = io.open(P, encoding="utf-8").read()

if "def is_admin(" in s:
    print("已存在")
    raise SystemExit(0)

helper = '''
# ---------- 权限 / 控制台窗口 ----------

def is_admin():
    """当前进程是不是管理员。"""
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def console_hwnd():
    """我们自己的控制台窗口句柄（没有返回 0）。"""
    try:
        import ctypes

        return int(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:
        return 0


def minimize_our_console():
    """把控制台最小化，免得它挡住微信、抢焦点。返回是否成功。"""
    import win32con
    import win32gui

    h = console_hwnd()
    if not h:
        return False
    try:
        win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
        time.sleep(0.15)
        return True
    except Exception:
        return False


def restore_our_console():
    import win32con
    import win32gui

    h = console_hwnd()
    if not h:
        return
    try:
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
    except Exception:
        pass


def wechat_elevated(hwnd):
    """微信进程是不是管理员权限（和我们不一致时容易控制失败）。"""
    try:
        import ctypes
        import win32process

        _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not h:
            return None
        try:
            token = ctypes.c_void_p()
            if not ctypes.windll.advapi32.OpenProcessToken(h, 0x0008, ctypes.byref(token)):
                return None
            try:
                size = ctypes.c_ulong(0)
                ctypes.windll.advapi32.GetTokenInformation(token, 20, None, 0, ctypes.byref(size))
                buf = ctypes.create_string_buffer(size.value or 4)
                if not ctypes.windll.advapi32.GetTokenInformation(
                    token, 20, buf, size, ctypes.byref(size)
                ):
                    return None
                # TOKEN_ELEVATION_TYPE: 1=default(UAC 关) 2=full 3=limited
                return int.from_bytes(buf.raw[:4], "little")
            finally:
                ctypes.windll.kernel32.CloseHandle(token)
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return None


def elevation_report():
    """给自检用：说清「谁在管理员下跑」。"""
    adm = is_admin()
    hwnd, _ = find_wechat_window()
    we = wechat_elevated(hwnd) if hwnd else None
    lines = ["  本程序是管理员运行: %s" % ("是" if adm else "否")]
    if hwnd:
        lines.append("  微信是管理员运行: %s" % ("是" if we == 2 else ("否" if we else "查不到")))
    if adm and we != 2:
        lines.append("  ⚠ 不建议用管理员运行：微信不是管理员，权限不一致时键盘/UIA 容易落到别的窗口")
        lines.append("    请直接双击运行（会弹 UAC 就点否），或右键「以当前用户身份运行」")
    return lines

'''

anchor = "# ---------- 找微信窗口 ----------"
if anchor not in s:
    print("找不到锚点")
    raise SystemExit(1)

s = s.replace(anchor, helper + "\n" + anchor, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已加：权限检测 + 控制台最小化")
