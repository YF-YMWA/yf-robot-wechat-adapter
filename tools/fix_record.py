"""修正录音：必须先 waveInAddBuffer 再 waveInStart。

否则 dwBytesRecorded 一直是 0 —— 看起来像「没声音」，其实是缓冲区没提交。
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_loopback.py")
s = io.open(P, encoding="utf-8").read()

old = """        if winmm.waveInPrepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr)) != 0:
            raise OSError("prepare 失败")
        if winmm.waveInStart(handle) != 0:
            raise OSError("start 失败")"""

new = """        if winmm.waveInPrepareHeader(handle, ctypes.byref(hdr), ctypes.sizeof(hdr)) != 0:
            raise OSError("prepare 失败")
        # 关键：录音必须先把缓冲区交给驱动，否则 dwBytesRecorded 永远是 0
        if winmm.waveInAddBuffer(handle, ctypes.byref(hdr), ctypes.sizeof(hdr)) != 0:
            raise OSError("AddBuffer 失败")
        if winmm.waveInStart(handle) != 0:
            raise OSError("start 失败")"""

if old not in s:
    print("未命中")
    sys.exit(1)

s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已补 waveInAddBuffer")
