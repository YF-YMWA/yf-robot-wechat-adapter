"""发语音条测试（发到文件传输助手，不打扰别人）。

用法：双击 发语音测试.bat
     或 python voice_test_cli.py "要念的话" [聊天名] [设备序号]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_send as VS
import voice_ptt as V


def core_tts(text):
    """让核心合成语音。"""
    import base64
    import json
    import urllib.request

    req = urllib.request.Request(
        "http://127.0.0.1:8899/api/tts",
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("  [X] 核心没响应（服务没开？）：%s" % e)
        return ""

    if not j.get("ok") or not j.get("data"):
        print("  [X] 合成失败：%s" % (j.get("error") or "没有音频数据"))
        return ""

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "media-cache")
    os.makedirs(out_dir, exist_ok=True)
    name = j.get("name") or "tts.wav"
    path = os.path.join(out_dir, os.path.basename(name))
    with open(path, "wb") as f:
        f.write(base64.b64decode(j["data"]))
    return path


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "测试语音条，听到就说明成功了"
    chat = sys.argv[2] if len(sys.argv) > 2 else "文件传输助手"
    dev = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    print("  文字：%s" % text)
    print("  发送到：%s" % (chat or "当前聊天"))
    print("  播放设备：%s" % dev)
    print("")

    # 先看控件树通不通（通了才能切聊天）
    print("  检查微信控件树…")
    from wechatauto import WeChatGUI

    try:
        gui = WeChatGUI()
        ok = gui.open_chat(chat) if chat else gui.is_alive()
        print("  切聊天：%s" % ("成功" if ok else "失败（只能用当前聊天）"))
        if not ok:
            chat = ""
    except Exception as e:
        print("  切聊天异常：%r → 用当前聊天" % (e,))
        chat = ""

    print("  开始发送（微信会被切到前台，约 5 秒）…")
    r = VS.send_voice(text, chat=chat, tts_fn=core_tts, out_device=dev)
    for s in r.get("steps") or []:
        print("   ·", s)
    print("")
    if r.get("ok"):
        print("  [OK] 已发送（按住 %.1f 秒）" % (r.get("seconds") or 0))
        if r.get("is_voice") is True:
            print("  [OK] 确认是语音条")
        elif r.get("is_voice") is None:
            print("  [!] 已发，但读不到消息，无法确认类型 —— 去微信看一眼")
        else:
            print("  [!] 发出去的不是语音条（类型=%s）" % r.get("verified"))
        return 0
    print("  [X] 失败：%s" % r.get("error"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
