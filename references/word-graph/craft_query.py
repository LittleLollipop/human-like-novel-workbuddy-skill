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
        print(f"\n■ {p.get('label','')}｜层级：{p.get('level','')}｜来源：{p.get('source','') or '学院派'}")
        if p.get("note"):
            print(f"  注：{p['note']}")
        if p.get("beats"):
            for i, b in enumerate(p["beats"], 1):
                pos = b.get("pos", "")
                print(f"  {i}. {b.get('name','')}{('（'+pos+'）') if pos else ''}：{b.get('purpose','')}")
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


def fig_narrative(mg, lib=None, src_filter=None):
    items = _narrative_items(mg, lib)
    if src_filter:
        items = [p for p in items if any(f in (p.get("source") or "") for f in src_filter)]
    label = {"dialogue": "对话技术", "opening": "开篇/黄金三章", "action": "战斗动作",
             "suspense": "悬念反转", "scene": "场景构建", "comedy": "喜剧手法"}.get(lib or "", "叙事手法")
    print(f"【{label}】（图库·{len(items)} 条手法）")
    for p in sorted(items, key=lambda x: x.get("name", "")):
        print(f"\n■ {p['name']}｜{p.get('formula','')}")
        for e in (p.get("examples") or [])[:2]:
            print(f"  例：{e}")
        print(f"  要点：{p.get('note','')}")


def file_narrative(lib=None, src_filter=None):
    label = {"dialogue": "对话技术", "opening": "开篇/黄金三章", "action": "战斗动作",
             "suspense": "悬念反转", "scene": "场景构建", "comedy": "喜剧手法"}.get(lib or "", "叙事手法")
    libs = [lib] if lib else ["dialogue", "opening", "action", "suspense", "scene", "comedy"]
    print(f"【{label}】（文件版）")
    for l in libs:
        data = load_file(f"{l}.json")
        for t in data.get("techniques", []):
            if src_filter and not any(f in (t.get("source") or "") for f in src_filter):
                continue
            print(f"\n■ {t['name']}｜{t.get('formula','')}")
            for e in (t.get("examples") or [])[:2]:
                print(f"  例：{e}")
            print(f"  要点：{t.get('note','')}")


def _sup_items(mg, vtype):
    g = mg._g
    items = []
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == vtype:
            items.append(gv(mg, dict(v)["id"]))
    return items


def fig_supplement(mg, vtype, src_filter=None):
    label = {"punch": "爽点引擎", "antipattern": "毒点反例", "trope": "网文流派套路", "writing": "写作实务"}.get(vtype, vtype)
    items = _sup_items(mg, vtype)
    if src_filter:
        items = [p for p in items if (p.get("source") or "") in src_filter]
    print(f"【{label}】（图库·{len(items)} 条，source 标注）")
    for p in sorted(items, key=lambda x: x.get("name", "")):
        print(f"\n■ {p['name']}｜来源：{p.get('source','')}")
        print(f"  {p.get('formula','')}")
        for e in (p.get("examples") or [])[:2]:
            print(f"  例：{e}")
        print(f"  要点：{p.get('note','')}")


def file_supplement(vtype, src_filter=None):
    fn = {"punch": "punch.json", "antipattern": "antipattern.json",
          "trope": "trope.json", "writing": "writing.json"}[vtype]
    key = {"antipattern": "antipatterns", "trope": "tropes"}.get(vtype, "techniques")
    data = load_file(fn)[key]
    if src_filter:
        data = [p for p in data if any(f in (p.get("source") or "") for f in src_filter)]
    label = {"punch": "爽点引擎", "antipattern": "毒点反例",
             "trope": "网文流派套路", "writing": "写作实务"}[vtype]
    print(f"【{label}】（文件版）")
    for p in data:
        print(f"\n■ {p['name']}｜来源：{p.get('source','')}")
        print(f"  {p.get('formula','')}")
        for e in (p.get("examples") or [])[:2]:
            print(f"  例：{e}")


def fig_allusion(mg, mood=None, scene=None, fam=None, sub=None, n=None):
    """图版：典故检索——按情绪/场景/熟悉度/类型过滤"""
    g = mg._g
    items = []
    for nid in g.pagerank().keys():
        v = g.get_vertex(nid)
        if v and dict(v).get("type") == "allusion":
            items.append(gv(mg, dict(v)["id"]))
    items = _filt_allusion(items, mood, scene, fam, sub)
    print(f"【通识典故库】{len(items)} 条（图库；mood={mood or '任意'} scene={scene or '任意'} fam={fam or '任意'}）")
    if n:
        items = items[:n]
    for p in items:
        print(f"\n■ {p['name']}｜{p.get('sub_type','')}｜熟悉度：{p.get('familiarity','中')}")
        print(f"  出处：{p.get('source','')}")
        print(f"  故事包：{p.get('story','')}")
        print(f"  含义：{p.get('meaning','')}")
        if p.get("note"):
            print(f"  提示：{p['note']}")


def file_allusion(mood=None, scene=None, fam=None, sub=None, n=None):
    data = load_file("allusion.json")
    items = _filt_allusion(data.get("allusions", []), mood, scene, fam, sub)
    print(f"【通识典故库】{len(items)} 条（文件版；mood={mood or '任意'} scene={scene or '任意'} fam={fam or '任意'}）")
    if n:
        items = items[:n]
    for p in items:
        print(f"\n■ {p['name']}｜{p.get('type','')}｜熟悉度：{p.get('familiarity','中')}")
        print(f"  出处：{p.get('source','')}")
        print(f"  故事包：{p.get('story','')}")
        print(f"  含义：{p.get('meaning','')}")
        if p.get("note"):
            print(f"  提示：{p['note']}")


def _filt_allusion(items, mood=None, scene=None, fam=None, sub=None):
    out = []
    for p in items:
        if mood:
            pm = p.get("mood") or []
            if isinstance(pm, str):
                try:
                    pm = json.loads(pm)
                except Exception:
                    pm = []
            if not any(m in pm for m in mood):
                continue
        if scene:
            ps = p.get("scene") or []
            if isinstance(ps, str):
                try:
                    ps = json.loads(ps)
                except Exception:
                    ps = []
            if "任意" not in ps and not any(s in ps for s in scene):
                continue
        if fam and p.get("familiarity") != fam:
            continue
        if sub and p.get("sub_type", p.get("type")) != sub:
            continue
        out.append(p)
    return out


# ── 文件版（兜底） ───────────────────────────────────# ── 文件版（兜底） ───────────────────────────────────# ── 文件版（兜底） ───────────────────────────────────# ── 文件版（兜底） ───────────────────────────────────
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
    ap.add_argument("--punch", action="store_true", help="爽点引擎（网文编辑方法论）")
    ap.add_argument("--antipattern", action="store_true", help="毒点反例（读者共识）")
    ap.add_argument("--source", help="来源过滤，逗号分隔（网文编辑方法论/网文读者共识/老舍/古龙/金庸/王小波/汪曾祺/学院派/特鲁比/沃格勒/莫多克/相声艺术/评书艺术/斯蒂芬·金/麦基/阿城/余华/刘震云/王朔/莫言/詹姆斯·斯科特·贝尔/杰里·克利弗）")
    ap.add_argument("--trope", action="store_true", help="网文流派套路（废柴流/退婚流/签到流/系统流等）")
    ap.add_argument("--writing", action="store_true", help="写作实务（斯蒂芬·金/麦基对白）")
    ap.add_argument("--allusion", action="store_true", help="通识典故库（成语/经文/历史；配 --mood/--scene/--fam/--sub）")
    ap.add_argument("--mood", help="典故情绪过滤，逗号分隔（得意/窘迫/恐惧/无奈/满足…）")
    ap.add_argument("--ascene", help="典故场景过滤，逗号分隔（市集买卖/夜袭战斗/谈判要价…；--scene 已被场景构建手法占用）")
    ap.add_argument("--fam", choices=["高", "中", "生僻"], help="典故熟悉度过滤")
    ap.add_argument("--sub", choices=["成语典故", "经文名句", "历史典故"], help="典故类型过滤")
    ap.add_argument("--master", action="store_true", help="名家风（古龙/金庸/王小波/老舍/汪曾祺）")
    ap.add_argument("--file", action="store_true", help="强制文件版（兜底）")
    args = ap.parse_args()

    if args.file:
        print("⛔ 文件版已禁用（2026-08-26 用户拍板：读 JSON 全量进上下文=注意力分散）。必须用图库。", file=sys.stderr)
        sys.exit(1)
    mg = get_graph()
    if mg is None:
        print(f"⛔ 图库打不开（{DB}）——必须用图库，禁止文件版兜底。请先运行 import_cilin.py/import_allusion.py 等建库。", file=sys.stderr)
        sys.exit(1)

    def show(kind, *params):
        if mg is not None:
            fig = {"rhetoric": fig_rhetoric, "imagery": fig_imagery,
                   "transition": fig_transition, "voice": fig_voice, "pacing": fig_pacing, "narrative": fig_narrative, "punch": fig_supplement, "antipattern": fig_supplement, "trope": fig_supplement, "writing": fig_supplement, "allusion": fig_allusion}[kind]
            fig(mg, *params)
        else:
            fil = {"rhetoric": file_rhetoric, "imagery": file_imagery,
                   "transition": file_transition, "voice": file_voice, "pacing": file_pacing, "narrative": file_narrative, "punch": file_supplement, "antipattern": file_supplement, "trope": file_supplement, "writing": file_supplement, "allusion": file_allusion}[kind]
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
            show("narrative", lib, args.source.split(",") if args.source else None)
            done = True
    if args.punch:
        show("punch", "punch", args.source.split(",") if args.source else None)
        done = True
    if args.antipattern:
        show("antipattern", "antipattern", args.source.split(",") if args.source else None)
        done = True
    if args.master:
        show("narrative", "master_style", args.source.split(",") if args.source else None)
        done = True
    if args.trope:
        show("trope", "trope", args.source.split(",") if args.source else None)
        done = True
    if args.writing:
        show("writing", "writing", args.source.split(",") if args.source else None)
        done = True
    if args.allusion:
        mood = [x.strip() for x in args.mood.split(",") if x.strip()] if args.mood else None
        scene = [x.strip() for x in args.ascene.split(",") if x.strip()] if args.ascene else None
        show("allusion", mood, scene, args.fam, args.sub, 12)
        done = True
    if not done:
        ap.error("至少给 --rhetoric / --imagery / --transition / --voice / --pacing / --dialogue / --opening / --action / --suspense / --scene / --comedy / --punch / --antipattern / --master / --trope / --writing / --allusion 之一")

    if mg is not None:
        mg.close()


if __name__ == "__main__":
    main()
