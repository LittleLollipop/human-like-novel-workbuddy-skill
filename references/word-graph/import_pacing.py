#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""节奏库导入图库（一次性）：pacing.json → lexicon.axeb

- pacing_{体系} (type=pacing, 属性: label/level/beats JSON/micro)
用法: python3 import_pacing.py
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
    with open(os.path.join(HERE, "pacing.json"), encoding="utf-8") as f:
        data = json.load(f)

    n = 0
    # 宏观体系
    for key, sysinfo in data["macro"].items():
        mg.upsert_vertex({
            "id": f"pacing_{key}", "type": "pacing", "status": "live", "domain": "lexicon",
            "label": sysinfo["label"], "name": key,
            "level": sysinfo.get("level", ""),
            "beats": json.dumps(sysinfo.get("beats", []), ensure_ascii=False),
        })
        n += 1
    # 微观规则
    micro = data.get("micro", {})
    mg.upsert_vertex({
        "id": "pacing_micro", "type": "pacing", "status": "live", "domain": "lexicon",
        "label": micro.get("label", "章节级节奏规则"),
        "name": "micro",
        "level": "chapter",
        "rules": json.dumps(micro.get("rules", []), ensure_ascii=False),
    })
    n += 1

    mg.close()
    print(f"✅ 节奏库导入完成: {n} 节点（宏观 {len(data['macro'])} 体系 + 微观规则）")


if __name__ == "__main__":
    main()
