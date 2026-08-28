#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_vocab.py — 生造词/缩略词检测（2026-08-29 用户方案 B 落地）

核心思路（用户）：全文分词，每个词去「辞林/词林」匹配——能匹配=合法词，匹配不到=AI 生造/缩略词候选。
词典体系（词林为核心，jieba 补常用词缺口）：
  ① 图库词林（lexicon.axeb type=word 45,366 + type=idiom 30,895）——转录写作词库，权威核心
  ② jieba 默认词典（约 35 万书面词）——补词林缺失的常用词（人气/沙土/小刀）
  ③ 本书词表（--book-dir 历史章节自动累积）——补网文词（玩家/鱼干/坐堂等）
  ④ 专名白名单（--whitelist 项目配置：角色/地名/组织）
检测两级：
  A. token 级：jieba 分词 → 合并词典外 + 非数量短语 → 生造候选（精确；但切碎型漏——「腌人」被切成单字）
  B. 单字区辅助：jieba 切碎的连续单字区（≥3 字）→ 切碎型生造词必然出现在其中（如「价不还/腌人」在「着价不还/能腌人」里），噪音多但作者扫读可见
  能力边界（2026-08-29 验证）：中文单字均为合法词，词法层无法精确判定 2 字生造组合——A 抓「jieba 切出的词典外 2+ 字词」，B 靠人扫单字区抓切碎型；两者互补，均提示级。
定位：提示级候选筛选（机器筛，人判），非硬报错。

用法：
  python3 check_vocab.py <文件或章节名>
  python3 check_vocab.py <文件> --book-dir /path/to/chapters --whitelist 花少,闷壳,灯塔镇
  python3 check_vocab.py <文件> --limit 30
"""
import argparse
import re
import sys
import glob
import os
from collections import Counter

try:
    import jieba
except ImportError:
    sys.stderr.write("需要 jieba：pip install jieba\n")
    sys.exit(1)

jieba.setLogLevel(60)

# ---- 数量短语过滤（一个/一剑/三家/第一把）----
NUM = "一二两三四五六七八九十百千万零壹贰叁肆伍陆柒捌玖"
QUANT = "个只条块张把根支口件笔声场回次遍顿下番阵趟步刀剑夜天月年家户头匹艘架台座间句页章"
NUM_RE = re.compile(f"^[{NUM}]+[{QUANT}]?$")
NUM_PREFIX_RE = re.compile(f"^[{NUM}]{{1,3}}[一了个]")


def load_lexicon(axeb_path):
    """加载图库词林（word + idiom）"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                    "..", "..", "..", "..", ".."))
    # 用 lobster-memory 引擎读图库
    from engine.memory_graph import MemoryGraph
    mg = MemoryGraph(axeb_path)
    g = mg._g
    words = set()
    for nid in g.pagerank().keys():
        v = dict(g.get_vertex(nid))
        if v.get("type") in ("word", "idiom"):
            w = v.get("word") or v.get("name")
            if w and len(w) >= 2:
                words.add(w)
    mg.close()
    return words


def load_book_words(book_dir):
    """从历史章节目录累积本书词表（自动白名单：本书用过=合法）"""
    words = set()
    if not book_dir:
        return words
    for f in sorted(glob.glob(os.path.join(book_dir, "*.txt"))):
        try:
            t = open(f, encoding="utf-8").read()
        except Exception:
            continue
        for w in jieba.lcut(t):
            w = w.strip()
            if len(w) >= 2 and re.fullmatch(r"[\u4e00-\u9fff]+", w):
                words.add(w)
    return words


def token_level_check(text, vocab):
    """token 级：jieba 分词 → 词典外候选"""
    cands = []
    for w in jieba.lcut(text):
        w = w.strip()
        if len(w) < 2 or not re.fullmatch(r"[\u4e00-\u9fff]+", w):
            continue
        if w in vocab:
            continue
        if NUM_RE.match(w) or NUM_PREFIX_RE.match(w):
            continue
        cands.append(w)
    return cands


def coverage_check(hanzi, vocab):
    """连续单字区报告：jieba 切碎的连续单字串（≥3 字）= 生造/缩略词信号（如「价不还」切成 价/不/还）
    说明：中文单字均为合法词，词法层无法判定 2 字生造组合（腌人=腌/人），故只报 ≥3 字单字区供人工扫读。
    """
    words = jieba.lcut(hanzi)
    runs = []
    cur = []
    for w in words:
        w = w.strip()
        if len(w) == 1 and re.fullmatch(r"[\u4e00-\u9fff]", w):
            cur.append(w)
        else:
            if len(cur) >= 3:
                runs.append("".join(cur))
            cur = []
    if len(cur) >= 3:
        runs.append("".join(cur))
    return runs


def main():
    ap = argparse.ArgumentParser(description="生造词/缩略词检测（词林核心 + jieba 补全 + 本书词表 + 连续串覆盖）")
    ap.add_argument("target", help="章节文件路径（或项目内章节名）")
    ap.add_argument("--lexicon", default=None, help="图库路径（默认找技能 references/word-graph/lexicon.axeb）")
    ap.add_argument("--book-dir", default=None, help="历史章节目录（自动累积本书词表）")
    ap.add_argument("--whitelist", default="", help="专名白名单，逗号分隔（角色/地名/组织）")
    ap.add_argument("--limit", type=int, default=40, help="每个列表最多显示条数")
    args = ap.parse_args()

    # 定位文件
    path = args.target
    if not os.path.exists(path):
        for cand in glob.glob(os.path.join(os.getcwd(), "chapters", "arc-1", f"{path}*")):
            path = cand
            break
    if not os.path.exists(path):
        sys.stderr.write(f"找不到文件: {args.target}\n")
        sys.exit(1)

    # 定位图库
    if args.lexicon is None:
        default_axeb = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lexicon.axeb")
        if os.path.exists(default_axeb):
            args.lexicon = default_axeb
        else:
            sys.stderr.write("找不到图库，用 --lexicon 指定\n")
            sys.exit(1)

    print(f"加载词林…（{args.lexicon}）")
    lexicon = load_lexicon(args.lexicon)
    jieba.initialize()
    jieba_dict = set(jieba.dt.FREQ.keys())
    book_words = load_book_words(args.book_dir)
    whitelist = {w.strip() for w in args.whitelist.split(",") if w.strip()}
    vocab = lexicon | jieba_dict | book_words | whitelist

    print(f"词典规模: 词林 {len(lexicon)} + jieba {len(jieba_dict)} + 本书词表 {len(book_words)} + 专名 {len(whitelist)} = {len(vocab)}")

    text = open(path, encoding="utf-8").read()

    # A. token 级
    cands = token_level_check(text, vocab)
    print(f"\n=== A. 生造词候选（token 级，{len(set(cands))} 种）===")
    for w, c in Counter(cands).most_common(args.limit):
        print(f"  {w}×{c}")

    # B. 连续单字区（≥3 字，生造/缩略词信号）
    hanzi = re.sub(r"[^\u4e00-\u9fff]", "", text)
    runs = coverage_check(hanzi, vocab)
    runs = [r for r in runs if not NUM_RE.match(r)]
    print(f"\n=== B. 连续单字区（jieba 切碎的 ≥3 字单字串——生造/缩略信号，{len(set(runs))} 种）===")
    for r, c in Counter(runs).most_common(args.limit):
        print(f"  {r}×{c}")

    print(f"\n定位：提示级候选（机器筛人判）。命中=人工甄别：真生造改掉 / 合理新词（招牌/称呼/剧情专名）加白名单。")


if __name__ == "__main__":
    main()
