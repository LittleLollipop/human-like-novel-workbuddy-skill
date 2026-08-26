#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技法查询器（craft_query）：按场景/情绪查修辞/物象/转场/声口素材库。

用法:
    python3 craft_query.py --rhetoric 无奈,市集        # 修辞手法（按情绪/场景过滤）
    python3 craft_query.py --imagery 冷,穷            # 感官物象（按场景/情绪）
    python3 craft_query.py --transition               # 全部转场手法
    python3 craft_query.py --voice                    # 声口语料（语气词+设计方法）
    python3 craft_query.py --all 冷,紧张              # 全部技法

写 plan 时：按本章情绪/场景查 → 挑 2-3 个填【技法注入位】。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def show_rhetoric(mood=None, scene=None):
    data = load("rhetoric.json")
    items = data["rhetorics"]
    if mood or scene:
        def match(r):
            m = not mood or any(x in r.get("mood", []) for x in mood)
            s = not scene or any(x in r.get("scene", []) for x in scene)
            return m and s
        items = [r for r in items if match(r)]
    print(f"【修辞手法】{len(items)} 格（陈望道《修辞学发凡》转录，去套路化范例）")
    for r in items:
        print(f"\n■ {r['name']}｜{r['formula']}")
        for e in r["examples"][:2]:
            print(f"  例：{e}")
        print(f"  频率：{r['freq']}")
        print(f"  要点：{r['note']}")


def show_imagery(keys=None):
    data = load("imagery.json")
    imgs = data["imagery"]
    if keys:
        imgs = {k: v for k, v in imgs.items() if k in keys}
    print(f"【感官物象】{len(imgs)} 类（写『冷』不写冷，写物象）")
    for k, v in imgs.items():
        print(f"\n■ {k}：{' / '.join(v[:6])}")


def show_transition():
    data = load("transition.json")
    print(f"【转场手法】{len(data['transitions'])} 种（替代『突然/就在这时』）")
    for t in data["transitions"]:
        print(f"\n■ {t['name']}｜{t['formula']}")
        for e in t["examples"][:2]:
            print(f"  例：{e}")
        print(f"  适用：{t['where']}｜{t['note']}")


def show_voice():
    data = load("voice.json")
    print("【人物声口】通用语气词 + 设计方法（治角色一个调）")
    for grp, words in data["interjections"].items():
        print(f"\n■ {grp}：{'/'.join(words[:8])}")
    print("\n■ 设计方法：")
    for k, v in data["design"].items():
        print(f"  {k}：{v}")


def main():
    ap = argparse.ArgumentParser(description="技法查询：修辞/物象/转场/声口")
    ap.add_argument("--rhetoric", nargs="?", const="", help="修辞查询（可不带参看全表）")
    ap.add_argument("--imagery", nargs="?", const="", help="物象查询，逗号分隔（冷/穷/暖/晨/夜/市集/海上/农事/恐惧/饥饿/疲惫/紧张/热闹/荒凉；空=全表）")
    ap.add_argument("--transition", action="store_true", help="全部转场手法")
    ap.add_argument("--voice", action="store_true", help="声口语料")
    ap.add_argument("--all", help="全部技法，逗号分隔情绪/场景")
    args = ap.parse_args()

    if args.all:
        mood_scene = [x.strip() for x in args.all.split(",")]
        show_rhetoric(mood_scene, mood_scene)
        print("\n" + "=" * 30)
        show_imagery(mood_scene)
        print("\n" + "=" * 30)
        show_transition()
        print("\n" + "=" * 30)
        show_voice()
        return

    done = False
    if args.rhetoric is not None:
        parts = [x.strip() for x in args.rhetoric.split(",")]
        # 分不出情绪/场景，全量展示（plan 时人工选）
        show_rhetoric()
        done = True
    if args.imagery is not None:
        keys = [x.strip() for x in args.imagery.split(",") if x.strip()]
        show_imagery(keys or None)
        done = True
    if args.transition:
        show_transition()
        done = True
    if args.voice:
        show_voice()
        done = True
    if not done:
        ap.error("至少给 --rhetoric / --imagery / --transition / --voice / --all 之一")


if __name__ == "__main__":
    main()
