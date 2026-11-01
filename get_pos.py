"""抓鼠标坐标：5 秒内把鼠标移到目标上，然后自动打印坐标。

用法：
    python get_pos.py            # 5 秒倒计时
    python get_pos.py 8          # 8 秒
把鼠标移到微信那颗圆形语音按钮上，等它打印即可。
"""
import ctypes
import sys
import time


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def main():
    wait = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print("")
    print("  请把鼠标移到【微信输入框右下角那颗圆形语音按钮】上")
    print("  不要动，倒计时结束后自动读取坐标…")
    for i in range(wait, 0, -1):
        p = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
        print("    %d 秒  当前 (%d, %d)" % (i, p.x, p.y), end="\r")
        time.sleep(1)

    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    print("")
    print("")
    print("  坐标: --x %d --y %d" % (p.x, p.y))
    print("")
    print("  下一步（把坐标复制进这条命令）：")
    print("    python try_voice_button.py --press --x %d --y %d" % (p.x, p.y))
    return 0


if __name__ == "__main__":
    sys.exit(main())
