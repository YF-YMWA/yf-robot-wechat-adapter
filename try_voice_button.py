"""实验：按住微信输入框右下角的「语音」按钮，看能不能发语音条。

为什么不用 Alt：微信 4.x 没有 Alt 按住说话。
这个按钮如果是「按住说话」，按住再松开就会发一条语音条（期间微信在录音）。

用法：
  python try_voice_button.py            # 只定位，不按（安全）
  python try_voice_button.py --press    # 按住 1.6 秒再松开（会真的发一条）
  python try_voice_button.py --press --hold 3
"""
import argparse
import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_ptt as V

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def wechat_rect(hwnd):
    import win32gui

    l, t, r, b = win32gui.GetWindowRect(hwnd)
    return l, t, r, b


def find_by_uia():
    """先在控件树里找「语音」按钮，拿它的中心坐标。"""
    try:
        from wechatauto import WeChatGUI

        gui = WeChatGUI()
        # wechatauto 内部通常暴露这些查找能力；用不到就回退到按比例估
        for name in ("语音", "按住 说话", "按住说话", "语音输入"):
            try:
                box = gui.get_input_box()
                if box:
                    break
            except Exception:
                pass
        return None
    except Exception:
        return None


def est_button_point(l, t, r, b):
    """按比例估：输入框右下角「发送」左边那个圆形按钮。"""
    w = r - l
    h = b - t
    # 实测：工具栏在窗口底部往上约 55px，语音按钮在发送键左侧约 70px
    x = l + int(w * 0.905)
    y = b - 55
    return x, y


def press_at(x, y, hold_s=1.6):
    user32.SetCursorPos(x, y)
    time.sleep(0.15)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    t0 = time.time()
    while time.time() - t0 < hold_s:
        time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--press", action="store_true", help="真的按住（会发一条语音）")
    ap.add_argument("--hold", type=float, default=1.6, help="按住秒数")
    ap.add_argument("--x", type=int, default=0, help="手动指定 x")
    ap.add_argument("--y", type=int, default=0, help="手动指定 y")
    args = ap.parse_args()

    hwnd, title = V.find_wechat_window()
    if not hwnd:
        print("  [X] 没找到微信窗口")
        return 1
    print("  微信窗口:", title)

    if not V.focus_window(hwnd):
        print("  [X] 切不到前台（先别按，避免点到别处）")
        return 1
    time.sleep(0.3)

    l, t, r, b = wechat_rect(hwnd)
    print("  窗口区域:", (l, t, r, b), "尺寸:", (r - l, b - t))

    if args.x and args.y:
        x, y = args.x, args.y
    else:
        x, y = est_button_point(l, t, r, b)
    print("  目标点:", (x, y), "（窗口内相对：%d, %d）" % (x - l, y - t))

    if not args.press:
        # 只把鼠标移过去，不发
        user32.SetCursorPos(x, y)
        print("")
        print("  已把鼠标移到该位置（没按）。")
        print("  看着微信窗口：鼠标是否停在那颗圆形语音按钮上？")
        print("  · 是 → 加 --press 再跑一次，会按住 1.6 秒松开")
        print("  · 不是 → 用 --x --y 手动给坐标（鼠标当前位置可用下面命令读）")
        print("      python -c \"import ctypes; p=ctypes.wintypes.POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(p)); print(p.x,p.y)\"")
        return 0

    print("  按住 %.1f 秒…" % args.hold)
    held = press_at(x, y, args.hold)
    print("  已松开（按住 %.1f 秒）" % held)
    time.sleep(0.8)

    # 尝试验证最后一条消息类型
    try:
        from wechatauto import WeChat

        msg = WeChat().GetSubWindow().GetLastMessage()
        kind = type(msg).__name__
        print("  最后一条消息类型:", kind)
        print("  " + ("[OK] 是语音条" if kind == "VoiceMessage" else "[!] 不是语音条（%s）" % kind))
    except Exception as e:
        print("  读不到消息（不影响判断，自己看微信）：%r" % (e,))

    return 0


if __name__ == "__main__":
    sys.exit(main())
