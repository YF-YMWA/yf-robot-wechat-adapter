"""看当前聊天最后一条消息是什么（验证语音条有没有真的发出去）。"""
import sys

sys.path.insert(0, ".")
import voice_send as VS

for who in ["", "文件传输助手"]:
    msg = VS.last_message(who or None)
    label = who or "当前聊天"
    if msg is None:
        print("  %-10s 读不到消息" % label)
        continue
    t = type(msg).__name__
    try:
        c = str(msg.content)[:40]
    except Exception:
        c = "(无 content)"
    print("  %-10s %-16s %s" % (label, t, c))
