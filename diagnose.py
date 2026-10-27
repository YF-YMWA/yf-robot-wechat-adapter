"""系统诊断：一次性检查所有关键条件。

检查项：
  1. 微信进程是否运行
  2. 微信主窗口是否在屏幕内
  3. 控件树是否物化（mmui::MainWindow）
  4. 能否读取 Weixin.dll 模块（权限）
  5. 数据库能否打开
  6. 最近消息时间
"""
import os
import sys
import time
import ctypes

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'diagnosis.txt')
lines = []


def log(msg):
    lines.append(str(msg))
    # 同时打到终端：双击运行时窗口里要能看见，不然像卡死了
    try:
        print(msg, flush=True)
    except Exception:                              # noqa: BLE001
        pass
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


open(OUT, 'w').close()
log('========================================')
log('  YF-Robot 诊断报告')
log('  时间: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
log('========================================')
log('')

# ===== 1. 微信进程 =====
WECHAT_PIDS = []   # 给第 4 节权限检查复用，避免重复检测（psutil 可能漏）
log('【1】微信进程')
try:
    procs = []

    # 先走 psutil（信息全）
    try:
        import psutil

        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            nm = (p.info.get('name') or '').lower()
            if 'weixin' in nm or 'wechat' in nm:
                try:
                    rss = p.info['memory_info'].rss
                except Exception:                  # noqa: BLE001
                    rss = 0
                procs.append((p.info['pid'], p.info.get('name'), rss))
    except Exception as e:                         # noqa: BLE001
        log(f'  psutil 枚举失败: {e}')

    # psutil 看不到就用 Win32 枚举（微信本体权限更高时，非管理员 psutil 会漏）
    if not procs:
        try:
            import win32process
            import win32api
            import win32con
            import win32com.client

            pids = win32process.EnumProcesses()
            wmi = win32com.client.GetObject('winmgmts:')
            for pr in wmi.ExecQuery('SELECT ProcessId,Name FROM Win32_Process'):
                nm = (pr.Name or '').lower()
                if 'weixin' in nm or 'wechat' in nm:
                    procs.append((pr.ProcessId, pr.Name, 0))
            del pids, win32api, win32con
        except Exception as e:                     # noqa: BLE001
            log(f'  Win32 枚举也失败: {e}')

    if procs:
        procs.sort(key=lambda x: x[2], reverse=True)
        WECHAT_PIDS.extend([p[0] for p in procs])
        pid, name, rss = procs[0]
        log(f'  主进程: {name} (PID {pid})'
            + (f'  内存 {rss // 1024 // 1024}MB' if rss else ''))
        log(f'  进程总数: {len(procs)}')
    else:
        log('  [注意] 看不到微信进程')
        log('         可能原因：微信没启动，或者当前不是管理员权限')
        log('         （微信权限比普通程序高时，普通权限枚举不到它）')
except Exception as e:
    log(f'  [错误] {e}')

log('')

# ===== 2. 微信窗口 =====
log('【2】微信窗口')
try:
    import win32gui

    def find_wechat_windows():
        """找微信主窗。

        不再要求标题是「微信」—— 微信 4.x 的主窗标题是**账号昵称**（比如「大肥鱼」）。
        改成看类名（Qt 窗口）+ 尺寸，顺带把「不可见 / 在托盘」的也收进来，
        这样能明确告诉用户是哪一种情况，而不是笼统说「找不到」。
        """
        result = []

        def callback(hwnd, _):
            cls = win32gui.GetClassName(hwnd) or ''
            title = win32gui.GetWindowText(hwnd) or ''
            is_candidate = (
                'Weixin' in cls
                or 'mmui' in cls
                or 'Qt5' in cls
                or 'Qt6' in cls
            )
            if not is_candidate:
                return True
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            visible = bool(win32gui.IsWindowVisible(hwnd))
            # 托盘里的窗口尺寸可能是 0 或负数，别用尺寸把它们筛掉
            result.append((hwnd, title, cls, rect, w, h, visible))
            return True

        win32gui.EnumWindows(callback, None)
        return result

    wins = find_wechat_windows()
    if wins:
        for hwnd, title, cls, rect, w, h, visible in wins:
            x, y = rect[0], rect[1]
            # 最小化不一定就是 -32000，实测还见过 -21333；IsIconic 最可靠
            try:
                minimized = bool(win32gui.IsIconic(hwnd))
            except Exception:                      # noqa: BLE001
                minimized = False
            if not minimized:
                # 兜底：坐标离谱或尺寸小到不像主窗
                minimized = x <= -10000 or y <= -10000 or w < 300 or h < 200
            log(f'  窗口: "{title or "(无标题)"}"  hwnd={hwnd}')
            log(f'    类名: {cls}')
            log(f'    可见: {"是" if visible else "否"}')
            if minimized:
                log(f'    位置: ({x},{y})  ← 在托盘/已最小化，自动化拿不到控件')
                log('    [问题] 把微信主窗口点出来（点托盘图标），不要最小化')
            else:
                log(f'    位置: ({x},{y}) 尺寸: {w}x{h}')
    else:
        log('  [注意] 没找到微信窗口（按 Qt 类名找的）')
        log('         如果微信明明开着，多半是没管理员权限，读不到窗口信息')
except Exception as e:
    log(f'  [错误] {e}')

log('')

# ===== 3. 控件树 =====
log('【3】控件树（mmui）')
try:
    import uiautomation as auto
    root = auto.GetRootControl()
    found_mmui = False
    for w in root.GetChildren():
        cls = w.ClassName or ''
        if 'mmui' in cls:
            found_mmui = True
            log(f'  [OK] 找到控件树: {w.Name} (cls={cls})')
            break
        if 'Qt5' in cls:
            log(f'  [部分] Qt 外壳: {w.Name} (cls={cls}) — 控件树未物化')

    if not found_mmui:
        log('  [警告] 没有 mmui 控件树')
except Exception as e:
    log(f'  [错误] {e}')

log('')

# ===== 4. 权限（读微信模块） =====
log('【4】权限检查')
try:
    # 复用第一节找到的 PID：微信权限比普通程序高时，psutil 再枚举一次还是空的
    wx = WECHAT_PIDS[0] if WECHAT_PIDS else None
    if not wx:
        import psutil
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] and 'weixin' in p.info['name'].lower():
                wx = p.info['pid']
                break

    if wx:
        # 尝试读了望模块
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        k = ctypes.windll.kernel32
        h = k.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, wx)
        if h:
            log(f'  [OK] 能打开微信进程 PID {wx}')
            k.CloseHandle(h)
        else:
            err = ctypes.get_last_error()
            log(f'  [失败] 无法打开微信进程 PID {wx}（错误 {err}）')
            log('         → 需要管理员权限')
    else:
        log('  [注意] 找不到微信进程（或没权限看），见第 1 节说明')
except Exception as e:
    log(f'  [错误] {e}')

log('')

# ===== 5. 是否为管理员 =====
log('【5】当前权限')
try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    log(f'  管理员: {"是" if is_admin else "否"}')
except Exception as e:
    log(f'  [错误] {e}')

log('')

# ===== 6. 数据库 =====
log('【6】数据库')
try:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _RT = os.path.join(_BASE, 'runtime', 'python', 'Lib', 'site-packages')
    if _RT not in sys.path:
        sys.path.insert(0, _RT)

    from wechatauto import WeChatDB, auto_detect_db_dir
    db_dir = auto_detect_db_dir()
    log(f'  目录: {db_dir}')

    db = WeChatDB(db_dir=db_dir)
    sessions = db.get_sessions(limit=5)
    log(f'  会话数: {len(sessions)}')

    if sessions:
        u = sessions[0]['username']
        msgs = db.get_messages(u, limit=1)
        if msgs:
            ts = float(msgs[0].get('create_time') or 0)
            ago = time.time() - ts
            log(f'  最新消息: {time.strftime("%m-%d %H:%M:%S", time.localtime(ts))}')
            log(f'  距今: {ago:.0f} 秒')
except Exception as e:
    log(f'  [错误] {e}')
    import traceback
    log(traceback.format_exc()[:400])

log('')
log('========================================')
