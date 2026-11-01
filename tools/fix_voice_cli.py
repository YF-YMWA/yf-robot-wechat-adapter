"""修 voice_test_cli：
  1. 检查控件树之前先收起自己的控制台（否则点击坐标落在控制台上：
     「落点窗口不属于微信（进程 XXXX != 1768）」）
  2. 参数中文乱码（bat 是 GBK、控制台是 UTF-8）→ 检测到乱码就用内置默认值
"""
import io

P = "voice_test_cli.py"
s = io.open(P, encoding="utf-8").read()

# 1. 乱码兜底 + 控制台最小化
old_main = '''def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "测试语音条，听到就说明成功了"
    chat = sys.argv[2] if len(sys.argv) > 2 else "文件传输助手"
    dev = int(sys.argv[3]) if len(sys.argv) > 3 else 0'''

new_main = '''def _looks_garbled(s):
    """GBK 参数在 UTF-8 控制台下会变成 ???????，这种就别用了。"""
    if not s:
        return True
    bad = sum(1 for ch in s if ch in "?\\ufffd")
    return bad >= max(2, len(s) // 3)


def main():
    default_text = "这是一条测试语音，听到就说明成功了"
    default_chat = "文件传输助手"

    text = sys.argv[1] if len(sys.argv) > 1 else default_text
    chat = sys.argv[2] if len(sys.argv) > 2 else default_chat
    dev = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    if _looks_garbled(text):
        print("  [!] 传入的文字是乱码（bat 编码问题），改用内置默认句子")
        text = default_text
    if _looks_garbled(chat):
        chat = default_chat'''

assert old_main in s
s = s.replace(old_main, new_main, 1)

# 2. 检查控件树之前收起控制台
old_check = '''    # 先看控件树通不通（通了才能切聊天）
    print("  检查微信控件树…")
    from wechatauto import WeChatGUI'''

new_check = '''    # 检查控件树之前，先把我们自己的控制台收起来。
    # 否则 UIA 点击会落在控制台上：「落点窗口不属于微信（进程 != 微信）」
    V.minimize_our_console()
    time.sleep(0.3)

    # 先看控件树通不通（通了才能切聊天）
    print("  检查微信控件树…")
    from wechatauto import WeChatGUI'''

assert old_check in s
s = s.replace(old_check, new_check, 1)

# 3. 结束还原控制台
s = s.replace(
    '''if __name__ == "__main__":
    sys.exit(main())''',
    '''if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        try:
            V.restore_our_console()
        except Exception:
            pass''',
)

# 4. 需要 time
if "\nimport time\n" not in s:
    s = s.replace("import os\nimport sys", "import os\nimport sys\nimport time", 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("已改：乱码兜底 + 检查前收起控制台 + 结束还原")
