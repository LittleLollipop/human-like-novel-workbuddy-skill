#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技法库导入图库（一次性）：rhetoric/imagery/transition/voice → lexicon.axeb

图库优先（2026-08-26 用户拍板：技法库也主推图库，无图库时文件兜底）：
- rhetoric_{名}   (type=rhetoric,  属性: formula/examples/mood/scene/freq/note) -fits-> emotion_/scene_
- imagery_{场景}  (type=imagery,  属性: items 列表)（命名即场景，不连锚点）
- transition_{名} (type=transition, 属性: formula/examples/where/note)
- voice           (type=voice,    属性: interjections/design)

用法: python3 import_craft.py [word-graph目录]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    mg = MemoryGraph(DB)

    # 1. 修辞（连 fits 边）
    n = n_edge = 0
    for r in load("rhetoric.json")["rhetorics"]:
        pid = f"rhetoric_{r['name']}"
        mg.upsert_vertex({
            "id": pid, "type": "rhetoric", "status": "live", "domain": "lexicon",
            "label": f"修辞·{r['name']}", "name": r["name"],
            "formula": r["formula"],
            "examples": json.dumps(r.get("examples", []), ensure_ascii=False),
            "mood": json.dumps(r.get("mood", []), ensure_ascii=False),
            "scene": json.dumps(r.get("scene", []), ensure_ascii=False),
            "freq": r.get("freq", ""), "note": r.get("note", ""),
        })
        n += 1
        for emo in r.get("mood", []):
            if mg.get_vertex(f"emotion_{emo}") and mg.add_edge(pid, f"emotion_{emo}", kind="fits", domain="lexicon"):
                n_edge += 1
        for sc in r.get("scene", []):
            if mg.get_vertex(f"scene_{sc}") and mg.add_edge(pid, f"scene_{sc}", kind="fits", domain="lexicon"):
                n_edge += 1

    # 2. 物象（命名即场景）
    for k, items in load("imagery.json")["imagery"].items():
        mg.upsert_vertex({
            "id": f"imagery_{k}", "type": "imagery", "status": "live", "domain": "lexicon",
            "label": f"物象·{k}", "name": k,
            "items": json.dumps(items, ensure_ascii=False),
        })
        n += 1

    # 3. 转场
    for t in load("transition.json")["transitions"]:
        pid = f"transition_{t['name']}"
        mg.upsert_vertex({
            "id": pid, "type": "transition", "status": "live", "domain": "lexicon",
            "label": f"转场·{t['name']}", "name": t["name"],
            "formula": t["formula"],
            "examples": json.dumps(t.get("examples", []), ensure_ascii=False),
            "where": t.get("where", ""), "note": t.get("note", ""),
        })
        n += 1

    # 4. 声口（全局一个节点）
    v = load("voice.json")
    mg.upsert_vertex({
        "id": "voice", "type": "voice", "status": "live", "domain": "lexicon",
        "label": "声口·通用语料",
        "interjections": json.dumps(v["interjections"], ensure_ascii=False),
        "design": json.dumps(v["design"], ensure_ascii=False),
    })
    n += 1

    mg.close()
    print(f"✅ 技法库导入完成: {n} 节点 / {n_edge} 条 fits 边（修辞连情绪/场景锚点）")


if __name__ == "__main__":
    main()
