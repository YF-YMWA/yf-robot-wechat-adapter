"""发送流程里加入：最小化控制台 → 切微信 → 确认前台 → 发完还原。"""
import io

P = "voice_send.py"
s = io.open(P, encoding="utf-8").read()

if "minimize_our_console" in s:
    print("已存在")
    raise SystemExit(0)

# 1. open_chat_and_focus 里：先把我们自己的控制台让开
old = '''    gui = _gui()
    try:
        if not gui.is_alive():
            return False, "微信窗口不在了"
        gui.bring_to_front()
        time.sleep(0.3)'''

new = '''    gui = _gui()
    try:
        if not gui.is_alive():
            return False, "微信窗口不在了"

        # 管理员运行/命令行窗口在前时，微信会被挤到后面，Alt 就按到控制台里去了。
        # 发送期间先把自己的控制台收起来，发完再还回来。
        V.minimize_our_console()

        gui.bring_to_front()
        time.sleep(0.3)'''

assert old in s
s = s.replace(old, new, 1)

# 2. 按 Alt 前再确认一次前台；失败就重试，仍失败就放弃（不盲按）
old2 = '''    hwnd, title = V.find_wechat_window()
    if not hwnd:
        return {"ok": False, "error": "找不到微信窗口", "steps": steps}
    if not V.foreground_is(hwnd):
        return {"ok": False, "error": "微信不在前台，拒绝盲按键", "steps": steps}'''

new2 = '''    hwnd, title = V.find_wechat_window()
    if not hwnd:
        return {"ok": False, "error": "找不到微信窗口", "steps": steps}

    # 再抢一次前台（管理员运行时系统会拒绝普通请求，这里用 AttachThreadInput 重试）
    ok_fg = False
    for attempt in range(3):
        if V.foreground_is(hwnd):
            ok_fg = True
            break
        V.focus_window(hwnd, tries=1)
        time.sleep(0.25)
    if not ok_fg:
        V.restore_our_console()
        tip = ""
        if V.is_admin():
            tip = "（你现在是用管理员运行的，微信不是管理员，权限不一致时切前台会被拒绝 —— 请改成普通双击运行）"
        return {
            "ok": False,
            "error": "微信不在前台，拒绝盲按键" + tip,
            "steps": steps,
        }
    steps.append("已确认微信在前台")'''

assert old2 in s
s = s.replace(old2, new2, 1)

# 3. 结束/异常时还原控制台
s = s.replace(
    '''    finally:
        V.key_up_safe()''',
    '''    finally:
        V.key_up_safe()
        V.restore_our_console()''',
    1,
)

# 4. 成功路径也还原
s = s.replace(
    '''    # 4. 验证：最后一条是不是语音
    time.sleep(1.0)''',
    '''    V.restore_our_console()

    # 4. 验证：最后一条是不是语音
    time.sleep(1.0)''',
    1,
)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已接入：最小化控制台 + 前台重试 + 还原")
