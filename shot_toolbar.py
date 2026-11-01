"""截图并裁出微信输入框工具栏区域，方便定位那颗圆形语音按钮。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import ImageGrab
import voice_ptt as V
import win32gui


def main():
    hwnd, title = V.find_wechat_window()
    if not hwnd:
        print("  没找到微信")
        return 1
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    print("  微信窗口: %s  rect=(%d,%d,%d,%d)  size=%dx%d" % (title, l, t, r, b, r - l, b - t))

    # 整窗截图
    full = ImageGrab.grab(bbox=(l, t, r, b))
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)
    full_path = os.path.join(out_dir, "wx_full.png")
    full.save(full_path)
    print("  整窗截图:", full_path, full.size)

    # 底部工具栏：最后 90 像素高，右侧 45% 宽
    w, h = full.size
    box = (int(w * 0.52), h - 95, w, h - 25)
    crop = full.crop(box)
    crop_path = os.path.join(out_dir, "wx_toolbar.png")
    crop.save(crop_path)
    print("  工具栏截图:", crop_path, crop.size)
    print("  裁剪区域(窗口内):", box)
    print("  换算：整窗坐标 = (裁剪x + %d, 裁剪y + %d)" % (box[0], box[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
