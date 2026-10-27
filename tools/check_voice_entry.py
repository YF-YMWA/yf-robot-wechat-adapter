"""扫微信主窗控件树，找「发语音」的入口。

用法：python check_voice_entry.py

先恢复窗口（如果最小化），再用句柄连进去，把所有控件名打出来，
重点看有没有 语音/麦克风/按住 之类。
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'YF-Robot', 'runtime', 'python', 'Lib', 'site-packages'))

KEYWORDS = ['语音', '录音', '说话', '按住', '麦克风', 'voice', 'record', 'mic', '音频']


def find_main_window():
    import win32gui

    found = []

    def cb(h, _):
        cls = win32gui.GetClassName(h) or ''
        name = win32gui.GetWindowText(h) or ''
        if cls.startswith('Qt') and name and 'Tray' not in cls:
            found.append((h, cls, name))
        return True

    win32gui.EnumWindows(cb, None)
    return found


def main():
    try:
        import win32gui
        import win32con
        import uiautomation as auto
    except Exception as e:
        print('  [错误] 依赖导入失败：', e)
        return 1

    wins = find_main_window()
    if not wins:
        print('  [注意] 没找到微信窗口（先把微信主界面打开）')
        return 1

    hwnd, cls, name = wins[0]
    print('  窗口: %r  cls=%s  hwnd=%d' % (name, cls, hwnd))

    # 最小化就先恢复
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(1)
            print('  已尝试恢复，iconic =', bool(win32gui.IsIconic(hwnd)))
    except Exception as e:
        print('  恢复失败：', e)

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.5)

    root = auto.ControlFromHandle(hwnd)
    if not root:
        print('  [错误] 拿不到 UIA 根控件')
        return 1

    print('  UIA 根:', root.Name, '/', root.ControlTypeName)

    items = []

    def walk(ctrl, depth=0, maxd=6):
        if depth > maxd:
            return
        try:
            children = ctrl.GetChildren()
        except Exception:
            return
        for ch in children:
            try:
                nm = ch.Name or ''
                ct = ch.ControlTypeName or ''
                ck = ch.ClassName or ''
            except Exception:
                continue
            items.append((depth, ct, nm, ck))
            walk(ch, depth + 1, maxd)

    walk(root)
    print('  控件总数（6 层内）: %d' % len(items))

    hits = [it for it in items if any(k.lower() in it[2].lower() for k in KEYWORDS)]
    print('  名字带语音关键词的控件: %d' % len(hits))
    for d, ct, nm, ck in hits[:15]:
        print('   %s%s | %r | %s' % ('  ' * d, ct, nm[:36], ck[:20]))

    # 所有有名字的按钮（发语音多半是个 Button）
    buttons = [it for it in items if it[1] in ('ButtonControl', 'MenuItemControl') and it[2]]
    print('')
    print('  按钮类控件（%d 个，最多列 30）:' % len(buttons))
    for d, ct, nm, ck in buttons[:30]:
        print('   - %r' % nm[:40])

    # 输入框附近
    print('')
    try:
        edits = [it for it in items if it[1] == 'EditControl']
        print('  输入框: %d 个' % len(edits))
        for d, ct, nm, ck in edits[:5]:
            print('   - %r' % nm[:40])
    except Exception as e:
        print('  读输入框失败：', e)

    return 0


if __name__ == '__main__':
    sys.exit(main())
