"""一次性补丁：面板启动时忽略 Ctrl+C。

原因：用户点一下适配器窗口（想复制日志）容易按到 Ctrl+C，
桥接就把 KeyboardInterrupt 当退出信号，直接退出 —— 表现为「窗口一点就显示适配器退出」。

做法：面板启动时设 YF_NO_SIGINT=1，桥接看到就忽略 SIGINT。
手动双击启动时照旧（Ctrl+C 仍然能退出）。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'YF_NO_SIGINT' in src:
    print('已经处理过了')
    raise SystemExit(0)

anchor = 'def main():\n    boot("进入 main()")'

patch = '''def main():
    boot("进入 main()")

    # 由面板启动时忽略 Ctrl+C：点窗口复制日志很容易误触，一按就把桥接退掉了。
    # 手动双击启动时不设这个变量，Ctrl+C 照旧能退出。
    if os.environ.get("YF_NO_SIGINT") == "1":
        try:
            import signal as _signal

            _signal.signal(_signal.SIGINT, _signal.SIG_IGN)
            log("（面板启动：已忽略 Ctrl+C；要停止请点面板「停止」或关掉本窗口）")
        except Exception:
            pass
'''

if anchor not in src:
    print('没找到 main() 开头')
    raise SystemExit(1)

src = src.replace(anchor, patch, 1)
io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已让桥接在面板启动时忽略 Ctrl+C')
