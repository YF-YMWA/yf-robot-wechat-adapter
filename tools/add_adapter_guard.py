"""测试脚本加保护：适配器在跑就别抢同一个微信窗口。

用户实测：适配器开着的时候跑测试脚本，出现
  「落点窗口不属于微信（进程 10624 != 1768）」——点击落在适配器的控制台/进程上。
两个自动化进程同时操作同一个微信窗口，必然互相抢焦点。
"""
import io

P = "voice_test_cli.py"
s = io.open(P, encoding="utf-8").read()

if "def adapter_running(" in s:
    print("已存在")
    raise SystemExit(0)

helper = '''def adapter_running():
    """适配器（wechatauto_bridge.py）是不是正在跑。返回 PID 或 0。"""
    try:
        import subprocess

        out = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \\"Name='python.exe'\\" | "
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


def main():'''

s = s.replace("def main():", helper, 1)

# 在 main 最前面加检查
s = s.replace(
    '''    default_text = "这是一条测试语音，听到就说明成功了"''',
    '''    # 两个自动化进程会抢同一个微信窗口，必须先关掉适配器
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

    default_text = "这是一条测试语音，听到就说明成功了"''',
)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已加：适配器运行中拒绝抢窗口")
