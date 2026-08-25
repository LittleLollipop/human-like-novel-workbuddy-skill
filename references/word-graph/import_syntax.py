#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句式范式导入图库（一次性）：把 syntax-patterns.json 导入 lexicon.axeb

复用词图的 emotion_/scene_ 锚点节点；范式节点：
- pattern_{名} (type=syntax_pattern, 属性: name/formula/examples/mood/scene/note)
- pattern -fits-> emotion_{情绪} / scene_{场景}  （适用关联）

用法: python3 import_syntax.py [patterns.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph  # noqa: E402

PATTERNS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "syntax-patterns.json")
DB = os.path.join(HERE, "lexicon.axeb")


def main():
    mg = MemoryGraph(DB)
    with open(PATTERNS, encoding="utf-8") as f:
        data = json.load(f)

    n_pat = n_edge = 0
    for p in data["patterns"]:
        pid = f"pattern_{p['name']}"
        props = {
            "id": pid, "type": "syntax_pattern", "status": "live", "domain": "lexicon",
            "label": f"句式·{p['name']}",
            "name": p["name"], "formula": p["formula"],
            "examples": json.dumps(p.get("examples", []), ensure_ascii=False),
            "mood": json.dumps(p.get("mood", []), ensure_ascii=False),
            "scene": json.dumps(p.get("scene", []), ensure_ascii=False),
            "note": p.get("note", ""),
        }
        mg.upsert_vertex(props)
        n_pat += 1
        # 适用关联：pattern -fits-> emotion_/scene_（锚点已存在则连）
        for emo in p.get("mood", []):
            eid = f"emotion_{emo}"
            if mg.get_vertex(eid) and mg.add_edge(pid, eid, kind="fits", domain="lexicon"):
                n_edge += 1
        for sc in p.get("scene", []):
            sid = f"scene_{sc}"
            if mg.get_vertex(sid) and mg.add_edge(pid, sid, kind="fits", domain="lexicon"):
                n_edge += 1

    mg.close()
    print(f"✅ 句式范式导入完成: {n_pat} 个范式 / {n_edge} 条 fits 边")


if __name__ == "__main__":
    main()
