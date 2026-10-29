"""发图崩溃改成按天计数，判断更可靠。

问题：last-op.txt 只有一个槽位，启动时的「枚举微信窗口」会把它覆盖掉，
于是 auto 模式永远判断不出「上次是发图崩的」。
做法：启动时如果发现上次是发图崩的，就累加 data/image-crash.json 里的当日计数，
auto 模式看这个计数（≥2 天当日就改按文件发）。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')
src = io.open(P, encoding='utf-8').read()

if 'bump_image_crash' in src:
    print('已打过补丁')
    raise SystemExit(0)

# 1. 新增计数函数（放在 count_today_crashes 前面）
anchor = 'def count_today_crashes():'
helper = '''def image_crash_count():
    """今天因为「发图」崩了几次。"""
    try:
        import json as _json

        p = os.path.join(ROOT, "data", "image-crash.json")
        if not os.path.exists(p):
            return 0
        with open(p, encoding="utf-8") as f:
            j = _json.load(f)
        today = time.strftime("%Y-%m-%d")
        return int(j.get(today) or 0)
    except Exception:
        return 0


def bump_image_crash(prev_op):
    """上次是发图崩的就 +1，并写回当天计数。"""
    try:
        import json as _json

        if "发图" not in str(prev_op or ""):
            return 0

        p = os.path.join(ROOT, "data", "image-crash.json")
        j = {}
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    j = _json.load(f) or {}
            except Exception:
                j = {}
        today = time.strftime("%Y-%m-%d")
        j = {today: int(j.get(today) or 0) + 1}      # 只留今天，不无限增长
        with open(p, "w", encoding="utf-8") as f:
            _json.dump(j, f)
        return j[today]
    except Exception:
        return 0


def count_today_crashes():'''

if anchor not in src:
    print('找不到 count_today_crashes')
    raise SystemExit(1)
src = src.replace(anchor, helper, 1)

# 2. 启动诊断处累加
old_diag = '''    if _crashes_today:
        log("[诊断] 今天已崩溃 %d 次；上次崩溃前正在做：%s" % (
            _crashes_today, _prev or "（没有记录）"))'''
new_diag = '''    if _crashes_today:
        _img_crashes = bump_image_crash(_prev)
        log("[诊断] 今天已崩溃 %d 次；上次崩溃前正在做：%s%s" % (
            _crashes_today,
            _prev or "（没有记录）",
            ("（发图崩溃 %d 次，本次起按文件发）" % _img_crashes) if _img_crashes else "",
        ))'''

if old_diag not in src:
    print('找不到启动诊断')
    raise SystemExit(1)
src = src.replace(old_diag, new_diag, 1)

# 3. auto 判断改用计数
src = src.replace(
    '''                try:
                    crashes = count_today_crashes()
                    prev = read_prev_op()
                except Exception:
                    return False, ""
                if crashes >= 2 and "发图" in prev:
                    return True, "今天因发图崩过 %d 次，自动改为按文件发" % crashes
                return False, ""''',
    '''                try:
                    n = image_crash_count()
                except Exception:
                    return False, ""
                if n >= 2:
                    return True, "今天发图崩过 %d 次，自动改为按文件发" % n
                return False, ""''',
    1,
)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加：发图崩溃按天计数')
