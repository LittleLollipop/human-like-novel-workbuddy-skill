#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 味指纹机检（技能级，书无关）——human-like-novel 双扫之一。
扫描任意章节文本，对 ai_tells.json 规则库输出：
  1. 硬禁命中（hard_bans：模板时间词/概念化场景句，确定性词，出现即报错❌）
  2. 统计报告（stats：概念化模板/突发副词/口头禅/主题词频/三连排比/句式分布/重复段落——提示级⚠️，报数字留人工裁量）
配合 error-cases 的 check_error_cases.py 双扫并行（错误模式 vs 生成指纹）。

复用：analyze(lines, text) 返回 (errs, warns)——项目机检（如新书 tools/check_chapter.py）
通过 importlib 加载本模块调用 analyze，单一权威源不双实现。

用法:
    python3 check_ai_tells.py <章节文件>
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "ai_tells.json")


def load_rules():
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)


def split_sents(text: str):
    return [s for s in re.findall(r"[^。！？…]*[。！？…]", text) if s.strip()]


def analyze(lines, text, rules=None):
    """核心分析：返回 (errs, warns)。
    errs=硬禁命中列表（必改）；warns=统计提示列表（人工裁量）。"""
    if rules is None:
        rules = load_rules()
    errs, warns = [], []

    # ── 1. 硬禁（确定性词/模式，出现即报错；pattern 型带 negate 豁免） ──
    hard_hits = 0
    for b in rules["hard_bans"]:
        if "pattern" in b:
            # 正则模式型（如『不是X，是Y』论断句）+ 豁免词（回忆冲突锚点/口语词）+ 对话层豁免（台词=角色语言风格）
            pat = re.compile(b["pattern"])
            negate = b.get("negate", [])
            for i, ln in enumerate(lines, 1):
                if pat.search(ln):
                    if any(n in ln for n in negate):
                        continue
                    if "“" in ln or "”" in ln:
                        continue  # 对话层豁免：台词内『不是X是Y』是角色语言风格（花少正反论断妙语）
                    hard_hits += 1
                    errs.append(f"[AI味·硬禁❌] L{i}: 命中「{b.get('why','')[:22]}…」→ {b['fix']}（{b.get('source','')}）")
        else:
            for i, ln in enumerate(lines, 1):
                if b["word"] in ln:
                    hard_hits += 1
                    errs.append(f"[AI味·硬禁❌] L{i}: 「{b['word']}」→ {b['fix']}（{b.get('source','')}）")
    if hard_hits == 0:
        errs.append("[AI味·硬禁✅] 模板时间词/概念化场景句/论断句：0 处")

    # ── 2. 统计报告（提示级） ──
    st = rules["stats"]

    # 2.1 概念化模板
    ct = st["concept_templates"]
    ct_hits = [(w, text.count(w)) for w in ct["words"] if text.count(w)]
    if len(ct_hits) > ct["max"]:
        warns.append(f"[AI味·提示⚠️] 概念化描写 {ct['max']}+ 处：{'、'.join(f'{w}×{c}' for w,c in ct_hits)} → {ct['fix']}")

    # 2.2 突发副词（裸用）
    ta = st["transition_adverbs"]
    ta_hits = [(w, text.count(w)) for w in ta["words"] if text.count(w)]
    ta_total = sum(c for _, c in ta_hits)
    if ta_total > ta["max"]:
        warns.append(f"[AI味·提示⚠️] 突发副词 {ta_total} 次（上限{ta['max']}）：{', '.join(f'{w}×{c}' for w,c in ta_hits)} → {ta['fix']}")

    # 2.3 口头禅
    ot = st["oral_tic_words"]
    ot_hits = [(w, text.count(w)) for w in ot["words"] if text.count(w)]
    ot_total = sum(c for _, c in ot_hits)
    if ot_total > ot["max"]:
        warns.append(f"[AI味·提示⚠️] 口头禅回应 {ot_total} 次（上限{ot['max']}）：{', '.join(f'{w}×{c}' for w,c in ot_hits)} → {ot['fix']}")

    # 2.4 高频词 top（主题词敲击信号）——只统计二字以上词（单字=常用字误报重灾区）
    tw = st["topic_word_freq"]
    stop = set(tw["stopwords"])
    words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    cnt = Counter(w for w in words if w not in stop)
    top = [(w, c) for w, c in cnt.most_common(tw["top_n"] + 15) if c >= 3][:tw["top_n"]]
    if top:
        line = "、".join(f"{w}×{c}" for w, c in top)
        warns.append(f"[AI味·统计] 高频词 top{tw['top_n']}: {line}")
        abstract = [f"{w}×{c}" for w, c in top if c > tw["max"]]
        if abstract:
            warns.append(f"[AI味·提示⚠️] 疑似主题词敲击（>{tw['max']}次）：{', '.join(abstract)} → 若为抽象概念词=反复敲击信号，{tw['fix']}")

    # 2.5 三连排比
    tp = st["triple_parallel"]
    tri = len(re.findall(r"[^。！？…]{2,6}，[^。！？…]{2,6}，[^。！？…]{2,6}。", text))
    if tri > tp["max"]:
        warns.append(f"[AI味·提示⚠️] 三连排比 {tri} 处（上限{tp['max']}，账目/货物罗列豁免）→ {tp['fix']}")
    else:
        warns.append(f"[AI味·统计] 三连排比: {tri} 处")

    # 2.6 句式分布
    sr = st["statement_ratio"]
    sents = split_sents(text)
    if sents:
        ends = Counter(s[-1] for s in sents)
        stmt = ends.get("。", 0)
        pct = stmt * 100 // len(sents)
        flag = ""
        if pct > sr["max_pct"]:
            flag = f" → ⚠️ 平铺陈述过多，{sr['fix']}"
        warns.append(f"[AI味·统计] 句式分布: 陈述{pct}% / 感叹{ends.get('！',0)*100//len(sents)}% / 疑问{ends.get('？',0)*100//len(sents)}% / 省略{ends.get('…',0)*100//len(sents)}%（共{len(sents)}句）{flag}")

    # 2.7 重复段落
    dp = st["dup_paragraphs"]
    if dp.get("on"):
        seen = {}
        dups = []
        for i, ln in enumerate(lines, 1):
            s = ln.strip()
            if not s:
                continue
            if s in seen:
                dups.append((seen[s], i, s[:30]))
            else:
                seen[s] = i
        if dups:
            det = "\n".join(f"    L{a} 与 L{b} 相同：{frag}…" for a, b, frag in dups[:10])
            warns.append(f"[AI味·提示⚠️] 完全重复段落 {len(dups)} 组：\n{det} → {dp.get('fix','删重复段')}")

    # 2.8 项目级动作短语重复（默认空，本书特例走项目配置）
    da = st["dup_action_phrases"]
    for w in da["words"]:
        c = text.count(w)
        if c > da["max"]:
            warns.append(f"[AI味·提示⚠️] 动作短语重复「{w}」×{c}（上限{da['max']}）→ {da['fix']}")

    # 2.9 冗余密度（用词层，2026-08-28 加——信息密度过高=AI 指纹）
    rd = st.get("redundancy")
    if rd:
        rd_words = rd.get("words", [])
        sents_all = split_sents(text)
        if sents_all:
            rd_sents = sum(1 for s in sents_all if any(w in s for w in rd_words))
            pct = rd_sents * 100 // len(sents_all)
            if pct < rd["min_pct"]:
                warns.append(f"[AI味·提示⚠️] 冗余密度 {pct}%（<{rd['min_pct']}%=信息密度过高，人类口述≈10%）→ {rd['fix']}")
            else:
                warns.append(f"[AI味·统计] 冗余密度 {pct}%（用词层，基准≈10%；结构型废话需人工补）")

    # 2.10 AI 第一人称情绪模板（'心里+X'，2026-08-28 加——朱雀验证负面）
    et = st.get("emotion_templates")
    if et:
        et_hits = [(w, text.count(w)) for w in et.get("words", []) if text.count(w)]
        et_total = sum(c for _, c in et_hits)
        if et_total > et["max"]:
            warns.append(f"[AI味·提示⚠️] 第一人称情绪模板『心里+X』{et_total} 次（上限{et['max']}）：{', '.join(f'{w}×{c}' for w,c in et_hits)} → {et['fix']}")

    # 2.11 论断式判断句（不是X，是Y——2026-08-29 ch34 加）
    js = st.get("judge_sentence")
    if js:
        hits = re.findall(js["pattern"], text)
        if len(hits) > js["max"]:
            warns.append(f"[AI味·提示⚠️] 论断式判断句『不是…是…』{len(hits)} 处（上限{js['max']}）→ {js['fix']}")

    # 2.12 比喻连接词密度（像是/像/仿佛——2026-08-29 ch34 加）
    sw = st.get("simile_words")
    if sw:
        sw_hits = [(w, text.count(w)) for w in sw["words"] if text.count(w)]
        sw_total = sum(c for _, c in sw_hits)
        if sw_total > sw["max"]:
            warns.append(f"[AI味·提示⚠️] 比喻连接词 {sw_total} 次（上限{sw['max']}）：{', '.join(f'{w}×{c}' for w,c in sw_hits)} → {sw['fix']}")

    # 2.13 X得发X 生造搭配（绿得发幽——2026-08-29 ch34 加）
    df = st.get("de_fa_pattern")
    if df:
        allow = set(df["allow"])
        df_hits = []
        for m in re.finditer(df["pattern"], text):
            tail = m.group(0)[-2:]
            if tail not in allow:
                df_hits.append(f"「{m.group(0)}」")
        if df_hits:
            warns.append(f"[AI味·提示⚠️] X得发X 生造搭配 {len(df_hits)} 处：{'、'.join(df_hits[:8])} → {df['fix']}")

    # 2.14 情绪身体扫描词（手脚冰凉/心口一沉——2026-08-29 ch34 加，#074 同族）
    bs = st.get("body_scan")
    if bs:
        bs_hits = [(w, text.count(w)) for w in bs["words"] if text.count(w)]
        bs_total = sum(c for _, c in bs_hits)
        if bs_total > bs["max"]:
            warns.append(f"[AI味·提示⚠️] 情绪身体扫描 {bs_total} 处（上限{bs['max']}）：{', '.join(f'{w}×{c}' for w,c in bs_hits)} → {bs['fix']}")

    # 2.15 同字重叠副词（XX地——2026-08-29 ch34 加）
    da2 = st.get("dup_adv")
    if da2:
        adv_hits = re.findall(da2["pattern"], text)
        if len(adv_hits) > da2["max"]:
            warned = "、".join(f"{w}{w}地" for w in adv_hits[:12])
            warns.append(f"[AI味·提示⚠️] 同字重叠副词 {len(adv_hits)} 处（上限{da2['max']}）：{warned} → {da2['fix']}")

    # 2.16 见过X见过X没见过 排比（2026-08-29 ch34 加）
    et2 = st.get("enum_turn")
    if et2:
        hits = re.findall(et2["pattern"], text)
        if len(hits) > et2["max"]:
            warns.append(f"[AI味·提示⚠️] 『见过…见过…没见过』排比 {len(hits)} 处（上限{et2['max']}）→ {et2['fix']}")

    return errs, warns


def main():
    if len(sys.argv) < 2:
        print("用法: check_ai_tells.py <章节文件>")
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"文件不存在: {path}")
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    errs, warns = analyze(lines, text)
    print(f"=== AI 味指纹机检：{path} ===")
    for e in errs:
        print(" " + e)
    for w in warns:
        print(" " + w)
    err_n = sum(1 for e in errs if "❌" in e)
    print(f"\n结论: AI 味指纹——硬禁 {err_n} 处（必改）+ 提示 {len(warns)} 项（人工裁量）")
    if err_n == 0:
        print("（提示项=统计特征，报数字留人工裁量，不自动判错）")


if __name__ == "__main__":
    main()
