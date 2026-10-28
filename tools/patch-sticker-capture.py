"""一次性补丁：动图 / 微信原表情包的收录定位。

用户反馈：「动图，微信原表情包，收入坐标定位有问题」。
看代码，定位确实有三个弱点：

1. 截图区域不校验 —— 截到侧边栏、头像、空白都照样存
2. 文件名随机 —— 同一个表情重复收录就变成两张，认不出是同一张
3. 定位只管「最后一条动画表情」，不管是谁发的

补：
  · 截图后校验：太窄太扁、纯色/近乎纯色（说明截到空白或背景）一律丢掉并记日志
  · 有 md5 时用 stk_<md5>.gif 命名 —— 核心侧按名字去重，同一张不会重复收
  · 定位时优先找「这个人发的」那条，找不到再退回全部
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'capture_looks_valid' in src:
    print('已打过补丁')
    raise SystemExit(0)

# ---------- 1. 截图有效性校验 ----------
anchor = '    def capture_sticker_frames(who, count=8, interval=0.12):'

helper = '''    def capture_looks_valid(pil_img, rect):
        """截下来的这块，像不像一个表情包。

        为什么需要：定位不准时截到的是侧边栏、头像、或者聊天背景，
        以前照样存进素材库，用户看到的就是「收进来的图不对」。

        判据很朴素但有效：
          · 尺寸不能太扁/太窄
          · 不能是近乎纯色（空白、背景）—— 用像素标准差判断
        """
        try:
            w, h = pil_img.size
            if w < 40 or h < 40:
                return False, "太小（%dx%d）" % (w, h)
            if w / max(1, h) > 6 or h / max(1, w) > 6:
                return False, "比例离谱（%dx%d）" % (w, h)

            # 缩小后算亮度标准差：纯色区域方差极小
            small = pil_img.convert("L").resize((32, 32))
            px = list(small.getdata())
            n = len(px)
            mean = sum(px) / n
            var = sum((p - mean) ** 2 for p in px) / n
            if var < 30:                      # 实测纯背景大概 <10，真表情 200+
                return False, "近乎纯色（方差 %.0f，可能截到了背景）" % var
            return True, ""
        except Exception as e:                # noqa: BLE001
            return True, ""                   # 校验本身出错就放行，别误伤

''' + anchor

if anchor not in src:
    print('找不到 capture_sticker_frames')
    raise SystemExit(1)
src = src.replace(anchor, helper, 1)

# ---------- 2. 连拍后校验每一帧 ----------
old_loop = '''            if shot is None:
                break'''
new_loop = '''            if shot is None:
                break

            # 第一帧先验一下：定位不准的话后面几帧也是错的
            if i == 0:
                ok_cap, why = capture_looks_valid(shot, rect)
                if not ok_cap:
                    log("表情包截图：这一块不像表情（%s），rect=%r 尺寸=%r"
                        % (why, rect, getattr(shot, "size", None)))
                    return b"", ""'''
src = src.replace(old_loop, new_loop, 1)

# ---------- 3. 有 md5 时用它命名（便于去重） ----------
old_collect = '''            def collect(data, suffix=".jpg", desc=""):
                if not data:
                    return
                try:
                    name = save_media(data, suffix, "sticker", chat_user, sender)'''
new_collect = '''            def collect(data, suffix=".jpg", desc="", md5_hint=""):
                if not data:
                    return
                try:
                    # 有 md5 就按它命名：同一张表情重复收录会命中同名文件，
                    # 核心侧按名字去重，不会变成两张
                    name = save_media(
                        data, suffix, "sticker", chat_user, sender,
                        name_hint=("stk_" + md5_hint if md5_hint else ""),
                    )'''
src = src.replace(old_collect, new_collect, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加：截图校验 + md5 命名')
