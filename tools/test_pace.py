"""验证 bubble_pause 的停顿是否合理。

跑法：在适配器目录下 python tools/test_pace.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wechatauto_bridge as b


def main():
    print('  参数：基准 %.0fms，每字 %.0fms，抖动 %.0f%%，上限 %.0fms'
          % (b.PACE_BUBBLE_MS, b.PACE_PER_CHAR_MS, b.PACE_JITTER * 100, b.PACE_MAX_MS))
    print('')

    cases = [
        ('在。', 2),
        ('写代码查资料都行，干完活给碗白米饭就成。', 20),
        ('（挪了挪）你要是拿这种题试探我，那我这碗饭是不是有点太亏了。', 31),
        ('很长的一段话' * 30, 180),
    ]

    ok = True
    for text, n in cases:
        vals = [b.bubble_pause(text) for _ in range(200)]
        lo, hi = min(vals), max(vals)
        avg = sum(vals) / len(vals)
        print('  %-3d 字 → 平均 %.2fs（范围 %.2f~%.2fs）' % (n, avg, lo, hi))

        # 短消息不能等太久
        if n <= 5 and avg > 2.0:
            print('    ✗ 短消息等太久了')
            ok = False
        # 长消息不能超过上限
        if hi > b.PACE_MAX_MS / 1000.0 + 0.01:
            print('    ✗ 超过上限')
            ok = False
        # 必须有抖动（不是固定值）
        if abs(hi - lo) < 0.05:
            print('    ✗ 没有抖动，节奏太机械')
            ok = False

    print('')
    print('  ' + ('✓ 全部正常' if ok else '✗ 有问题'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
