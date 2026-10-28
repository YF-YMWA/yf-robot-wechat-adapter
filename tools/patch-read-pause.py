"""一次性补丁：发第一条之前先「看一眼消息」再回。

真人不会秒回，尤其消息长的时候 —— 要先读。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

# 1. 加一个算「读消息」时间的函数
if 'def read_pause(' not in src:
    anchor = 'def bubble_pause(text):'
    helper = '''def read_pause(text):
    """回第一条之前「读一遍」要多久（秒）。

    真人看到消息不会立刻回，要先看完、想一下再动手。
    消息越长，读得越久；但封顶 2.5 秒，别让人等太久。
    """
    import random

    n = len(str(text or ""))
    base = 0.6 + min(n * 0.012, 1.6)      # 短消息约 0.6s，长消息最多 2.2s
    return max(0.3, base * random.uniform(0.75, 1.25))


def bubble_pause(text):'''
    src = src.replace(anchor, helper, 1)
    print('  已加 read_pause')

# 2. 发第一条之前先等
old = '''            first = True
            for line in bubbles:'''
new = '''            # 发第一条之前先「读一遍」——真人不会秒回
            try:
                _said = data.get("reply") or " ".join(str(b) for b in bubbles[:2])
                time.sleep(read_pause(_said))
            except Exception:
                pass

            first = True
            for line in bubbles:'''
if old in src:
    src = src.replace(old, new, 1)
    print('  已加读消息延迟')

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('完成')
