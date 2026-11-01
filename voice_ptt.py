"""按住 Alt 发语音条（微信 PC 的按住说话）。

原理：
  微信 PC 在聊天输入框里**按住 Alt** 就开始录音，松开就发送。
  所以我们做三件事：
    1. 把合成的语音播到「微信正在用的麦克风」那条线路上
       （装个虚拟声卡 VB-CABLE，或启用系统「立体声混音」，
         微信麦克风选它的输出端，我们把声音播到它的输入端）
    2. 按住 Alt，等到音频播完
    3. 松开 Alt → 微信发出语音条

为什么不用 sounddevice/pyaudio：
  包里没有这两个库，为了少装依赖，直接用系统自带的 winmm（ctypes）。
  好处是零依赖，坏处是只能播 PCM WAV —— 所以事先用 ffmpeg 转成
  16bit 单声道 wav。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import struct
import subprocess
import sys
import time

# ---------- winmm 设备枚举 ----------

winmm = ctypes.WinDLL("winmm", use_last_error=True)

WAVE_MAPPER = -1
MAXPNAMELEN = 32


class WAVEOUTCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wt.WORD),
        ("wPid", wt.WORD),
        ("vDriverVersion", wt.UINT),
        ("szPname", wt.WCHAR * MAXPNAMELEN),
        ("dwFormats", wt.DWORD),
        ("wChannels", wt.WORD),
        ("wReserved1", wt.WORD),
        ("dwSupport", wt.DWORD),
    ]


class WAVEINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wt.WORD),
        ("wPid", wt.WORD),
        ("vDriverVersion", wt.UINT),
        ("szPname", wt.WCHAR * MAXPNAMELEN),
        ("dwFormats", wt.DWORD),
        ("wChannels", wt.WORD),
        ("wReserved1", wt.WORD),
    ]


def list_outputs():
    """所有播放设备：[(index, name), ...]"""
    n = winmm.waveOutGetNumDevs()
    out = []
    for i in range(n):
        caps = WAVEOUTCAPSW()
        if winmm.waveOutGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
            out.append((i, caps.szPname))
    return out


def list_inputs():
    """所有录音设备：[(index, name), ...]（用来确认微信麦克风是哪条）"""
    n = winmm.waveInGetNumDevs()
    out = []
    for i in range(n):
        caps = WAVEINCAPSW()
        if winmm.waveInGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
            out.append((i, caps.szPname))
    return out


# ---------- WAV 播放（指定设备） ----------

WAVE_FORMAT_PCM = 1


class WAVEFORMATEX(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("wFormatTag", wt.WORD),
        ("nChannels", wt.WORD),
        ("nSamplesPerSec", wt.DWORD),
        ("nAvgBytesPerSec", wt.DWORD),
        ("nBlockAlign", wt.WORD),
        ("wBitsPerSample", wt.WORD),
        ("cbSize", wt.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_char_p),
        ("dwBufferLength", wt.DWORD),
        ("dwBytesRecorded", wt.DWORD),
        ("dwUser", ctypes.c_void_p),
        ("dwFlags", wt.DWORD),
        ("dwLoops", wt.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_void_p),
    ]


WHDR_DONE = 0x00000001


def _read_wav(path):
    """读 PCM WAV，返回 (params, data)。只支持 PCM。"""
    with open(path, "rb") as f:
        raw = f.read()

    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("不是 WAV 文件：" + os.path.basename(path))

    pos = 12
    fmt = None
    data = None
    while pos + 8 <= len(raw):
        cid = raw[pos : pos + 4]
        size = struct.unpack("<I", raw[pos + 4 : pos + 8])[0]
        body = raw[pos + 8 : pos + 8 + size]
        if cid == b"fmt ":
            tag, ch, rate, _avg, align, bits = struct.unpack("<HHIIHH", body[:16])
            fmt = {"tag": tag, "ch": ch, "rate": rate, "bits": bits, "align": align}
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)

    if not fmt or data is None:
        raise ValueError("WAV 缺少 fmt/data 段")
    if fmt["tag"] != WAVE_FORMAT_PCM:
        raise ValueError("只支持 PCM WAV（当前 format=%s）" % fmt["tag"])
    return fmt, data


def play_wav(path, device_index=WAVE_MAPPER, timeout_s=None):
    """把 WAV 播到指定设备，播完才返回。返回 (played_seconds, device_name)。"""
    fmt, data = _read_wav(path)
    names = dict(list_outputs())
    dev = device_index if device_index is not None else WAVE_MAPPER
    dev_name = names.get(dev, "系统默认输出")

    wf = WAVEFORMATEX(
        WAVE_FORMAT_PCM, fmt["ch"], fmt["rate"], fmt["rate"] * fmt["align"], fmt["align"], fmt["bits"], 0
    )

    handle = ctypes.c_void_p()
    rc = winmm.waveOutOpen(ctypes.byref(handle), dev, ctypes.byref(wf), 0, 0, 0)
    if rc != 0:
        raise OSError("打开音频设备失败（code=%s），检查设备序号是否有效" % rc)

    try:
        buf = ctypes.create_string_buffer(data, len(data))
        hdr = WAVEHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
        hdr.dwBufferLength = len(data)

        rc = winmm.waveOutPrepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
        if rc != 0:
            raise OSError("准备缓冲区失败（code=%s）" % rc)
        rc = winmm.waveOutWrite(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
        if rc != 0:
            raise OSError("播放失败（code=%s）" % rc)

        seconds = len(data) / float(fmt["rate"] * fmt["align"])
        deadline = time.time() + (timeout_s or seconds + 15)
        while time.time() < deadline:
            if hdr.dwFlags & WHDR_DONE:
                break
            time.sleep(0.02)
        else:
            winmm.waveOutReset(handle)

        winmm.waveOutUnprepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
        return seconds, dev_name
    finally:
        winmm.waveOutClose(handle)


# ---------- 按键：按住 Alt ----------

user32 = ctypes.WinDLL("user32", use_last_error=True)
VK_MENU = 0x12      # 左 Alt（微信 4.x 不用它）
VK_RMENU = 0xA5     # 右 Alt —— 微信 4.x 的「按住发语音」就是这个
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001


def _key(vk, up=False, extended=False):
    flags = 0
    if up:
        flags |= KEYEVENTF_KEYUP
    # 注意：KEYEVENTF_SCANCODE 时第二个参数必须是扫描码，
    # 之前把虚拟键(0xA5)塞进扫描码位，结果按键根本没生效 —— 右 Alt 完全没按下去。
    # 扩展键要的是 KEYEVENTF_EXTENDEDKEY。
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    user32.keybd_event(vk, 0, flags, 0)


def alt_down():
    # 微信 4.x 认的是右 Alt（界面提示「发语音（按住右 Alt）」）
    _key(VK_RMENU, up=False, extended=True)


def alt_up():
    _key(VK_RMENU, up=True, extended=True)


def key_up_safe():
    """兜底：无论如何把 Alt 松开（异常时防止键盘卡在按下状态）。"""
    try:
        alt_up()
    except Exception:
        pass



# ---------- 权限 / 控制台窗口 ----------

def is_admin():
    """当前进程是不是管理员。"""
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def console_hwnd():
    """我们自己的控制台窗口句柄（没有返回 0）。"""
    try:
        import ctypes

        return int(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:
        return 0


def minimize_our_console():
    """把控制台最小化，免得它挡住微信、抢焦点。返回是否成功。"""
    import win32con
    import win32gui

    h = console_hwnd()
    if not h:
        return False
    try:
        win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
        time.sleep(0.15)
        return True
    except Exception:
        return False


def restore_our_console():
    import win32con
    import win32gui

    h = console_hwnd()
    if not h:
        return
    try:
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
    except Exception:
        pass


def wechat_elevated(hwnd):
    """微信进程是不是管理员权限（和我们不一致时容易控制失败）。"""
    try:
        import ctypes
        import win32process

        _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not h:
            return None
        try:
            token = ctypes.c_void_p()
            if not ctypes.windll.advapi32.OpenProcessToken(h, 0x0008, ctypes.byref(token)):
                return None
            try:
                size = ctypes.c_ulong(0)
                ctypes.windll.advapi32.GetTokenInformation(token, 20, None, 0, ctypes.byref(size))
                buf = ctypes.create_string_buffer(size.value or 4)
                if not ctypes.windll.advapi32.GetTokenInformation(
                    token, 20, buf, size, ctypes.byref(size)
                ):
                    return None
                # TOKEN_ELEVATION_TYPE: 1=default(UAC 关) 2=full 3=limited
                return int.from_bytes(buf.raw[:4], "little")
            finally:
                ctypes.windll.kernel32.CloseHandle(token)
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return None


def elevation_report():
    """给自检用：说清「谁在管理员下跑」。"""
    adm = is_admin()
    hwnd, _ = find_wechat_window()
    we = wechat_elevated(hwnd) if hwnd else None
    lines = ["  本程序是管理员运行: %s" % ("是" if adm else "否")]
    if hwnd:
        lines.append("  微信是管理员运行: %s" % ("是" if we == 2 else ("否" if we else "查不到")))
    if adm and we != 2:
        lines.append("  ⚠ 不建议用管理员运行：微信不是管理员，权限不一致时键盘/UIA 容易落到别的窗口")
        lines.append("    请直接双击运行（会弹 UAC 就点否），或右键「以当前用户身份运行」")
    return lines


# ---------- 找微信窗口 ----------

def find_wechat_window(titles=("微信", "WeChat")):
    """返回 (hwnd, title)。找不到返回 (0, '')。"""
    import win32gui

    found = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        t = win32gui.GetWindowText(hwnd)
        if not t:
            return True
        cls = win32gui.GetClassName(hwnd)
        # 主窗口类名 WeChatMainWndForPC（3.x）/ Qt51514QWindowIcon 之类（4.x 变化较多），
        # 所以主要看标题，并排除明显不是的
        if any(k == t or k in t for k in titles) and "WeChatAppEx" not in cls:
            found.append((hwnd, t, cls))
        return True

    win32gui.EnumWindows(cb, None)
    if not found:
        return 0, ""
    # 取面积最大的那个（主窗口）
    found.sort(key=lambda x: _area(x[0]), reverse=True)
    return found[0][0], found[0][1]


def _area(hwnd):
    try:
        import win32gui

        l, t, r, b = win32gui.GetWindowRect(hwnd)
        if r <= l or b <= t:
            return 0
        return (r - l) * (b - t)
    except Exception:
        return 0


def focus_window(hwnd, tries=3):
    """把窗口提到前台。返回是否**真的**到了前台。

    只用 SetForegroundWindow 会被系统静默拒绝（Windows 的前台锁定），
    实测会「以为切过去了，其实键盘还在别的窗口」。这里用
    AttachThreadInput 把自己的输入队列挂到前台线程上再切。
    """
    import ctypes
    import time as _t

    user32 = ctypes.windll.user32

    for _ in range(max(1, tries)):
        try:
            if user32.GetForegroundWindow() == hwnd:
                return True

            fg = user32.GetForegroundWindow()
            tid_fg = user32.GetWindowThreadProcessId(fg, None)
            tid_me = user32.GetWindowThreadProcessId(hwnd, None)

            attached = False
            try:
                if tid_fg and tid_me and tid_fg != tid_me:
                    attached = bool(user32.AttachThreadInput(tid_fg, tid_me, True))
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetFocus(hwnd)
            finally:
                if attached:
                    try:
                        user32.AttachThreadInput(tid_fg, tid_me, False)
                    except Exception:
                        pass

            _t.sleep(0.2)
            if user32.GetForegroundWindow() == hwnd:
                return True
        except Exception:
            pass
    return False


def foreground_is(hwnd):
    import win32gui

    try:
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return False


# ---------- 转成 PCM WAV ----------

def to_pcm_wav(src, dst, ffmpeg="ffmpeg"):
    """转成 16bit 单声道 16k wav（微信语音就这个档）。失败抛异常。"""
    cmds = [
        [ffmpeg, "-y", "-i", src, "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", dst],
        [ffmpeg + ".exe", "-y", "-i", src, "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", dst],
    ]
    last = None
    for c in cmds:
        try:
            p = subprocess.run(c, capture_output=True, timeout=120, creationflags=0x08000000)
            if p.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 44:
                return dst
            last = (p.stderr or b"").decode("utf-8", "ignore")[-200:]
        except Exception as e:
            last = repr(e)
    raise RuntimeError("转码失败（ffmpeg）: %s" % last)


# ---------- 主流程 ----------

def send_voice(text, *, tts_fn, ffmpeg="ffmpeg", out_device=None, tail_ms=350, log=print):
    """合成 + 按住 Alt 播放 + 松开。返回 dict 说明结果。"""
    steps = []
    if not str(text or "").strip():
        return {"ok": False, "error": "要念的内容是空的", "steps": steps}

    hwnd, title = find_wechat_window()
    if not hwnd:
        return {"ok": False, "error": "没找到微信窗口（微信没开？）", "steps": steps}
    steps.append("微信窗口：%s" % title)

    if not focus_window(hwnd):
        return {"ok": False, "error": "微信没能切到前台，拒绝盲按键", "steps": steps}
    steps.append("已切到前台")

    wav = tts_fn(text)
    if not wav:
        return {"ok": False, "error": "语音合成失败", "steps": steps}
    steps.append("合成完成：%s" % os.path.basename(wav))

    pcm = os.path.join(os.path.dirname(wav), "ptt_" + os.path.splitext(os.path.basename(wav))[0] + ".wav")
    try:
        to_pcm_wav(wav, pcm, ffmpeg=ffmpeg)
        steps.append("已转 PCM：%s" % os.path.basename(pcm))
    except Exception as e:
        return {"ok": False, "error": "转码失败：" + str(e), "steps": steps}

    try:
        duration, dev_name = play_wav(pcm, out_device)
        steps.append("试播成功：%.1fs → %s" % (duration, dev_name))
    except Exception as e:
        return {"ok": False, "error": "播放失败：" + str(e), "steps": steps}

    # 微信要求按住至少约 1 秒，太短会提示「说话时间太短」
    hold_s = max(1.2, duration + tail_ms / 1000.0)

    try:
        alt_down()
        steps.append("Alt 按下，开始录")
        t0 = time.time()
        # 先放一小段静音让微信进入录音，再播正文
        time.sleep(0.2)
        play_wav(pcm, out_device)
        # 补足到 hold_s
        while time.time() - t0 < hold_s:
            time.sleep(0.02)
        alt_up()
        steps.append("Alt 松开（按住 %.1fs）" % (time.time() - t0))
    except Exception as e:
        return {"ok": False, "error": "按住说话过程出错：" + str(e), "steps": steps}
    finally:
        key_up_safe()

    time.sleep(0.4)
    return {"ok": True, "steps": steps, "seconds": round(hold_s, 1), "device": out_device}


# ---------- 自检（不发消息） ----------

def selftest():
    ok = True
    print("== 微信窗口 ==")
    hwnd, title = find_wechat_window()
    if hwnd:
        print("  找到：%s（hwnd=%s）" % (title, hwnd))
    else:
        print("  没找到微信窗口")
        ok = False

    print("== 权限 ==")
    for line in elevation_report():
        print(line)

    print("== 播放设备 ==")
    outs = list_outputs()
    for i, name in outs:
        print("  [%d] %s" % (i, name))
    if not outs:
        print("  没有播放设备")
        ok = False

    print("== 录音设备（微信麦克风应该是其中一条）==")
    for i, name in list_inputs():
        print("  [%d] %s" % (i, name))

    print("== 虚拟声卡提示 ==")
    names = " ".join(n.lower() for _, n in outs)
    if "cable" in names or "virtual" in names or "vb-audio" in names:
        print("  发现虚拟声卡，可以用它把声音送进微信")
    else:
        print("  没发现虚拟声卡：")
        print("    · 装 VB-CABLE 后会出现 CABLE Input/Output")
        print("    · 或启用系统「立体声混音」（声音设置 → 录制）")
        print("    · 微信麦克风选 CABLE Output / 立体声混音，我们把声音播到 CABLE Input")
    print("")
    print("结果：" + ("可用" if ok else "有项目没通过，见上面"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--play" in sys.argv:
        # 播放指定 wav 到指定设备：--play file.wav --device 3
        path = sys.argv[sys.argv.index("--play") + 1]
        dev = WAVE_MAPPER
        if "--device" in sys.argv:
            dev = int(sys.argv[sys.argv.index("--device") + 1])
        secs, name = play_wav(path, dev)
        print("played %.2fs -> %s" % (secs, name))
    else:
        sys.exit(selftest())
