"""陌生人限制：回话次数 / 图片 / 语音。

用户要求：对陌生人对话要有可设定的限制（回话次数、图片收入等）。

规则（都在 config.json 的 stranger 段里配）：
  enabled         总开关
  maxRepliesPerDay 每天最多回几次（0 = 不限）
  allowImages     允不允许给她发图（陌生人发的图不收藏、不识别）
  allowVoice      允不允许语音回复陌生人
  maxImagesPerDay 每天最多收几张图（0 = 不限）

计数按「每天 + 每个陌生人」分别记，落盘 data/stranger.json，重启不清零。
确定是主人（owner）或白名单里的人不受这些限制。
"""
from __future__ import annotations

import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "data", "stranger.json")


def _today():
    return time.strftime("%Y-%m-%d")


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            j = json.load(f) or {}
    except Exception:
        j = {}
    if j.get("day") != _today():
        # 换天了，计数清零
        return {"day": _today(), "replies": {}, "images": {}}
    j.setdefault("replies", {})
    j.setdefault("images", {})
    return j


def save_state(st):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _cfg(cfg):
    return (cfg or {}).get("stranger") or {}


def check_reply(username, cfg):
    """能不能回这个人。返回 (ok, reason)。"""
    c = _cfg(cfg)
    if c.get("enabled") is False:
        return True, ""
    limit = int(c.get("maxRepliesPerDay") or 0)
    if limit <= 0:
        return True, ""
    st = load_state()
    used = int((st["replies"] or {}).get(str(username)) or 0)
    if used >= limit:
        return False, "今天的回话次数已用完（%d/%d）" % (used, limit)
    return True, ""


def note_reply(username, cfg=None):
    """记一次回话。"""
    c = _cfg(cfg)
    if c.get("enabled") is False:
        return
    st = load_state()
    st["replies"][str(username)] = int((st["replies"] or {}).get(str(username)) or 0) + 1
    save_state(st)


def check_image(username, cfg):
    """能不能接收/处理这个人发的图。返回 (ok, reason)。"""
    c = _cfg(cfg)
    if c.get("enabled") is False:
        return True, ""
    if c.get("allowImages") is False:
        return False, "设置里关了「接收陌生人的图」"
    limit = int(c.get("maxImagesPerDay") or 0)
    if limit <= 0:
        return True, ""
    st = load_state()
    used = int((st["images"] or {}).get(str(username)) or 0)
    if used >= limit:
        return False, "今天收图已达上限（%d/%d）" % (used, limit)
    return True, ""


def note_image(username, cfg=None):
    c = _cfg(cfg)
    if c.get("enabled") is False:
        return
    st = load_state()
    st["images"][str(username)] = int((st["images"] or {}).get(str(username)) or 0) + 1
    save_state(st)


def allow_voice(username, cfg):
    """陌生人允不允许收到语音。"""
    c = _cfg(cfg)
    if c.get("enabled") is False:
        return True
    return c.get("allowVoice") is not False


def stats(username, cfg=None):
    st = load_state()
    return {
        "day": st.get("day"),
        "replies": int((st["replies"] or {}).get(str(username)) or 0),
        "images": int((st["images"] or {}).get(str(username)) or 0),
    }
