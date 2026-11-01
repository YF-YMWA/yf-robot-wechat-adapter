"""只验证：能否切到「文件传输助手」并读到消息（不发任何内容）。"""
import sys

sys.path.insert(0, ".")
import voice_send as VS

ok, detail = VS.open_chat_and_focus("文件传输助手")
print("  切聊天:", ok, "|", detail)

msg = VS.last_message("文件传输助手")
if msg is None:
    print("  读最后一条: 拿不到")
else:
    print("  读最后一条:", type(msg).__name__)
    try:
        print("  内容:", str(msg.content)[:60])
    except Exception:
        print("  （没有 content 属性）")
