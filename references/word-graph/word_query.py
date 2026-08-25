#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词图查询器（word-graph）：直接查图库按情绪/场景检索候选用词。

用法:
    python3 word_query.py --emotion 得意,炫耀 --scene 市集买卖 --n 12
    python3 word_query.py --emotion 恐惧 --n 8
    python3 word_query.py --scene 夜袭战斗 --n 10

查询路径（纯图，无映射表）：
    情绪: emotion_X -seed_of-> 种子词 -belongs_to-> 语义类 <-belongs_to- 候选词
    场景: scene_X   -seed_of-> 种子词 -belongs_to-> 语义类 <-belongs_to- 候选词
    情绪+场景: 两候选集合并，交集加权优先
过滤: ban 属性（文言硬错）排除；单字生僻排除；超长排除
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph, str_to_id  # noqa: E402
from engine.schema import dict_from_props  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")
RARE_SINGLE = set("尔汝吾乃遂辄弗毋勿莫须颇甚殊曰即矣哉乎兮焉乎哉厮弔拙迂谑谲骇愕矍遽亟")

KINDS = {"belongs_to", "seed_of"}


def out_words(mg, nid, kind):
    """出边指向的节点 id（限定 kind）"""
    g = mg._g
    nid_int = str_to_id(nid)
    out = []
    for tnid in g.out_neighbors(nid_int):
        e = g.get_edge(nid_int, tnid)
        if e and e[1].get("kind") == kind:
            v = g.get_vertex(tnid)
            if v and dict(v).get("status") == "live":
                out.append(dict(v)["id"])
    return out


def in_words(mg, nid, kind):
    """入边来源的节点 id（限定 kind）"""
    g = mg._g
    nid_int = str_to_id(nid)
    out = []
    for snid in g.in_neighbors(nid_int):
        e = g.get_edge(snid, nid_int)
        if e and e[1].get("kind") == kind:
            v = g.get_vertex(snid)
            if v and dict(v).get("status") == "live":
                out.append(dict(v)["id"])
    return out


def query(mg, anchors):
    """锚点节点（emotion_/scene_）→ 候选词集合 {词: 命中数}"""
    cands = {}
    for aid in anchors:
        if mg.get_vertex(aid) is None:
            print(f"⚠️ 未知锚点: {aid}", file=sys.stderr)
            continue
        seed_words = out_words(mg, aid, "seed_of")
        for sw in seed_words:
            classes = out_words(mg, sw, "belongs_to")
            for c in classes:
                for w in in_words(mg, c, "belongs_to"):
                    cands[w] = cands.get(w, 0) + 1
    return cands


def filt(mg, cands):
    out = {}
    for wid, hits in cands.items():
        v = mg.get_vertex(wid)
        if not v:
            continue
        p = dict(v)
        w = p.get("word", "")
        if p.get("ban"):
            continue
        if len(w) == 1 and w in RARE_SINGLE:
            continue
        if len(w) > 8 or any(ch in w for ch in "（）()·～-"):
            continue
        out[w] = hits
    return out


def main():
    ap = argparse.ArgumentParser(description="词图查询：按情绪/场景检索候选用词（纯图）")
    ap.add_argument("--emotion", help="情绪，逗号分隔（得意/炫耀/窘迫/慌乱/紧张/恐惧/愤怒/惊讶/无奈/疲惫/温馨/满足/轻蔑/心虚）")
    ap.add_argument("--scene", help="场景，逗号分隔（市集买卖/海上出海/夜袭战斗/酒馆闲聊/谈判要价/破屋贫寒/危机逃生）")
    ap.add_argument("--n", type=int, default=12, help="输出候选数（默认 12）")
    ap.add_argument("--word", help="直接给种子词，逗号分隔（跳过锚点，直接用词查同类词）")
    args = ap.parse_args()

    if not (args.emotion or args.scene or args.word):
        ap.error("至少给 --emotion / --scene / --word 之一")

    mg = MemoryGraph(DB)
    anchors = []
    srcs = []
    if args.emotion:
        for e in args.emotion.split(","):
            e = e.strip()
            anchors.append(f"emotion_{e}")
            srcs.append(f"情绪[{e}]")
    if args.scene:
        for s in args.scene.split(","):
            s = s.strip()
            anchors.append(f"scene_{s}")
            srcs.append(f"场景[{s}]")
    if args.word:
        for w in args.word.split(","):
            w = w.strip()
            anchors.append(f"word_{w}")
            srcs.append(f"词[{w}]")

    cands = query(mg, anchors)
    cands = filt(mg, cands)
    # 排序：2-4 字优先，命中数高优先，稳定（可复现）
    two_four = {w: h for w, h in cands.items() if 2 <= len(w) <= 4}
    others = {w: h for w, h in cands.items() if len(w) < 2 or len(w) > 4}
    def sort_key(item):
        return (-item[1], item[0])
    picked = sorted(two_four.items(), key=sort_key) + sorted(others.items(), key=sort_key)
    picked = picked[: args.n]

    print(f"【词汇注入候选·图查询】来源: {' + '.join(srcs)}｜候选 {len(cands)} 个 → 取 {len(picked)}")
    print("（用法：写 plan 时填【用词注入位】，正文每约 700 字自然用 1 个）")
    for i, (w, h) in enumerate(picked, 1):
        print(f"{i}. {w}（命中 {h}）")

    mg.close()


if __name__ == "__main__":
    main()
