#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词汇检索器（word-injector）：按情绪/场景从同义词词林扩展版检索候选用词。

用法:
    python3 word_injector.py --emotion 得意,炫耀 --scene 市集买卖 --n 12
    python3 word_injector.py --emotion 恐惧 --n 8            # 只看情绪
    python3 word_injector.py --scene 夜袭战斗 --n 10         # 只看场景
    python3 word_injector.py --emotion 得意 --with-desc      # 带同义词群上下文

原理:
    模型语体单极化+歧义词概率稀释 → 生词贫乏。负向禁词只是 top0→top1 换皮。
    正解=在写 plan 时把符合情绪/场景的人类常用词注入上下文，按字数卡频率使用。
    词林按语义组织，种子词扩展成同义词群 = chunk 化注入（模型照抄 chunk 是强项）。

词表: 同义词词林扩展版（哈工大 HIT-IRLab，77k 词，GB18030 转 UTF-8 入库）
过滤: 文言缩词（baihua-lexicon words 反向排除）+ 生僻单字 + 超长短语
可累积: 踩到好词往 seed-map.json 的对应情绪/场景 seeds 加
"""
import argparse
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CILIN = os.path.join(HERE, "cilin-extended.txt")
SEED_MAP = os.path.join(HERE, "seed-map.json")
BAIHUA_LEXICON = os.path.join(HERE, "..", "baihua-lexicon.json")

# 生僻单字（词林里的大量单字文言词，白话文不适用）
RARE_SINGLE = set("尔汝吾乃遂辄弗毋勿莫须颇甚殊曰即矣哉乎兮焉乎哉厮弔拙迂谑谲骇愕矍遽亟")
# 2字及以上的白话语境常用排除（个别过于文言的词）
EXTRA_BAN = set()

def load_cilin():
    """解析词林 → {词: [编码, ...]} + {编码: [词, ...]}"""
    word_to_code = {}
    code_to_words = {}
    with open(CILIN, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or "=" not in ln:
                continue
            code, _, rest = ln.partition("=")
            code = code.strip()
            words = [w.strip() for w in rest.split() if w.strip()]
            for w in words:
                word_to_code.setdefault(w, []).append(code)
            code_to_words[code] = words
    return word_to_code, code_to_words

def load_seeds():
    with open(SEED_MAP, encoding="utf-8") as f:
        return json.load(f)

def load_baihua_ban():
    """文言缩词反向排除表（复用白话护栏词表——降级保留：此处当过滤器）"""
    try:
        with open(BAIHUA_LEXICON, encoding="utf-8") as f:
            lex = json.load(f)
        return set(lex.get("words", {}).keys()) | set(lex.get("dialogue_only", {}).keys())
    except FileNotFoundError:
        return set()

def expand(seeds, word_to_code, code_to_words, ban):
    """种子 → 同义词群 → 候选（去重、过滤）"""
    out = []
    seen = set()
    for s in seeds:
        codes = word_to_code.get(s, [])
        for c in codes:
            for w in code_to_words.get(c, []):
                if w in seen:
                    continue
                seen.add(w)
                # 过滤
                if w in ban or w in EXTRA_BAN:
                    continue
                if len(w) == 1 and w in RARE_SINGLE:
                    continue
                if len(w) > 8:  # 超长短语（含注音/解释）不要
                    continue
                if re.search(r"[（()·～\-]", w):  # 带符号的不要
                    continue
                out.append((w, c))
    return out

def main():
    ap = argparse.ArgumentParser(description="按情绪/场景检索候选用词（词林种子扩展）")
    ap.add_argument("--emotion", help="情绪，逗号分隔（得意/炫耀/窘迫/慌乱/紧张/恐惧/愤怒/惊讶/无奈/疲惫/温馨/满足/轻蔑/心虚）")
    ap.add_argument("--scene", help="场景，逗号分隔（市集买卖/海上出海/夜袭战斗/酒馆闲聊/谈判要价/破屋贫寒/危机逃生）")
    ap.add_argument("--n", type=int, default=12, help="输出候选数（默认 12）")
    ap.add_argument("--with-desc", action="store_true", help="附带同义词群编码（看词源）")
    ap.add_argument("--seed", help="直接给种子词，逗号分隔（绕过映射表，自定义检索）")
    ap.add_argument("--shuffle", action="store_true", help="随机打乱（默认稳定排序，可复现）")
    args = ap.parse_args()

    if not (args.emotion or args.scene or args.seed):
        ap.error("至少给 --emotion / --scene / --seed 之一")

    word_to_code, code_to_words = load_cilin()
    seeds_map = load_seeds()
    ban = load_baihua_ban()

    seeds = []
    srcs = []
    if args.seed:
        seeds += [s.strip() for s in args.seed.split(",") if s.strip()]
        srcs.append("自定义")
    if args.emotion:
        emo_map = seeds_map["emotion_seeds"]
        for e in args.emotion.split(","):
            e = e.strip()
            if e in emo_map:
                seeds += emo_map[e]
                srcs.append(f"情绪[{e}]")
            else:
                print(f"⚠️ 未知情绪: {e}（可用: {'/'.join(emo_map.keys())}）", file=sys.stderr)
    if args.scene:
        sc_map = seeds_map["scene_seeds"]
        for s in args.scene.split(","):
            s = s.strip()
            if s in sc_map:
                seeds += sc_map[s]
                srcs.append(f"场景[{s}]")
            else:
                print(f"⚠️ 未知场景: {s}（可用: {'/'.join(sc_map.keys())}）", file=sys.stderr)

    cands = expand(seeds, word_to_code, code_to_words, ban)
    # 排序：2-4 字词优先（白话双音节为主），组内按种子词出现顺序（词林文件序）稳定
    two_four = [c for c in cands if 2 <= len(c[0]) <= 4]
    others = [c for c in cands if len(c[0]) < 2 or len(c[0]) > 4]
    if args.shuffle:
        random.shuffle(two_four)
        random.shuffle(others)
    picked = (two_four + others)[: args.n]

    print(f"【词汇注入候选】来源: {' + '.join(srcs)}｜种子 {len(set(seeds))} 个 → 候选 {len(cands)} 个 → 取 {len(picked)}")
    print("（用法：写 plan 时填【用词注入位】，正文按字数比例自然使用——每约 700 字 1 个）")
    for i, (w, c) in enumerate(picked, 1):
        suffix = f"（词群 {c}）" if args.with_desc else ""
        print(f"{i}. {w}{suffix}")

if __name__ == "__main__":
    main()
