"""按 Alt 之前，用真实鼠标点一下输入框。

日志证据：
  uia_compat: 点击了 'YF' 但 current_chat=None，回退搜索框
  guia: 输入框探测连续失败，自动重新校准布局

也就是说 UIA 切聊天失败后，焦点留在**搜索框**里，
于是按住右 Alt 只被搜索框吃掉，微信不会进入录音。
用户手动按右 Alt 能出气泡条，就是因为他的焦点在输入框里。

做法：按比例算出输入框位置（右侧聊天区、底部往上一点），
用真实鼠标点一下，让焦点回到输入框，再按 Alt。
"""
import time

import voice_ptt as V


def click_input_box(hwnd, log=print):
    """在微信输入框里点一下。返回点击坐标或 None。"""
    import ctypes
    import win32gui

    user32 = ctypes.windll.user32
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    w = r - l
    h = b - t

    # 会话列表约占左侧 28%，输入框在右侧区域的下半部分
    x = l + int(w * 0.62)
    y = b - int(h * 0.18)
    user32.SetCursorPos(x, y)
    time.sleep(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)   # left down
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)   # left up
    time.sleep(0.25)
    log("[语音] 已点击输入框 (%d,%d) 让焦点回到消息输入" % (x, y))
    return x, y
