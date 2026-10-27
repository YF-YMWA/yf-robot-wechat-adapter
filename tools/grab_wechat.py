"""抓微信窗口截图（处理 DPI 缩放）。

坑：Windows 高分屏有缩放（比如 150%），
win32gui 给的窗口坐标是「逻辑像素」，而屏幕截图是「物理像素」，
直接按 rect 去裁会偏一大截。

这里先声明进程 DPI 感知，坐标就和截图一致了。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'YF-Robot', 'runtime', 'python', 'Lib', 'site-packages'))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'data', 'tmp', 'wechat-window.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # 关键：先声明 DPI 感知，否则坐标和截图对不上
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    import win32gui
    from PIL import ImageGrab

    found = []

    def cb(h, _):
        cls = win32gui.GetClassName(h) or ''
        name = win32gui.GetWindowText(h) or ''
        if cls.startswith('Qt') and name and 'Tray' not in name:
            found.append((h, name, cls))
        return True

    win32gui.EnumWindows(cb, None)
    if not found:
        print('  没找到微信窗口')
        return 1

    hwnd, name, cls = found[0]
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    print('  窗口 %r cls=%s' % (name, cls))
    print('  rect=%s  尺寸 %dx%d' % (rect, right - left, bottom - top))

    if right - left <= 0 or bottom - top <= 0:
        print('  尺寸异常（可能最小化）')
        return 1

    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    img.save(out)
    print('  已保存 %s（%dx%d, %d 字节）' % (out, img.width, img.height, os.path.getsize(out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
