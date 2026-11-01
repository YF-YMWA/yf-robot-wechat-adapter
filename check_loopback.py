"""验证某个虚拟设备能不能环回：播上一条，录下一条，看录到的有没有声音。

用法：python check_loopback.py <out_index> <in_index>
"""
import ctypes
import ctypes.wintypes as wt
import math
import struct
import sys
import threading
import time

import voice_ptt as V

winmm = V.winmm
WAVE_FORMAT_PCM = 1
WAVE_MAPPER = -1


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


def make_tone(seconds=1.0, rate=16000, freq=440.0, amp=0.35):
    n = int(seconds * rate)
    data = bytearray()
    for i in range(n):
        v = int(amp * 32767 * math.sin(2 * math.pi * freq * i / rate))
        data += struct.pack("<h", v)
    return bytes(data), rate


def record(device_index, seconds, rate=16000, ch=1, bits=16):
    """录一段，返回 PCM 字节。"""
    fmt = V.WAVEFORMATEX(WAVE_FORMAT_PCM, ch, rate, rate * ch * bits // 8, ch * bits // 8, bits, 0)
    handle = ctypes.c_void_p()
    rc = winmm.waveInOpen(ctypes.byref(handle), device_index, ctypes.byref(fmt), 0, 0, 0)
    if rc != 0:
        raise OSError("waveInOpen 失败 code=%s" % rc)

    total = int(seconds * rate * ch * bits // 8)
    buf = ctypes.create_string_buffer(total + 4096)
    hdr = WAVEHDR()
    hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
    hdr.dwBufferLength = total

    try:
        if winmm.waveInPrepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr)) != 0:
            raise OSError("prepare 失败")
        if winmm.waveInAddBuffer(handle, ctypes.byref(hdr), ctypes.sizeof(hdr)) != 0:
            raise OSError("AddBuffer 失败")
        if winmm.waveInStart(handle) != 0:
            raise OSError("start 失败")
        time.sleep(seconds + 0.2)
        winmm.waveInStop(handle)
        time.sleep(0.1)
        winmm.waveInUnprepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
        return bytes(buf.raw[: hdr.dwBytesRecorded or total])
    finally:
        winmm.waveInClose(handle)


def rms(pcm):
    if len(pcm) < 2:
        return 0.0
    n = len(pcm) // 2
    vals = struct.unpack("<%dh" % n, pcm[: n * 2])
    return math.sqrt(sum(v * v for v in vals) / max(1, n))


def main():
    out_i = int(sys.argv[1])
    in_i = int(sys.argv[2])
    tone, rate = make_tone(1.2)
    print("  播放端 [%d] %s" % (out_i, dict(V.list_outputs()).get(out_i, "?")))
    print("  录音端 [%d] %s" % (in_i, dict(V.list_inputs()).get(in_i, "?")))

    # 先录本底噪音
    base = rms(record(in_i, 0.8, rate=rate))
    print("  本底噪音 RMS: %.0f" % base)

    result = {}

    def play():
        # 直接写缓冲区播放（避开文件）
        fmt = V.WAVEFORMATEX(WAVE_FORMAT_PCM, 1, rate, rate * 2, 2, 16, 0)
        handle = ctypes.c_void_p()
        rc = winmm.waveOutOpen(ctypes.byref(handle), out_i, ctypes.byref(fmt), 0, 0, 0)
        if rc != 0:
            result["err"] = "waveOutOpen code=%s" % rc
            return
        try:
            buf = ctypes.create_string_buffer(tone, len(tone))
            hdr = WAVEHDR()
            hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
            hdr.dwBufferLength = len(tone)
            winmm.waveOutPrepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            winmm.waveOutWrite(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            time.sleep(1.2)
            winmm.waveOutReset(handle)
            winmm.waveOutUnprepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
        finally:
            winmm.waveOutClose(handle)

    t = threading.Thread(target=play)
    t.start()
    time.sleep(0.2)
    got = rms(record(in_i, 1.2, rate=rate))
    t.join()

    print("  录到的 RMS: %.0f" % got)
    if result.get("err"):
        print("  播放失败:", result["err"])
        return 1
    if got > max(60, base * 2.2):
        print("  ✅ 能环回（这条线可以把声音送进麦克风）")
        return 0
    print("  ❌ 听不到 —— 这条线不通，或者需要开启「侦听此设备」")
    return 2


if __name__ == "__main__":
    sys.exit(main())
