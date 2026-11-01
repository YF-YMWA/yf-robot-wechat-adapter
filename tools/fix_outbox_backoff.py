"""核心没起来时，outbox 轮询不要每 5 秒刷一屏错误。

用户截图：适配器窗口满屏「后台结果轮询失败 … 连接被拒绝」。
原因：核心服务没启动，适配器仍每 5 秒请求一次并完整打印异常。

改法：
  · 连不上就退避（5s → 10 → 20 → 40 → 最多 60s）
  · 同样的错误只打印第一次，恢复时打印一行「已恢复」
  · 真正连上了就把退避重置回 5 秒
"""
import io
import os
import re

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if "OUTBOX_BACKOFF" in s:
    print("已改过")
    raise SystemExit(0)

old = '''        while True:
            time.sleep(5)
            try:
                if AWAY["on"] or away_active():
                    continue
                base = bot_base()'''

new = '''        # 核心没起来时退避，避免满屏「连接被拒绝」
        OUTBOX_BACKOFF = 5
        OUTBOX_MAX = 60
        last_err = ""

        while True:
            time.sleep(OUTBOX_BACKOFF)
            try:
                if AWAY["on"] or away_active():
                    continue
                base = bot_base()'''

assert old in s, "找不到 outbox 循环"
s = s.replace(old, new, 1)

# 成功/失败分别处理
old2 = '''                data = r.json() or {}
                items = data.get("list") or []'''
new2 = '''                data = r.json() or {}
                if OUTBOX_BACKOFF != 5:
                    log("[后台] 核心已恢复，轮询回到 5 秒")
                    OUTBOX_BACKOFF = 5
                last_err = ""
                items = data.get("list") or []'''
assert old2 in s
s = s.replace(old2, new2, 1)

old3 = '''            except Exception as e:                  # noqa: BLE001
                log("后台结果轮询失败（不影响聊天）：", repr(e))'''
new3 = '''            except Exception as e:                  # noqa: BLE001
                # 连不上核心是常态（服务没开），退避 + 只提示一次，别刷屏
                msg = str(e)
                kind = "连接被拒绝（核心没启动？）" if "10061" in msg or "Connection refused" in msg \\
                    and "10061" in msg else "轮询出错"
                if "10061" in msg or "refused" in msg.lower():
                    kind = "连接被拒绝（核心没启动？）"
                if kind != last_err:
                    log("[后台] 取不到待发结果：%s —— 会退避重试，不影响聊天" % kind)
                    last_err = kind
                OUTBOX_BACKOFF = min(OUTBOX_MAX, OUTBOX_BACKOFF * 2)'''
assert old3 in s
s = s.replace(old3, new3, 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已改：outbox 轮询退避 + 错误只提示一次")
