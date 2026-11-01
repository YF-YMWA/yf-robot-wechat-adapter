"""把「播放端 × 录音端」的组合都试一遍，看哪条线能把声音送进麦克风。"""
import sys

sys.path.insert(0, ".")
import check_loopback as L
import voice_ptt as V

outs = V.list_outputs()
ins = V.list_inputs()

print("  播放端:", [(i, n) for i, n in outs])
print("  录音端:", [(i, n) for i, n in ins])
print("")

tone, rate = L.make_tone(1.2)

for oi, oname in outs:
    for ii, iname in ins:
        base = L.rms(L.record(ii, 0.5, rate=rate))
        import threading, time, ctypes

        def play():
            fmt = V.WAVEFORMATEX(1, 1, rate, rate * 2, 2, 16, 0)
            h = ctypes.c_void_p()
            if V.winmm.waveOutOpen(ctypes.byref(h), oi, ctypes.byref(fmt), 0, 0, 0) != 0:
                return
            try:
                buf = ctypes.create_string_buffer(tone, len(tone))
                hdr = L.WAVEHDR()
                hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
                hdr.dwBufferLength = len(tone)
                V.winmm.waveOutPrepareHeader(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
                V.winmm.waveOutWrite(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
                time.sleep(1.3)
                V.winmm.waveOutReset(h)
                V.winmm.waveOutUnprepareHeader(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
            finally:
                V.winmm.waveOutClose(h)

        t = threading.Thread(target=play)
        t.start()
        time.sleep(0.2)
        got = L.rms(L.record(ii, 1.2, rate=rate))
        t.join()

        mark = "[OK] 通" if got > max(60, base * 2.2) else "—"
        print("  out[%d] %-30s → in[%d] %-28s 本底%4.0f 录到%5.0f %s"
              % (oi, oname[:28], ii, iname[:26], base, got, mark))
