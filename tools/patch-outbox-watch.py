"""适配器加一个 outbox 轮询线程：取核心的后台作业结果并发出去。

为什么要这样：画图要十几秒，同步等会像卡死。
现在核心先回「画着呢」，画完把结果放进待发队列，
这里轮询取走 → 发微信 → 完事。不用长连接。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'wechatauto_bridge.py')

src = io.open(P, encoding='utf-8').read()

if 'def outbox_watch' in src:
    print('已打过补丁')
    raise SystemExit(0)

anchor = '    def config_watch():'

impl = '''    def outbox_watch():
        """轮询核心的后台作业结果（画图这类长任务做完会放在这里）。

        每 5 秒问一次「有没有要发的东西」。取走即清，不会重复发。
        """
        while True:
            time.sleep(5)
            try:
                if AWAY["on"] or away_active():
                    continue
                base = bot_base()
                tok = _adapter_token()
                r = requests.get(
                    base + "/api/outbox",
                    params={"chat": ""},
                    headers={"x-adapter-token": tok} if tok else {},
                    timeout=10,
                )
                if not r.ok:
                    continue
                data = r.json() or {}
                items = data.get("list") or []
                for it in items:
                    chat = str(it.get("chatId") or "")
                    text = str(it.get("text") or "").strip()
                    imgs = it.get("images") or []
                    if not chat:
                        continue
                    # chatId 可能带 private: / grp: 前缀
                    target = chat.split(":", 1)[1] if ":" in chat else chat
                    if text:
                        log("[后台] 补发一条 → %s：%s" % (target, text[:30]))
                        send_text(text, target)
                        time.sleep(0.6)
                    for name in imgs[:3]:
                        _p = resolve_media_path(name)
                        if not _p:
                            log("[后台] 图找不到：%s" % name)
                            continue
                        log("[后台] 补发图片 → %s：%s" % (target, name))
                        send_sticker(target, specific_path=_p)
                        time.sleep(0.8)
            except Exception as e:                  # noqa: BLE001
                log("后台结果轮询失败（不影响聊天）：", repr(e))

''' + anchor

if anchor not in src:
    print('找不到 config_watch')
    raise SystemExit(1)

src = src.replace(anchor, impl, 1)

# 启动线程
old_start = '''    threading.Thread(target=config_watch, daemon=True).start()'''
new_start = '''    threading.Thread(target=config_watch, daemon=True).start()
    threading.Thread(target=outbox_watch, daemon=True).start()'''

if old_start in src:
    src = src.replace(old_start, new_start, 1)
else:
    print('  [警告] 没找到 config_watch 的启动点，需手动加线程')

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已加：outbox 轮询线程')
