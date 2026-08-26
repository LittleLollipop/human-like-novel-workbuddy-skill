#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""非学院派补充库导入图库（一次性）：punch/antipattern/master_style → lexicon.axeb

- punch_{名}         (type=punch,        source=网文编辑方法论)
- antipattern_{名}   (type=antipattern,  source=网文读者共识)
- master_{名}        (type=narrative, lib=master_style, source=作家名)

所有条目带 source 字段（2026-08-26 用户要求：标明来源，写严肃文学时可按来源筛选）。
用法: python3 import_supplement.py
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
    n = 0

    # 1. punch（爽点引擎）
    with open(os.path.join(HERE, "punch.json"), encoding="utf-8") as f:
        data = json.load(f)
    for t in data.get("techniques", []):
        mg.upsert_vertex({
            "id": f"punch_{t['name']}", "type": "punch", "status": "live", "domain": "lexicon",
            "label": f"爽点·{t['name']}", "name": t["name"],
            "source": t.get("source", "网文编辑方法论"),
            "formula": t.get("formula", ""),
            "examples": json.dumps(t.get("examples", []), ensure_ascii=False),
            "scene": json.dumps(t.get("scene", []), ensure_ascii=False),
            "note": t.get("note", ""),
        })
        n += 1

    # 2. antipattern（毒点反例）
    with open(os.path.join(HERE, "antipattern.json"), encoding="utf-8") as f:
        data = json.load(f)
    for t in data.get("antipatterns", []):
        mg.upsert_vertex({
            "id": f"antipattern_{t['name']}", "type": "antipattern", "status": "live", "domain": "lexicon",
            "label": f"毒点·{t['name']}", "name": t["name"],
            "source": t.get("source", "网文读者共识"),
            "formula": t.get("formula", ""),
            "examples": json.dumps(t.get("examples", []), ensure_ascii=False),
            "note": t.get("note", ""),
        })
        n += 1

    # 3. master_style（名家风，并入 narrative lib=master_style）
    with open(os.path.join(HERE, "master_style.json"), encoding="utf-8") as f:
        data = json.load(f)
    for t in data.get("techniques", []):
        mg.upsert_vertex({
            "id": f"narrative_master_{t['name']}", "type": "narrative", "status": "live", "domain": "lexicon",
            "label": f"名家风·{t['name']}", "lib": "master_style", "name": t["name"],
            "source": t.get("source", ""),
            "formula": t.get("formula", ""),
            "examples": json.dumps(t.get("examples", []), ensure_ascii=False),
            "scene": json.dumps(t.get("scene", []), ensure_ascii=False),
            "note": t.get("note", ""),
        })
        n += 1

    mg.close()
    print(f"✅ 补充库导入完成: {n} 节点（punch {len(json.load(open(os.path.join(HERE,'punch.json'), encoding='utf-8'))['techniques'])} / antipattern {len(json.load(open(os.path.join(HERE,'antipattern.json'), encoding='utf-8'))['antipatterns'])} / master {len(json.load(open(os.path.join(HERE,'master_style.json'), encoding='utf-8'))['techniques'])}）")


if __name__ == "__main__":
    main()
