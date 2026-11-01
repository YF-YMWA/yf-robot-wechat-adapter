"""把陌生人限制接进回复流程。"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if "stranger_limit" in s:
    print("已接入")
    raise SystemExit(0)

# 1. 回复前检查次数（在 rate_guard 之后、真正发送之前）
old = '''            if not rate_guard(username):
                log("这一分钟回太多了，先停一下：", target)
                return
            log("回复", ("群" if is_group else "私聊"), target, "→", nickname, "：", (bubbles[0] or "")[:40])'''

new = '''            if not rate_guard(username):
                log("这一分钟回太多了，先停一下：", target)
                return

            # 陌生人限制：每天回话次数（主人/白名单不受限）
            _is_owner = bool(MASTER_WXID) and str(username) == str(MASTER_WXID)
            if not _is_owner:
                try:
                    import stranger_limit as _sl

                    _okr, _why = _sl.check_reply(username, _CFG)
                    if not _okr:
                        log("[陌生人] 不回 %s：%s" % (target, _why))
                        return
                except Exception as _se:            # noqa: BLE001
                    log("[陌生人] 次数检查失败（放行）：%r" % (_se,))

            log("回复", ("群" if is_group else "私聊"), target, "→", nickname, "：", (bubbles[0] or "")[:40])'''

assert old in s, "找不到 rate_guard 段"
s = s.replace(old, new, 1)

# 2. 回复后记一次
old2 = '''                send_text(line, target, username, quote_text=(content if first and QUOTE_REPLY else None))
                first = False'''
new2 = '''                send_text(line, target, username, quote_text=(content if first and QUOTE_REPLY else None))
                first = False
                if not _is_owner:
                    try:
                        import stranger_limit as _sl2

                        _sl2.note_reply(username, _CFG)
                    except Exception:
                        pass'''
assert old2 in s
s = s.replace(old2, new2, 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已接入：回话次数限制")
