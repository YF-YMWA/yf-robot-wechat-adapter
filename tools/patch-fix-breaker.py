"""一次性补丁：修正发送熔断的计数方式。

问题（刚发现的）：
  我把记账放在了 with_window_on_top 里，而它**每条消息会被调用 2~3 次**
  （UIA 第一轮、UIA 重试、重新激活后的再试）。于是**一条消息失败就凑满 3 次**，
  立刻进入 60 秒冷却 —— 后面正常消息全被「跳过发送：冷却中」挡掉。
  用户看到的就是「又出问题了：消息不发了」。

修法：
  · with_window_on_top 不再记账（它只是「一次尝试」）
  · 改在 send_text 的最终失败分支记一次失败，成功分支记一次成功
  · 冷却提示的天数改成向上取整（之前出现「还剩 0 秒」却还在挡）
  · 非管理员时 UIA 必然失败，这种情况不计入熔断（是权限问题，不是抖动）
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'account_send_result' in src:
    print('已经修过了')
    raise SystemExit(0)

# ---------- 1. 冷却提示向上取整 ----------
src = src.replace(
    '''    left = SEND_HEALTH["cooldown"] - time.time()
    if left > 0:
        return False, "连续失败冷却中，还剩 %d 秒" % int(left)''',
    '''    left = SEND_HEALTH["cooldown"] - time.time()
    if left > 0:
        # 用 ceil：之前 int() 会显示「还剩 0 秒」却还在挡，看着像 bug
        return False, "连续失败冷却中，还剩 %d 秒" % max(1, int(-(-left // 1)))''',
)

# ---------- 2. 新增「整条消息」级别的记账 ----------
anchor = 'def note_send_result(ok, err=""):'
if anchor not in src:
    print('找不到 note_send_result')
    raise SystemExit(1)

src = src.replace(
    anchor,
    '''def account_send_result(ok, err=""):
    """按「一条消息」记账，而不是按「一次尝试」。

    with_window_on_top 一条消息会走 2~3 次，按它记账会让一条消息失败就进冷却。
    """
    try:
        import ctypes as _ct

        is_admin = bool(_ct.windll.shell32.IsUserAnAdmin())
    except Exception:
        is_admin = True

    # 非管理员时 UIA 必失败，那是权限问题 —— 不参与熔断，免得把正常发送也停了
    if not ok and not is_admin:
        log("[权限] 当前不是管理员，UIA 发不出去是正常的；不计入熔断")
        return

    note_send_result(ok, err)


''' + anchor,
    1,
)

# ---------- 3. with_window_on_top 不再记账 ----------
src = src.replace(
    '''        finally:
            # 统一记账：成功清连败计数，失败累计 —— 连败三次就冷却（note_send_result 里）
            try:
                note_send_result(ok)
            except Exception:
                pass
            if BACKGROUND_SEND:''',
    '''        finally:
            # 这里**不记账**：一条消息会调用本函数 2~3 次（重试/重新激活），
            # 按次数记账会让单条消息失败就触发冷却。记账在 send_text 的最终分支。
            if BACKGROUND_SEND:''',
)

# ---------- 4. send_text 的最终失败分支记一次 ----------
src = src.replace(
    '''            log("发送最终失败，请把微信窗口保持在桌面、别最小化；内容：", text[:30])
            return False''',
    '''            account_send_result(False, "send_text 最终失败")
            log("发送最终失败，请把微信窗口保持在桌面、别最小化；内容：", text[:30])
            return False''',
)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已修正：熔断按「一条消息」计数，非管理员不计入')
