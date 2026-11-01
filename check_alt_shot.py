"""探针 2：截屏对比，看按住 Alt 时微信界面有没有变化（录音浮层）。

只按 0.6 秒（不到 1 秒微信会判「时间太短」不发消息），不会发出去任何东西。
"""
import sys
import time

sys.path.insert(0, ".")
import voice_ptt as V

from PIL import ImageGrab


def grab(hwnd):
    import win32gui

    l, t, r, b = win32gui.GetWindowRect(hwnd)
    return ImageGrab.grab(bbox=(l, t, r, b))


def diff_score(a, b):
    """返回 0~1 的差异比例（缩到小图再比，快）。"""
    sa = a.resize((160, 100)).convert("L")
    sb = b.resize((160, 100)).convert("L")
    pa, pb = sa.load(), sb.load()
    changed = 0
    for y in range(100):
        for x in range(160):
            if abs(pa[x, y] - pb[x, y]) > 12:
                changed += 1
    return changed / 16000.0


hwnd, title = V.find_wechat_window()
if not hwnd:
    sys.exit("没找到微信")
print("  微信:", title)

if not V.focus_window(hwnd):
    sys.exit("切不到前台")

time.sleep(0.5)
shot0 = grab(hwnd)
print("  截图 1 完成")

# 按一下 Alt（点按，不进录音），看菜单栏是否弹动
V.alt_down()
time.sleep(0.05)
V.alt_up()
time.sleep(0.6)
shot1 = grab(hwnd)
print("  单按 Alt 差异: %.3f" % diff_score(shot0, shot1))

# 按住 0.6 秒
time.sleep(0.4)
V.alt_down()
time.sleep(0.6)
shot2 = grab(hwnd)
V.alt_up()
V.key_up_safe()
time.sleep(0.5)
shot3 = grab(hwnd)
print("  按住 Alt 期间差异: %.3f" % diff_score(shot1, shot2))
print("  松开后差异: %.3f" % diff_score(shot1, shot3))

shot0.save("data_alt0.png")
shot1.save("data_alt1.png")
shot2.save("data_alt2.png")
shot3.save("data_alt3.png")
print("  已存 data_alt0..3.png")
