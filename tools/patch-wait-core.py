"""适配器启动时先等核心就绪，别在核心没起的时候空转。

事故：今早 09:34 适配器起来了，但核心（YF-Robot）没起（昨晚关机后没自启）。
于是每收到一条微信消息就请求 8899 失败，日志刷
  ConnectionError ... WinError 10061 由于目标计算机积极拒绝
用户看到的是「她在微信里不回话」，日志里看不出该去启动核心。
"""
import io

P = 'wechatauto_bridge.py'
s = io.open(P, encoding='utf-8').read()

if 'def wait_for_core' in s:
    print('已打过补丁')
    raise SystemExit(0)

anchor = '    threading.Thread(target=self_check, daemon=True).start()'

new = '''    def wait_for_core(timeout=90):
        """等核心就绪（最多 timeout 秒）。

        核心没起的时候，适配器能做的一切都是徒劳 —— 收得到消息、回不出话。
        与其让用户对着一堆 ConnectionError 猜，不如明确告诉他要先启动核心。
        """
        import time as _t

        url = bot_base().rstrip("/") + "/api/bridge/hello"
        t0 = _t.time()
        last_note = 0.0
        while _t.time() - t0 < timeout:
            try:
                import requests as _rq

                r = _rq.get(url, timeout=3)
                if r.status_code < 500:
                    if _t.time() - t0 > 2:
                        log("核心已就绪（等了 %.1f 秒）" % (_t.time() - t0))
                    return True
            except Exception:
                pass
            if _t.time() - last_note > 10:
                last_note = _t.time()
                log("等核心启动中…（已等 %d 秒）YF-Robot 没在跑？先双击 YF-Robot.bat"
                    % int(_t.time() - t0))
            _t.sleep(2)
        return False

    # 启动前 90 秒内等核心；等不到就明确报错退出，别让它带着一个死端口继续跑
    if not wait_for_core(90):
        log("=" * 46)
        log("核心（YF-Robot）没启动，适配器无法工作。")
        log("请先双击 YF-Robot 文件夹里的 YF-Robot.bat，再启动本程序。")
        log("（如果你用了开机自启，检查一下自启项有没有生效）")
        log("=" * 46)
        return 3

''' + anchor

if anchor not in s:
    print('找不到 self_check 启动点')
    raise SystemExit(1)

s = s.replace(anchor, new, 1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('已加：启动前等核心就绪')
