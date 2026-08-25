#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句式查询器（syntax_query）：按情绪/场景从图库检索句式范式。

用法:
    python3 syntax_query.py --emotion 无奈 --scene 谈判要价
    python3 syntax_query.py --scene 夜袭战斗
    python3 syntax_query.py --emotion 得意
    python3 syntax_query.py --all            # 全部范式

查询路径（纯图）：pattern_{句式} -fits-> emotion_/scene_ 锚点
输出：范式名 + 结构公式 + 例句（注入 plan【句式注入位】直接用）

频率（用户拍板）：按需求使用，每个自然段最多用 1 种特殊句式；全章 3-5 种轮换。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
sys.path.insert(0, SKILL_ENGINE)

from engine.memory_graph import MemoryGraph, str_to_id  # noqa: E402

DB = os.path.join(HERE, "lexicon.axeb")


def get_pat(mg, pid):
    v = mg.get_vertex(pid)
    if not v:
        return None
    p = dict(v)
    ex = p.get("examples")
    if isinstance(ex, str):
        ex = json.loads(ex or "[]")
    mo = p.get("mood")
    if isinstance(mo, str):
        mo = json.loads(mo or "[]")
    sc = p.get("scene")
    if isinstance(sc, str):
        sc = json.loads(sc or "[]")
    return {
        "name": p.get("name", pid),
        "formula": p.get("formula", ""),
        "examples": ex or [],
        "note": p.get("note", ""),
    }


def main():
    ap = argparse.ArgumentParser(description="句式查询：按情绪/场景检索句式范式（纯图）")
    ap.add_argument("--emotion", help="情绪，逗号分隔")
    ap.add_argument("--scene", help="场景，逗号分隔")
    ap.add_argument("--all", action="store_true", help="列出全部 30 个范式")
    args = ap.parse_args()

    if not (args.emotion or args.scene or args.all):
        ap.error("至少给 --emotion / --scene / --all 之一")

    mg = MemoryGraph(DB)
    g = mg._g
    nid_int = str_to_id("class_Aa01A01")  # 占位（获取图对象用）

    # 收集所有 pattern 节点
    all_pats = {}
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "syntax_pattern":
            pid = dict(v)["id"]
            all_pats[pid] = get_pat(mg, pid)

    if args.all:
        print(f"【句式范式全表】共 {len(all_pats)} 个（黄廖体系转录 + 口语语用补充）")
        for pid in sorted(all_pats):
            p = all_pats[pid]
            print(f"\n■ {p['name']}｜{p['formula']}")
            for e in p["examples"][:2]:
                print(f"  例：{e}")
        mg.close()
        return

    # 按锚点过滤：pattern -fits-> emotion_/scene_
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

    hits = {}
    for aid in anchors:
        a_int = str_to_id(aid)
        for snid in g.in_neighbors(a_int):  # pattern -> fits -> anchor 的入边
            e = g.get_edge(snid, a_int)
            if e and e[1].get("kind") == "fits":
                v = g.get_vertex(snid)
                if v and dict(v).get("type") == "syntax_pattern":
                    pid = dict(v)["id"]
                    hits[pid] = hits.get(pid, 0) + 1

    print(f"【句式注入候选】来源: {' + '.join(srcs)}｜命中 {len(hits)} 个范式")
    print("（用法：写 plan 时挑 3-5 个填【句式注入位】；每自然段最多 1 种，全章轮换）")
    for pid, h in sorted(hits.items(), key=lambda x: -x[1]):
        p = get_pat(mg, pid)
        print(f"\n■ {p['name']}（命中 {h}）｜{p['formula']}")
        for e in p["examples"][:2]:
            print(f"  例：{e}")
        if p["note"]:
            print(f"  提示：{p['note']}")

    mg.close()


if __name__ == "__main__":
    main()
