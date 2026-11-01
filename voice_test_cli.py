"""发语音条测试（发到文件传输助手，不打扰别人）。

用法：双击 发语音测试.bat
     或 python voice_test_cli.py "要念的话" [聊天名] [设备序号]
"""
import os
import sys
import time

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


def _looks_garbled(s):
    """GBK 参数在 UTF-8 控制台下会变成 ???????，这种就别用了。"""
    if not s:
        return True
    bad = sum(1 for ch in s if ch in "?\ufffd")
    return bad >= max(2, len(s) // 3)


def adapter_running():
    """适配器（wechatauto_bridge.py）是不是正在跑。返回 PID 或 0。"""
    try:
        import subprocess

        out = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                "Where-Object { $_.CommandLine -like '*wechatauto_bridge*' } | "
                "Select-Object -First 1 -ExpandProperty ProcessId",
            ],
            capture_output=True,
            timeout=15,
            creationflags=0x08000000,
        )
        txt = (out.stdout or b"").decode("utf-8", "ignore").strip()
        return int(txt) if txt.isdigit() else 0
    except Exception:
        return 0


def main():
    # 两个自动化进程会抢同一个微信窗口，必须先关掉适配器
    pid = adapter_running()
    if pid and "--force" not in sys.argv:
        print("")
        print("  [X] 适配器正在运行（PID %s），会和你抢微信窗口。" % pid)
        print("      现象：点击落在适配器窗口上，日志报「落点窗口不属于微信」。")
        print("")
        print("  两种做法：")
        print("    A. 想单独测这条链路：先关掉适配器窗口，再跑本脚本")
        print("    B. 想测真实回复：关掉本脚本，在适配器里把「语音概率」调到 100，")
        print("       然后给别人发条消息，看她回不回语音条")
        print("")
        print("  确实要同时跑（不推荐）：加参数 --force")
        return 2

    default_text = "这是一条测试语音，听到就说明成功了"
    default_chat = "文件传输助手"

    text = sys.argv[1] if len(sys.argv) > 1 else default_text
    chat = sys.argv[2] if len(sys.argv) > 2 else default_chat
    dev = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    if _looks_garbled(text):
        print("  [!] 传入的文字是乱码（bat 编码问题），改用内置默认句子")
        text = default_text
    if _looks_garbled(chat):
        chat = default_chat

    print("  文字：%s" % text)
    print("  发送到：%s" % (chat or "当前聊天"))
    print("  播放设备：%s" % dev)
    print("")

    # 检查控件树之前，先把我们自己的控制台收起来。
    # 否则 UIA 点击会落在控制台上：「落点窗口不属于微信（进程 != 微信）」
    V.minimize_our_console()
    time.sleep(0.3)

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
    try:
        sys.exit(main())
    finally:
        try:
            V.restore_our_console()
        except Exception:
            pass
