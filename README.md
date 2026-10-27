# YF-Robot 微信适配器

> ## ⚠️ 先读这段
>
> **这个项目违反《微信个人账号使用规范》。**
>
> - 它通过 UI 自动化和读取本地数据库来操作微信，**有封号风险**
> - 仅供个人学习研究，**不要用于营销、刷屏、批量养号**
> - 出了任何问题（封号、数据丢失、法律纠纷）**自己承担**，作者不提供任何担保
> - 如果你不接受这些，请直接关掉这个页面

这是 [YF-Robot](https://github.com/your-name/yf-robot) 的微信适配器。

核心（YF-Robot）不含任何平台的登录或自动化代码，只提供一套 HTTP 协议。
这个仓库负责把微信的消息转给核心、把核心的回复发出去。

---

## 它做什么

```
微信客户端 ──(UIA / 本地数据库)──▶ 本适配器 ──(HTTP)──▶ YF-Robot 核心
                                      ▲                      │
                                      └──── bubbles ─────────┘
```

- **收消息**：读 `wechatauto-replica` 提供的事件流
- **发消息**：UIA 驱动窗口输入（`gui_lock` 串行化，避免并发崩溃）
- **图片/表情**：交给核心入库（不做本地落盘，见下文）
- **心跳**：每 20 秒报一次状态，核心的控制台靠它显示「已接入」

---

## 环境要求

- Windows（用到 UIA 和 Win32 API，别的系统跑不了）
- 微信 4.x 客户端，**窗口保持可见**，不要最小化到托盘
- Python 3.10+
- 管理员权限（读微信进程模块、操作窗口都需要）

```bash
pip install wechatauto-replica requests pillow
```

---

## 跑起来

1. 先启动核心（YF-Robot 的 `YF-Robot.bat`），确认控制台能打开
2. 复制配置：

```bash
cp config.example.json config.json
```

3. 填 `config.json`：
   - `gateway.wechat.inboundToken`：和核心 `config.json` 里的一致
   - `persona.master.wxids`：你自己的 wxid（否则她不认你）

4. 以管理员身份运行：

```bat
启动桥接.bat
```

或者直接：

```bash
python wechatauto_bridge.py
```

---

## 和核心的分工

| 事情 | 谁做 |
|---|---|
| 收消息、发消息 | 本适配器 |
| 图片/表情**存哪** | **核心**（通过 `POST /api/media/ingest`） |
| 白名单判断 | **核心**（本适配器只传 `senderId`/`chatId`） |
| 去重、打情绪标签 | **核心** |
| 人设、记忆、模型调用 | **核心** |

> 为什么图片不自己存：
> 适配器和核心是两个目录、两个进程。适配器自己写 `data/`，
> 结果是核心的控制台里看不到这些图（「收藏了但素材库里没有」）。
> 所以字节一律上传，存不存、存哪、算不算重复，全部由核心决定。

这样做的另一个好处：白名单只有一处实现，不会两边判断不一致。

---

## 配置说明

见 `config.example.json` 里的注释。几个关键的：

| 字段 | 作用 |
|---|---|
| `gateway.wechat.inboundToken` | 和核心对接的口令，必须一致 |
| `persona.master.wxids` | 主人 wxid，决定谁能指挥她 |
| `wechat.stickerChance` | 回复后补一个表情包的概率 |
| `wechat.staleAfterSec` | 多久之前的消息不回复（避免回上一条） |
| `wechat.ignoreSenders` | 忽略这些联系人 |
| `wechat.gameWhitelist` | 哪些游戏运行时暂停回复 |

收藏白名单**不在这里配**了 —— 那是核心的设置，在控制台「主人设置」里改。

---

## 崩溃了怎么办

UIA / COM 偶发原生崩溃（`0x80010108`、access violation），这是 Windows
自动化本身的问题，Python 层拦不住。

启动脚本会 5 秒后自动重启，最多连试 8 次；
连崩 8 次就停下，并提示你去看 `data/bridge-crash.log`。

碰到这种情况把崩溃日志最后一段发出来。

---

## 文件

```
wechatauto_bridge.py    主程序
media_store.py          本地兜底用的素材存取（正常情况走核心）
msg_route.py            消息类型路由（文本/图片/表情/链接）
wechat_xml.py           微信 XML 解析
uia_compat.py           UIA 兼容补丁
diagnose.py             环境诊断
tests/                  单元测试
```

---

## 许可

MIT。但请注意开头那段风险声明 —— **许可证不代表微信允许你这么用**。
