import io
import json

P = "config.json"
with io.open(P, encoding="utf-8") as f:
    j = json.load(f)

if "stranger" not in j:
    j["stranger"] = {
        "enabled": True,
        "maxRepliesPerDay": 20,
        "allowImages": True,
        "allowVoice": True,
        "maxImagesPerDay": 50,
    }
    with io.open(P, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("已写入 stranger 配置")
else:
    print("stranger 配置已存在")
