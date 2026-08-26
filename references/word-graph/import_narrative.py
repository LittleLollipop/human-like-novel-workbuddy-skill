#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""叙事手法库导入图库（一次性）：dialogue/opening/action/suspense/scene/comedy → lexicon.axeb

- narrative_{库}_{手法名} (type=narrative, 属性: lib/name/formula/examples/scene/note)
用法: python3 import_narrative.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")
LIBS = ["dialogue", "opening", "action", "suspense", "scene", "comedy"]
LABELS = {"dialogue": "对话技术", "opening": "开篇/黄金三章", "action": "战斗动作",
          "suspense": "悬念反转", "scene": "场景构建", "comedy": "喜剧手法"}


def main():
    mg = MemoryGraph(DB)
    n = 0
    for lib in LIBS:
        with open(os.path.join(HERE, f"{lib}.json"), encoding="utf-8") as f:
            data = json.load(f)
        for t in data.get("techniques", []):
            pid = f"narrative_{lib}_{t['name']}"
            mg.upsert_vertex({
                "id": pid, "type": "narrative", "status": "live", "domain": "lexicon",
                "label": f"{LABELS[lib]}·{t['name']}", "lib": lib, "name": t["name"],
                "formula": t.get("formula", ""),
                "examples": json.dumps(t.get("examples", []), ensure_ascii=False),
                "scene": json.dumps(t.get("scene", []), ensure_ascii=False),
                "note": t.get("note", ""),
            })
            n += 1
    mg.close()
    print(f"✅ 叙事手法库导入完成: {n} 节点（{'/'.join(LIBS)}）")


if __name__ == "__main__":
    main()
