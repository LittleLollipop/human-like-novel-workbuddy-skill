#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量成语库导入图库：新华成语数据集（chinese-xinhua，30,895 条）→ lexicon.axeb

- idiom_{word} (type=idiom, 属性: word/pinyin/explanation/derivation/example/abbreviation)

与精选池（type=allusion，230 条带 mood/scene 标签）分工：
- 精选池 = 写 plan 按情绪/场景过滤（主用）
- 全量池 = 按关键词搜索/随机抽取（扩充候选、查冷门）

用法: python3 import_idiom.py /path/to/idiom.json
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")
SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/idiom.json"


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    print(f"加载 {len(data)} 条成语")

    mg = MemoryGraph(DB)
    t0 = time.time()
    n = 0
    batch = 0
    for d in data:
        w = d.get("word", "")
        if not w:
            continue
        mg.upsert_vertex({
            "id": f"idiom_{w}", "type": "idiom", "status": "live", "domain": "lexicon",
            "label": f"成语·{w}", "word": w,
            "pinyin": d.get("pinyin", ""),
            "explanation": d.get("explanation", ""),
            "derivation": d.get("derivation", ""),
            "example": d.get("example", ""),
            "abbreviation": d.get("abbreviation", ""),
        })
        n += 1
        batch += 1
        if batch >= 5000:
            print(f"  已导入 {n}/{len(data)}（{time.time()-t0:.0f}s）", flush=True)
            batch = 0

    mg.close()
    print(f"✅ 全量成语库导入完成: {n} 节点（{time.time()-t0:.0f}s）")


if __name__ == "__main__":
    main()
