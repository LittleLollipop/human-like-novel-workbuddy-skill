#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通识典故库导入图库：allusion.json → lexicon.axeb

- allusion_{名} (type=allusion, 属性: name/type/sub_type/source/story/meaning/mood/scene/familiarity/note)
  sub_type = 成语典故/经文名句/历史典故

用法: python3 import_allusion.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")


def main():
    mg = MemoryGraph(DB)
    with open(os.path.join(HERE, "allusion.json"), encoding="utf-8") as f:
        data = json.load(f)

    n = 0
    for t in data.get("allusions", []):
        mg.upsert_vertex({
            "id": f"allusion_{t['name']}", "type": "allusion", "status": "live", "domain": "lexicon",
            "label": f"典故·{t['name']}", "name": t["name"],
            "sub_type": t.get("type", "成语典故"),
            "source": t.get("source", ""),
            "story": t.get("story", ""),
            "meaning": t.get("meaning", ""),
            "mood": json.dumps(t.get("mood", []), ensure_ascii=False),
            "scene": json.dumps(t.get("scene", []), ensure_ascii=False),
            "familiarity": t.get("familiarity", "中"),
            "note": t.get("note", ""),
        })
        n += 1

    mg.close()
    print(f"✅ 通识典故库导入完成: {n} 节点（allusion）")


if __name__ == "__main__":
    main()
