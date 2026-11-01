"""自己发的消息要在「路由之前」就丢掉。

现象（用户日志）：
  [语音] 消息路由: type='语音' → voice（self_sent: True）
  [语音] 识别结果: What ...
  她把自己发的语音条拿去识别，还可能当成对方说的话来回复。

原因：自我过滤写在后面（sender == me），而语音/图片分支在这之前就执行了。
改：在 on_message_inner 开头，拿到 sender 就先判自己，直接返回。
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wechatauto_bridge.py")
s = io.open(P, encoding="utf-8").read()

if "自己发的消息不该走 ASR" in s:
    print("已改过")
    raise SystemExit(0)

old = '''            mtype = msg.get("type") or ""
            content = (msg.get("content") or "").strip()

            # 统一决策：这条消息走哪条路（实现和用例都在 msg_route.py）
            route = route_message(mtype, content)'''

new = '''            # 自己发的消息不该走 ASR/图像描述，也不该触发回复。
            # 以前这个判断放在后面，导致语音先被识别了一遍（刷 ASR 额度、还可能自问自答）。
            try:
                _sender = msg.get("sender_username") or ""
                _me = me
                if _sender and _me and _sender == _me:
                    return
            except Exception:
                pass

            mtype = msg.get("type") or ""
            content = (msg.get("content") or "").strip()

            # 统一决策：这条消息走哪条路（实现和用例都在 msg_route.py）
            route = route_message(mtype, content)'''

if old not in s:
    print("找不到锚点")
    raise SystemExit(1)

s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已改：自我消息在路由前拦截")
