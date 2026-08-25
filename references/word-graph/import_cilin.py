#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词林导入图库（一次性）：references/word-graph/lexicon.axeb

把同义词词林扩展版（txt）与情绪/场景种子锚点（seed-map.json）导入 axolotl 图库。
图库是唯一真源；cilin-extended.txt 仅作兜底备选（文件版）。

图结构：
- word_{词}   (type=word,    属性: len/ban/first_char)
- class_{编码} (type=semclass, 属性: code/size)
- emotion_{名} (type=emotion) —— seed-map.json 的情绪锚点
- scene_{名}   (type=scene)   —— seed-map.json 的场景锚点
- word -belongs_to-> class   （词属于语义类；一词多义=多条边）
- emotion/scene -seed_of-> word（情绪/场景锚点种子词，一次导入后查询纯走图）

用法: python3 import_cilin.py [词林txt] [seed-map.json]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph  # noqa: E402

CILIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "word-injector", "cilin-extended.txt")
SEED_MAP = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "word-injector", "seed-map.json")
DB = os.path.join(HERE, "lexicon.axeb")
BAIHUA_LEXICON = os.path.join(HERE, "..", "baihua-lexicon.json")

# 文言硬错词（禁词表复用——标 ban 属性，查询时排除）
try:
    with open(BAIHUA_LEXICON, encoding="utf-8") as f:
        _lex = json.load(f)
    BAN_WORDS = set(_lex.get("words", {}).keys()) | set(_lex.get("dialogue_only", {}).keys())
except FileNotFoundError:
    BAN_WORDS = set()


def code_clean(code: str) -> str:
    """去尾部符号（#/@）→ 纯编码"""
    return re.sub(r"[#@]$", "", code.strip())


def main():
    if os.path.exists(DB):
        os.remove(DB)  # 重新导入 = 重建
    mg = MemoryGraph(DB)

    # 1. 语义类节点 + 词节点 + belongs_to 边
    n_word = n_class = n_edge = 0
    with open(CILIN, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or "=" not in ln:
                continue
            code, _, rest = ln.partition("=")
            code = code_clean(code)
            words = [w.strip() for w in rest.split() if w.strip()]
            if not words:
                continue
            # 语义类节点
            cid = f"class_{code}"
            if mg.get_vertex(cid) is None:
                mg.upsert_vertex({
                    "id": cid, "type": "semclass", "status": "live", "domain": "lexicon",
                    "label": f"语义类 {code}", "code": code,
                })
                n_class += 1
            # 词节点 + 边
            for w in words:
                wid = f"word_{w}"
                if mg.get_vertex(wid) is None:
                    mg.upsert_vertex({
                        "id": wid, "type": "word", "status": "live", "domain": "lexicon",
                        "label": w, "word": w, "len": len(w),
                        "ban": 1 if w in BAN_WORDS else 0,
                    })
                    n_word += 1
                if mg.add_edge(wid, cid, kind="belongs_to", domain="lexicon"):
                    n_edge += 1

    # 2. 维度锚点（seed-map 所有 *_seeds 组 → {前缀}_{子类} 节点 + seed_of 边）
    #    2026-08-26 泛化：emotion/scene/person/action/env/season/obj/sense 全支持
    with open(SEED_MAP, encoding="utf-8") as f:
        seeds = json.load(f)
    n_dim = n_seed = 0
    for group, subclasses in seeds.items():
        if not group.endswith("_seeds"):
            continue
        prefix = group[:-len("_seeds")]  # emotion/scene/person/action/env/season/obj/sense
        for sub, words in subclasses.items():
            nid = f"{prefix}_{sub}"
            mg.upsert_vertex({
                "id": nid, "type": prefix, "status": "live", "domain": "lexicon",
                "label": f"{prefix}·{sub}", "name": sub,
            })
            n_dim += 1
            for w in words:
                if mg.get_vertex(f"word_{w}") and mg.add_edge(nid, f"word_{w}", kind="seed_of", domain="lexicon"):
                    n_seed += 1

    mg.close()
    size_mb = os.path.getsize(DB) / 1024 / 1024
    print(f"✅ 图库建成: {DB}")
    print(f"   词节点 {n_word} / 语义类 {n_class} / 维度锚点 {n_dim} / belongs_to 边 {n_edge} / seed_of 边 {n_seed}")
    print(f"   文件大小 {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
