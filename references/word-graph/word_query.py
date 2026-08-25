#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词图查询器（word-graph）：按情绪/场景/沾边词三级词池检索候选用词。

用法:
    python3 word_query.py --emotion 温馨,满足 --scene 种田务农 --extra 锄头,垄,畦 --n 30
    python3 word_query.py --emotion 恐惧 --n 8
    python3 word_query.py --scene 夜袭战斗 --n 10

查询路径（纯图，无映射表）：
    情绪: emotion_X -seed_of-> 种子词 -belongs_to-> 语义类 <-belongs_to- 候选词
    场景: scene_X   -seed_of-> 种子词 -belongs_to-> 语义类 <-belongs_to- 候选词

三级词池（2026-08-26 用户拍板，修复「词池筛选单一导致该换的词换不进去/负面堆砌」）：
    1 级·核心：命中 ≥2 个锚点（情绪+场景交集）——最贴合，写 plan 必用
    2 级·单维：命中 ==1 个锚点（只中情绪 或 只中场景）——补充，按需用
    3 级·沾边：--extra/--char 种子词扩展（具体名词/人物词/本章关键词）——大池备用，防情绪词霸榜

过滤: ban 属性（文言硬错）排除；单字生僻排除；超长排除
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph, str_to_id  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")
RARE_SINGLE = set("尔汝吾乃遂辄弗毋勿莫须颇甚殊曰即矣哉乎兮焉乎哉厮弔拙迂谑谲骇愕矍遽亟")


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
    """锚点节点（emotion_/scene_/word_）→ 候选词集合 {词: 命中数}"""
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


def split_levels(cands, n_anchor_types):
    """按命中锚点类型数分级：命中≥2 类=1 级核心；==1 类=2 级单维。
    cands 为 {词: 命中数}，命中数=跨锚点累加（情绪+场景可各自命中多次）。
    """
    l1 = {w: h for w, h in cands.items() if h >= 2}
    l2 = {w: h for w, h in cands.items() if h == 1}
    return l1, l2


def expand_extra(mg, seeds, ban_extra):
    """3 级：--extra 种子词 → 词林扩展（具体名词/人物词/本章关键词）"""
    out = {}
    for s in seeds:
        codes = out_words(mg, f"word_{s}", "belongs_to")  # word_X 出 belongs_to 边到语义类
        for c in codes:
            for w in in_words(mg, c, "belongs_to"):
                if w not in ban_extra:
                    out[w] = out.get(w, 0) + 1
    return out


def main():
    ap = argparse.ArgumentParser(description="词图查询：三级词池（1核心/2单维/3沾边）")
    ap.add_argument("--emotion", help="情绪，逗号分隔")
    ap.add_argument("--scene", help="场景，逗号分隔")
    ap.add_argument("--extra", help="3 级沾边词种子，逗号分隔（具体名词/人物词/本章关键词，如 锄头,垄,畦,草木灰）")
    ap.add_argument("--n", type=int, default=40, help="每级输出上限（默认 40）")
    ap.add_argument("--word", help="直接给种子词，逗号分隔（等价于 --extra，单独用时按 3 级输出）")
    args = ap.parse_args()

    if not (args.emotion or args.scene or args.extra or args.word):
        ap.error("至少给 --emotion / --scene / --extra / --word 之一")

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

    # 1/2 级：情绪/场景锚点
    l1, l2 = {}, {}
    if anchors:
        cands = filt(mg, query(mg, anchors))
        l1, l2 = split_levels(cands, 2)
        # 稳定排序（可复现）
        def sk(item):
            return (-item[1], item[0])
        l1 = dict(sorted(l1.items(), key=sk)[: args.n])
        l2 = dict(sorted(l2.items(), key=sk)[: args.n])

    # 3 级：extra/word 种子扩展
    extra_seeds = []
    if args.extra:
        extra_seeds += [s.strip() for s in args.extra.split(",") if s.strip()]
    if args.word:
        extra_seeds += [w.strip() for w in args.word.split(",") if w.strip()]
    l3 = {}
    if extra_seeds:
        # 排除 1/2 级已出现的词
        ban3 = set(l1) | set(l2)
        l3 = expand_extra(mg, extra_seeds, ban3)
        l3 = filt(mg, l3)
        l3 = dict(sorted(l3.items(), key=lambda x: (-x[1], x[0]))[: args.n])

    print(f"【词汇注入候选·三级词池】来源: {' + '.join(srcs) if srcs else '词[直接]'}｜extra: {','.join(extra_seeds) if extra_seeds else '—'}")
    print("（写 plan 填【用词注入位】：1 级核心必用；2 级补充；3 级大池按需——正文每约 20 字自然用 1 个，禁止句尾堆砌同义情绪词）")
    if l1:
        print(f"\n【1 级·核心】（情绪+场景交集，最贴合）{len(l1)} 个：")
        for i, (w, h) in enumerate(l1.items(), 1):
            print(f"  {i}. {w}（命中 {h}）")
    if l2:
        print(f"\n【2 级·单维】（只中情绪 或 只中场景）{len(l2)} 个：")
        for i, (w, h) in enumerate(l2.items(), 1):
            print(f"  {i}. {w}（命中 {h}）")
    if l3:
        print(f"\n【3 级·沾边】（extra/word 种子扩展——具体名词/人物词/本章关键词）{len(l3)} 个：")
        for i, (w, h) in enumerate(l3.items(), 1):
            print(f"  {i}. {w}")

    mg.close()


if __name__ == "__main__":
    main()
