"""尝试点击微信的麦克风按钮，观察界面变化。

安全说明：只是切换输入模式（文字 <-> 语音），
**不会**按住录音、不会发消息。点一次切过去，截图，再点一次切回来。

用法：python try_voice_mode.py
"""
import os
import sys
import time
import ctypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'YF-Robot', 'runtime', 'python', 'Lib', 'site-packages'))

# 先声明 DPI 感知，坐标才和截图一致
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import win32gui
import win32con
import win32api
from PIL import ImageGrab

# 麦克风图标在窗口内的相对位置（从截图量出来的）
MIC_REL = (745, 792)


def find_window():
    found = []

    def cb(h, _):
        cls = win32gui.GetClassName(h) or ''
        name = win32gui.GetWindowText(h) or ''
        if cls.startswith('Qt') and name and 'Tray' not in name:
            found.append((h, name))
        return True

    win32gui.EnumWindows(cb, None)
    return found[0] if found else (None, None)


def shot(hwnd, path):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    img.save(path)
    return img.size


def click(x, y):
    """真实鼠标点击（SendInput 级别），微信能收到。"""
    win32api.SetCursorPos((x, y))
    time.sleep(0.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def main():
    hwnd, name = find_window()
    if not hwnd:
        print('  没找到微信窗口')
        return 1

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print('  切前台失败：', e)
    time.sleep(0.8)

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    print('  窗口 %r rect=%s' % (name, (left, top, right, bottom)))

    x, y = left + MIC_REL[0], top + MIC_REL[1]
    print('  麦克风图标屏幕坐标: (%d, %d)' % (x, y))

    os.makedirs(os.path.join(HERE, '..', 'data', 'tmp'), exist_ok=True)
    before = os.path.join(HERE, '..', 'data', 'tmp', 'voice-before.png')
    after = os.path.join(HERE, '..', 'data', 'tmp', 'voice-after.png')
    back = os.path.join(HERE, '..', 'data', 'tmp', 'voice-back.png')

    print('  截点击前…')
    print('   ', shot(hwnd, before))

    print('  点击麦克风…')
    click(x, y)
    time.sleep(1.2)
    print('  截点击后…')
    print('   ', shot(hwnd, after))

    # 再点一次切回文字模式（避免一直停在语音模式）
    print('  再点一次切回…')
    click(x, y)
    time.sleep(1.0)
    print('   ', shot(hwnd, back))

    print('')
    print('  生成三张图供对比：')
    print('    before:', before)
    print('    after :', after)
    print('    back  :', back)
    return 0


if __name__ == '__main__':
    sys.exit(main())
