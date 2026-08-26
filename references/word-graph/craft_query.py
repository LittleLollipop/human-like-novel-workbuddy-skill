#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技法查询器（craft_query）：按场景/情绪查修辞/物象/转场/声口——图库优先，无图库时文件兜底。

用法:
    python3 craft_query.py --rhetoric                    # 修辞全表（图）
    python3 craft_query.py --rhetoric 无奈,市集          # 修辞（按情绪/场景过滤，fits 边）
    python3 craft_query.py --imagery 冷,穷              # 物象（按名）
    python3 craft_query.py --transition                  # 全部转场
    python3 craft_query.py --voice                       # 声口语料
    python3 craft_query.py --file                        # 强制文件版（兜底）

写 plan 时：按本章情绪/场景查 → 挑 2-3 个填【技法注入位】。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "lexicon.axeb")


def load_file(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def get_graph():
    SKILL_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")
    sys.path.insert(0, SKILL_ENGINE)
    from engine.memory_graph import MemoryGraph, str_to_id  # noqa
    if not os.path.exists(DB):
        return None
    return MemoryGraph(DB)


def gv(mg, pid):
    """读节点属性（图）"""
    v = mg.get_vertex(pid)
    if not v:
        return None
    p = dict(v)
    out = dict(p)
    for k in ("examples", "mood", "scene", "items", "interjections", "design"):
        if isinstance(out.get(k), str):
            try:
                out[k] = json.loads(out[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return out


# ── 图版 ─────────────────────────────────────────────
def fig_rhetoric(mg, mood=None, scene=None):
    g = mg._g
    nodes = []
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "rhetoric":
            nodes.append(dict(v)["id"])
    if mood or scene:
        def match(pid):
            p = gv(mg, pid)
            m = not mood or any(x in (p.get("mood") or []) for x in mood)
            s = not scene or any(x in (p.get("scene") or []) for x in scene)
            return m and s
        nodes = [n for n in nodes if match(n)]
    print(f"【修辞手法】{len(nodes)} 格（图库·陈望道《修辞学发凡》转录）")
    for pid in sorted(nodes, key=lambda x: gv(mg, x).get("name", "")):
        p = gv(mg, pid)
        print(f"\n■ {p['name']}｜{p.get('formula','')}")
        for e in (p.get("examples") or [])[:2]:
            print(f"  例：{e}")
        print(f"  频率：{p.get('freq','')}")
        print(f"  要点：{p.get('note','')}")


def fig_imagery(mg, keys=None):
    g = mg._g
    imgs = {}
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "imagery":
            p = gv(mg, dict(v)["id"])
            imgs[p["name"]] = p.get("items") or []
    if keys:
        imgs = {k: v for k, v in imgs.items() if k in keys}
    print(f"【感官物象】{len(imgs)} 类（图库·写『冷』不写冷，写物象）")
    for k, v in imgs.items():
        print(f"\n■ {k}：{' / '.join(v[:6])}")


def fig_transition(mg):
    g = mg._g
    items = []
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "transition":
            items.append(gv(mg, dict(v)["id"]))
    print(f"【转场手法】{len(items)} 种（图库·替代『突然/就在这时』）")
    for t in sorted(items, key=lambda x: x.get("name", "")):
        print(f"\n■ {t['name']}｜{t.get('formula','')}")
        for e in (t.get("examples") or [])[:2]:
            print(f"  例：{e}")
        print(f"  适用：{t.get('where','')}｜{t.get('note','')}")


def fig_voice(mg):
    p = gv(mg, "voice")
    print("【人物声口】（图库·通用语气词 + 设计方法）")
    for grp, words in (p.get("interjections") or {}).items():
        print(f"\n■ {grp}：{'/'.join(words[:8])}")
    print("\n■ 设计方法：")
    for k, v in (p.get("design") or {}).items():
        print(f"  {k}：{v}")


def fig_pacing(mg, name=None):
    g = mg._g
    items = []
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "pacing":
            items.append(gv(mg, dict(v)["id"]))
    if name:
        items = [p for p in items if p.get("name") == name or name in (p.get("label") or "")]
    print(f"【叙事节奏】{len(items)} 个体系（图库）")
    for p in sorted(items, key=lambda x: x.get("name", "")):
        print(f"\n■ {p.get('label','')}｜层级：{p.get('level','')}")
        if p.get("beats"):
            for i, b in enumerate(p["beats"], 1):
                print(f"  {i}. {b.get('name','')}（{b.get('pos','')}）：{b.get('purpose','')}")
        if p.get("rules"):
            for r in p["rules"]:
                print(f"  · {r.get('name','')}：{r.get('rule','')}")


def file_pacing(name=None):
    data = load_file("pacing.json")
    items = []
    for key, s in data["macro"].items():
        if not name or name in key or name in s["label"]:
            items.append((s["label"], s.get("level", ""), s.get("beats", [])))
    if not name or "micro" in name or not items:
        m = data.get("micro", {})
        items.append((m.get("label", "章节级节奏规则"), "chapter", []))
    print(f"【叙事节奏】（文件版）{len(items)} 个体系")
    for label, level, beats in items:
        print(f"\n■ {label}｜层级：{level}")
        for i, b in enumerate(beats, 1):
            print(f"  {i}. {b.get('name','')}（{b.get('pos','')}）：{b.get('purpose','')}")


def _narrative_items(mg, lib=None):
    g = mg._g
    items = []
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "narrative":
            p = gv(mg, dict(v)["id"])
            if not lib or p.get("lib") == lib:
                items.append(p)
    return items


def fig_narrative(mg, lib=None):
    items = _narrative_items(mg, lib)
    label = {"dialogue": "对话技术", "opening": "开篇/黄金三章", "action": "战斗动作",
             "suspense": "悬念反转", "scene": "场景构建", "comedy": "喜剧手法"}.get(lib or "", "叙事手法")
    print(f"【{label}】（图库·{len(items)} 条手法）")
    for p in sorted(items, key=lambda x: x.get("name", "")):
        print(f"\n■ {p['name']}｜{p.get('formula','')}")
        for e in (p.get("examples") or [])[:2]:
            print(f"  例：{e}")
        print(f"  要点：{p.get('note','')}")


def file_narrative(lib=None):
    label = {"dialogue": "对话技术", "opening": "开篇/黄金三章", "action": "战斗动作",
             "suspense": "悬念反转", "scene": "场景构建", "comedy": "喜剧手法"}.get(lib or "", "叙事手法")
    libs = [lib] if lib else ["dialogue", "opening", "action", "suspense", "scene", "comedy"]
    print(f"【{label}】（文件版）")
    for l in libs:
        data = load_file(f"{l}.json")
        for t in data.get("techniques", []):
            print(f"\n■ {t['name']}｜{t.get('formula','')}")
            for e in (t.get("examples") or [])[:2]:
                print(f"  例：{e}")
            print(f"  要点：{t.get('note','')}")


# ── 文件版（兜底） ───────────────────────────────────# ── 文件版（兜底） ───────────────────────────────────
def file_rhetoric():
    data = load_file("rhetoric.json")
    print(f"【修辞手法】{len(data['rhetorics'])} 格（文件版·陈望道转录）")
    for r in data["rhetorics"]:
        print(f"\n■ {r['name']}｜{r['formula']}")
        for e in r["examples"][:2]:
            print(f"  例：{e}")
        print(f"  频率：{r['freq']}")


def file_imagery(keys=None):
    data = load_file("imagery.json")["imagery"]
    if keys:
        data = {k: v for k, v in data.items() if k in keys}
    print(f"【感官物象】{len(data)} 类（文件版）")
    for k, v in data.items():
        print(f"\n■ {k}：{' / '.join(v[:6])}")


def file_transition():
    data = load_file("transition.json")
    print(f"【转场手法】{len(data['transitions'])} 种（文件版）")
    for t in data["transitions"]:
        print(f"\n■ {t['name']}｜{t['formula']}")
        for e in t["examples"][:2]:
            print(f"  例：{e}")


def file_voice():
    data = load_file("voice.json")
    print("【人物声口】（文件版）")
    for grp, words in data["interjections"].items():
        print(f"\n■ {grp}：{'/'.join(words[:8])}")
    print("\n■ 设计方法：")
    for k, v in data["design"].items():
        print(f"  {k}：{v}")


def main():
    ap = argparse.ArgumentParser(description="技法查询：修辞/物象/转场/声口（图库优先，文件兜底）")
    ap.add_argument("--rhetoric", nargs="?", const="", help="修辞查询（可带 情绪,场景 过滤）")
    ap.add_argument("--imagery", nargs="?", const="", help="物象查询，逗号分隔（空=全表）")
    ap.add_argument("--transition", action="store_true", help="全部转场手法")
    ap.add_argument("--voice", action="store_true", help="声口语料")
    ap.add_argument("--pacing", nargs="?", const="", help="叙事节奏体系（救猫咪/故事圈/三幕/七点/弗莱塔格/英雄之旅/微观；空=全部）")
    ap.add_argument("--dialogue", action="store_true", help="对话技术手法")
    ap.add_argument("--opening", action="store_true", help="开篇/黄金三章手法")
    ap.add_argument("--action", action="store_true", help="战斗动作手法")
    ap.add_argument("--suspense", action="store_true", help="悬念反转手法")
    ap.add_argument("--scene", action="store_true", help="场景构建手法")
    ap.add_argument("--comedy", action="store_true", help="喜剧手法")
    ap.add_argument("--file", action="store_true", help="强制文件版（兜底）")
    args = ap.parse_args()

    mg = None if args.file else get_graph()

    def show(kind, *params):
        if mg is not None:
            fig = {"rhetoric": fig_rhetoric, "imagery": fig_imagery,
                   "transition": fig_transition, "voice": fig_voice, "pacing": fig_pacing, "narrative": fig_narrative}[kind]
            fig(mg, *params)
        else:
            fil = {"rhetoric": file_rhetoric, "imagery": file_imagery,
                   "transition": file_transition, "voice": file_voice, "pacing": file_pacing, "narrative": file_narrative}[kind]
            fil(*params)

    done = False
    if args.rhetoric is not None:
        parts = [x.strip() for x in args.rhetoric.split(",") if x.strip()]
        show("rhetoric", parts or None, None)
        done = True
    if args.imagery is not None:
        keys = [x.strip() for x in args.imagery.split(",") if x.strip()]
        show("imagery", keys or None)
        done = True
    if args.transition:
        show("transition")
        done = True
    if args.voice:
        show("voice")
        done = True
    if args.pacing is not None:
        show("pacing", args.pacing or None)
        done = True
    for lib in ("dialogue", "opening", "action", "suspense", "scene", "comedy"):
        if getattr(args, lib):
            show("narrative", lib)
            done = True
    if not done:
        ap.error("至少给 --rhetoric / --imagery / --transition / --voice / --pacing / --dialogue / --opening / --action / --suspense / --scene / --comedy 之一")

    if mg is not None:
        mg.close()


if __name__ == "__main__":
    main()
