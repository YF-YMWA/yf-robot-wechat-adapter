"""单独验证 waveIn 录音能不能拿到数据。"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time

sys.path.insert(0, ".")
import voice_ptt as V

winmm = V.winmm


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


def rec(idx, seconds=1.0, rate=16000):
    fmt = V.WAVEFORMATEX(1, 1, rate, rate * 2, 2, 16, 0)
    h = ctypes.c_void_p()
    rc = winmm.waveInOpen(ctypes.byref(h), idx, ctypes.byref(fmt), 0, 0, 0)
    print("    waveInOpen rc=%s" % rc)
    if rc != 0:
        return None

    total = int(seconds * rate * 2)
    buf = ctypes.create_string_buffer(total)
    hdr = WAVEHDR()
    hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
    hdr.dwBufferLength = total

    rc1 = winmm.waveInPrepareHeader(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
    rc2 = winmm.waveInStart(h)
    print("    prepare=%s start=%s" % (rc1, rc2))
    time.sleep(seconds + 0.3)
    winmm.waveInStop(h)
    time.sleep(0.15)
    n = hdr.dwBytesRecorded
    flags = hdr.dwFlags
    winmm.waveInUnprepareHeader(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
    winmm.waveInClose(h)
    print("    录到字节=%s flags=0x%x" % (n, flags))

    pcm = bytes(buf.raw[: n or 0])
    if len(pcm) >= 2:
        cnt = len(pcm) // 2
        vals = struct.unpack("<%dh" % cnt, pcm[: cnt * 2])
        rms = (sum(v * v for v in vals) / cnt) ** 0.5
        peak = max(abs(v) for v in vals)
        print("    RMS=%.0f 峰值=%d" % (rms, peak))
    return pcm


for i, name in V.list_inputs():
    print("  [%d] %s" % (i, name))
    try:
        rec(i, 1.0)
    except Exception as e:
        print("    失败:", repr(e))
