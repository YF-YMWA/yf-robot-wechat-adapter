"""验证多开检测：把 count_weixin_main_windows 抠出来单独跑。"""
import textwrap

src = open('wechatauto_bridge.py', encoding='utf-8').read()
start = src.index('    def count_weixin_main_windows():')
end = src.index('    def find_weixin_hwnd():')
block = textwrap.dedent(src[start:end])

ns = {'log': lambda *a, **k: print('   [log]', *a)}
exec(compile(block, '<extracted>', 'exec'), ns)

n = ns['count_weixin_main_windows']()
print('  微信主窗数量:', n, '（-1 = 环境不支持，比如不是 Windows）')

if n == 1:
    print('  单开 → 允许发送（正常）')
elif n == 0:
    print('  没找到微信窗口（微信没开？）')
elif n > 1:
    print('  多开 → 会拒绝发送（防串号），这正是我们要的')
