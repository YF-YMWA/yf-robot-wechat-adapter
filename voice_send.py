"""发语音条：切换聊天 → 聚焦输入框 → 按住 Alt 播放 → 松开 → 验证。

为什么必须有这个模块：
  以前「语音」只是把 wav 当**文件**发出去，对方看到的是文件，不是语音条。
  微信 PC 支持「按住 Alt 说话」，所以可以真的发语音条：
     按住 Alt（微信开始录音）→ 把合成语音送进麦克风 → 松开（微信发出）
  关键前提是「合成的声音要能进微信的麦克风」：
     · 装了虚拟声卡（VB-CABLE）：微信麦克风选 CABLE Output，我们播到 CABLE Input
     · 或启用系统「立体声混音」：微信麦克风选它，我们播到扬声器
  两种都没配的话，只能走声学路径（外放让麦克风听到），质量差但能用。

安全点：
  · 只在目标聊天窗口处于前台时才按键（否则盲按会按到别的程序里）
  · 时长不足 1 秒会被微信判「说话时间太短」，所以强制至少 1.2 秒
  · 任何异常都会松开 Alt，避免键盘卡在按下状态
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import voice_ptt as V

MIN_HOLD_S = 1.2


def _gui():
    from wechatauto import WeChatGUI

    return WeChatGUI()


def open_chat_and_focus(who, log=print):
    """切到指定聊天并把光标放进输入框。返回 (ok, detail)。"""
    gui = _gui()
    try:
        if not gui.is_alive():
            return False, "微信窗口不在了"

        # 管理员运行/命令行窗口在前时，微信会被挤到后面，Alt 就按到控制台里去了。
        # 发送期间先把自己的控制台收起来，发完再还回来。
        V.minimize_our_console()

        gui.bring_to_front()
        time.sleep(0.3)
        if who:
            ok = gui.open_chat(who)
            if not ok:
                return False, "打不开聊天：%s" % who
            time.sleep(0.4)
        try:
            gui.focus_input()
        except Exception:
            pass
        time.sleep(0.2)
        return True, "已切到 %s 并把光标放进输入框" % (who or "当前聊天")
    except Exception as e:
        return False, "切聊天失败：%r" % (e,)


def last_message(who=None):
    """读目标聊天最后一条消息（用来验证语音条真的发出去了）。"""
    try:
        from wechatauto import WeChat

        wx = WeChat()
        if who:
            chat = wx.ChatWith(who)
        else:
            chat = wx.GetSubWindow()
        msg = chat.GetLastMessage() if hasattr(chat, "GetLastMessage") else None
        return msg
    except Exception:
        return None


def send_voice(text, *, chat=None, tts_fn, ffmpeg="ffmpeg", out_device=None,
               tail_ms=400, log=print):
    """完整流程。返回 dict：{ok, steps, error?, seconds?, verified?}"""
    steps = []
    text = str(text or "").strip()
    if not text:
        return {"ok": False, "error": "要念的内容是空的", "steps": steps}

    # 1. 合成
    wav = tts_fn(text)
    if not wav:
        return {"ok": False, "error": "语音合成失败", "steps": steps}
    steps.append("合成：%s" % os.path.basename(wav))

    pcm = os.path.join(os.path.dirname(wav), "ptt_" + os.path.splitext(os.path.basename(wav))[0] + ".wav")
    try:
        V.to_pcm_wav(wav, pcm, ffmpeg=ffmpeg)
        steps.append("转 PCM 完成")
    except Exception as e:
        return {"ok": False, "error": "转码失败：%s" % e, "steps": steps}

    try:
        dur, dev_name = V.play_wav(pcm, out_device if out_device is not None else -1)
        steps.append("试播 %.1fs → %s" % (dur, dev_name))
    except Exception as e:
        return {"ok": False, "error": "播放失败：%s" % e, "steps": steps}

    # 2. 切聊天 + 聚焦
    ok, detail = open_chat_and_focus(chat, log=log)
    steps.append(detail)
    if not ok:
        return {"ok": False, "error": detail, "steps": steps}

    # 3. 按住 Alt 播放
    hwnd, title = V.find_wechat_window()
    if not hwnd:
        return {"ok": False, "error": "找不到微信窗口", "steps": steps}

    # 再抢一次前台（管理员运行时系统会拒绝普通请求，这里用 AttachThreadInput 重试）
    ok_fg = False
    for attempt in range(3):
        if V.foreground_is(hwnd):
            ok_fg = True
            break
        V.focus_window(hwnd, tries=1)
        time.sleep(0.25)
    if not ok_fg:
        V.restore_our_console()
        tip = ""
        if V.is_admin():
            tip = "（你现在是用管理员运行的，微信不是管理员，权限不一致时切前台会被拒绝 —— 请改成普通双击运行）"
        return {
            "ok": False,
            "error": "微信不在前台，拒绝盲按键" + tip,
            "steps": steps,
        }
    steps.append("已确认微信在前台")

    hold_s = max(MIN_HOLD_S, dur + tail_ms / 1000.0)
    try:
        V.alt_down()
        t0 = time.time()
        steps.append("Alt 按下")
        time.sleep(0.25)
        V.play_wav(pcm, out_device if out_device is not None else -1)
        while time.time() - t0 < hold_s:
            time.sleep(0.02)
        V.alt_up()
        steps.append("Alt 松开（按住 %.1fs）" % (time.time() - t0))
    except Exception as e:
        return {"ok": False, "error": "按住说话失败：%s" % e, "steps": steps}
    finally:
        V.key_up_safe()
        V.restore_our_console()

    V.restore_our_console()

    # 4. 验证：最后一条是不是语音
    time.sleep(1.0)
    verified = None
    try:
        msg = last_message(chat)
        if msg is not None:
            kind = type(msg).__name__
            verified = kind
            steps.append("最后一条消息类型：%s" % kind)
    except Exception as e:
        steps.append("验证失败（不影响已发）：%r" % (e,))

    # 验证读不到消息时（常见原因：UIA 树被安全软件拦），
    # 不能说「不是语音条」—— 只说「发了，但没法确认类型」。
    if verified is None:
        steps.append(
            "读不到消息，无法确认类型（UIA 控件树拿不到时就会这样："
            "把 python 加进安全软件白名单、别用管理员运行，通常就好了）"
        )
        return {
            "ok": True,
            "steps": steps,
            "seconds": round(hold_s, 1),
            "verified": None,
            "is_voice": None,
            "note": "已按住 Alt 发送，但没能读取消息确认类型",
        }

    return {
        "ok": True,
        "steps": steps,
        "seconds": round(hold_s, 1),
        "verified": verified,
        "is_voice": verified == "VoiceMessage",
    }


if __name__ == "__main__":
    # python voice_send_cli.py "文字" [聊天名] [设备序号]
    text = sys.argv[1] if len(sys.argv) > 1 else "测试语音"
    chat = sys.argv[2] if len(sys.argv) > 2 else "文件传输助手"
    dev = int(sys.argv[3]) if len(sys.argv) > 3 else None

    def _tts(t):
        import base64
        import json
        import urllib.request

        req = urllib.request.Request(
            "http://127.0.0.1:8899/api/tts",
            data=json.dumps({"text": t}).encode("utf-8"),
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.loads(r.read().decode("utf-8"))
        if not j.get("ok"):
            return ""
        d = base64.b64decode(j["data"])
        out = os.path.join("data", "media-cache", j.get("name") or "tts.wav")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(d)
        return out

    r = send_voice(text, chat=chat, tts_fn=_tts, out_device=dev)
    for s in r.get("steps") or []:
        print("  ·", s)
    print("结果：", "成功" if r.get("ok") else "失败", r.get("error") or "", "| 语音条:", r.get("is_voice"))
