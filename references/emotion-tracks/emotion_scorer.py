#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""节级情绪解析打分器 v3（技能级，书无关）——情绪评估机制·双轨 的节级工具。

v3 核心重构（2026-08-30 用户拍板）：**废弃手工情绪词表，改用词林语义类**。
  分词 → 查词林（lexicon.axeb）word_X -belongs_to-> class_XXX → 按 class 编码段映射情绪类别。
  词林 45k 词 + 9000+ 语义类，覆盖远超手工词表，且免维护。

情绪类别由 class 编码段决定（同义词词林编码规则）：
  Ga01A=高兴  Ga02A=忧愁/忧虑  Ga02B=烦闷/憋屈  Ga03A=愤怒/恼火  Ga04A=得意
  Ga06A/B/C=满意/满足/舒畅  Ga07B=不安/紧张  Ga08A/B=惭愧/心虚  Ga09B=平静
  Ga09C=慌张/惊慌  Ga12A/B/C=无奈/尴尬  Ga16A/B=惊讶/害怕  Gb10B=愤恨
  Gb11B=委屈  Gb19B=担心  Gb21D=轻蔑/鄙视  Gc04B=不屑
  Ed13B=理亏  Ef10B=紧张(局势)  Ee13B=怯懦  Ee34D=骄傲  Ef07A=舒服
  具体 class→情绪 映射见 emotion_scorer_config.json 的 class_map（可按需补）。

视角与打分（保留 v2）：
  - 视角降权：主角台词/叙述=全权重；非主角台词=non_main_weight（0.3）
  - 语意磨损豁免：worn_words（口语常用词，情绪已磨损不计分）
  - 结构分/对话分 × 地基得分率折扣（discount=0.5+0.5×strength_rate）

打分维度（配置 emotion_scorer_config.json）：
  1. 情绪强度（0-40）：主情绪词命中加权密度
  2. 写法完整（0-30）：铺垫/爆发/余韵 结构信号（分档） × discount
  3. 对话承载（0-20）：对话占比 × discount
  4. 类型纯净（0-10）：主情绪词占比

复用：analyze(lines, text, mode) 返回 (errs, warns, sections)
用法: python3 emotion_scorer.py <章节文件> [--mode A|B] [--config config.json]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "emotion_scorer_config.json")
WORD_GRAPH = os.path.join(HERE, "..", "word-graph", "lexicon.axeb")
LOBSTER_ENGINE = os.environ.get("LOBSTER_MEMORY_ENGINE", "/Users/sai/.workbuddy/skills/lobster-memory")

_TALK_VERBS = r"(说道|说|喊|笑|接话|嘀咕|开口|追问|补了一句|应道|低声道|问)"
_PRE = re.compile(rf"([\u4e00-\u9fff]{{1,4}}?)({_TALK_VERBS})[\u201c]")
_POST = re.compile(rf"[\u201d]([\u4e00-\u9fff]{{1,4}}?)({_TALK_VERBS})")
_NON_MAIN_HINTS = ["玩家", "那人", "有人", "兄弟", "坐堂", "白姐", "闷壳", "周先生", "渔户", "老渔户", "酒瓮"]


def load_config(path=None):
    p = path or DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_word_graph():
    """加载词林图库，返回 MemoryGraph 实例"""
    sys.path.insert(0, LOBSTER_ENGINE)
    from engine.memory_graph import MemoryGraph, str_to_id  # noqa
    mg = MemoryGraph(WORD_GRAPH)
    return mg, str_to_id


# 惰性加载的词林查询器（单例）
_mg = None
_str2id = None
_EMO_INDEX = None  # {情绪类别: [词, ...]} 由词林动态构建


def get_graph():
    global _mg, _str2id
    if _mg is None:
        _mg, _str2id = load_word_graph()
    return _mg, _str2id


def build_emo_index(cfg):
    """从词林动态构建「情绪类别 → [(词, emo_weight), ...]」索引。
    路径：class_map 里的情绪 class → in_neighbors 挂的 word 节点（词林补词即自动生效）。
    词权重（语意磨损分层，存词林节点 emo_weight）：口语高频=0.5 / 普通=1.0 / 四字成语=1.5。"""
    global _EMO_INDEX
    if _EMO_INDEX is not None:
        return _EMO_INDEX
    mg, str2id = get_graph()
    g = mg._g
    cmap = cfg.get("class_map", {})
    idx = {}
    for cls_id, emo in cmap.items():
        if cls_id == "note" or not cls_id.startswith("class_"):
            continue
        nid = str2id(cls_id)
        if g.get_vertex(nid) is None:
            continue
        for sn in g.in_neighbors(nid):
            v = g.get_vertex(sn)
            if v and dict(v).get("type") == "word":
                w = dict(v).get("word", "")
                if w:
                    wgt = dict(v).get("emo_weight", 1.0)
                    idx.setdefault(emo, {})[w] = wgt
    # 排序稳定
    for emo in idx:
        idx[emo] = dict(sorted(idx[emo].items()))
    _EMO_INDEX = idx
    return idx


def word_classes(word):
    """查词林：word_X 的 belongs_to 出边 → 语义类 id 列表"""
    mg, str2id = get_graph()
    nid = str2id(f"word_{word}")
    if mg._g.get_vertex(nid) is None:
        return []
    out = []
    for t in mg._g.out_neighbors(nid):
        e = mg._g.get_edge(nid, t)
        if e and e[1].get("kind") == "belongs_to":
            v = mg._g.get_vertex(t)
            if v:
                out.append(dict(v)["id"])
    return out


def split_sections(lines):
    """按 ※※※ 分隔符分节，返回 [(起始行号, 节文本), ...]"""
    secs = []
    cur = []
    start = 1
    for i, ln in enumerate(lines, 1):
        if ln.strip() == "※※※":
            if cur:
                secs.append((start, "\n".join(cur)))
                cur = []
            start = i + 1
        elif ln.strip():
            cur.append(ln)
    if cur:
        secs.append((start, "\n".join(cur)))
    return secs


def _dialog_ratio(text):
    in_q = False
    hz = 0
    qc = 0
    for ch in text:
        if ch in "\u201c\u201d":
            in_q = not in_q
        elif "\u4e00" <= ch <= "\u9fff":
            hz += 1
            if in_q:
                qc += 1
    return (qc / hz) if hz else 0.0


def _speaker_of(line, cfg):
    if "“" not in line and "”" not in line:
        return None
    main_chars = cfg["main_chars"]
    for mc in main_chars:
        if mc in line and re.search(rf"{mc}.{{0,8}}?({_TALK_VERBS})", line):
            return "main"
    for hint in _NON_MAIN_HINTS:
        if hint in line:
            return "non"
    for m in _PRE.finditer(line):
        return "main" if m.group(1) in main_chars else "non"
    for m in _POST.finditer(line):
        return "main" if m.group(1) in main_chars else "non"
    return None


def _weight_for_line(line, cfg, mode):
    sp = _speaker_of(line, cfg)
    if sp == "non":
        return cfg["modes"][mode]["non_main_weight"]
    return 1.0


def _subject_of(line, cfg):
    """行主语判定（供情绪逆向用）：
    'main' = 行内含主角名（花少）→ 主角自身活动/台词，不逆向
    'non'  = 行内含非主角称呼且无主角 → 描述对手/他人，命中方向性词时逆向
    None   = 无法判定（代词句/无称呼）→ 保守不逆向
    注意：『坐堂』是玩家对花少的称呼（非主角称呼），『闷壳/白姐』是同伴——
    同伴的压制类词几乎不会出现，若出现按 non 逆向，权重小可接受。"""
    for mc in cfg["main_chars"]:
        if mc == "他" or mc == "我":
            continue  # 代词不判 main（"他得意地晃着叉子"描述对手也用他）
        if mc in line:
            return "main"
    for hint in _NON_MAIN_HINTS:
        if hint in line:
            return "non"
    return None


def _is_worn(word, cfg):
    for grp, words in cfg.get("worn_words", {}).items():
        if grp == "note":
            continue
        if word in words:
            return True
    return False


def _class_to_cats(cls_id, cfg):
    """class id → 情绪类别列表（按 class_map 编码段匹配）"""
    cmap = cfg.get("class_map", {})
    # 精确 class 匹配优先，其次编码段（Ga02B01 → Ga02B）
    if cls_id in cmap:
        return cmap[cls_id]
    seg3 = cls_id[6:10]  # class_Ga02B01 -> Ga02B
    if seg3 in cmap:
        return cmap[seg3]
    seg2 = cls_id[6:9]   # class_Ga02B01 -> Ga02
    if seg2 in cmap:
        return cmap[seg2]
    return None


def score_section(text, cfg, mode):
    """单节打分：返回 (主情绪, 总分, 维度分, 证据)"""
    mod = cfg["modes"][mode]
    W = mod["weights"]
    struct = cfg["structure"]
    lines = text.splitlines()

    # 1. 词林情绪索引 → 子串匹配统计（词权重 emo_weight + 视角权重 + 豁免 + 逆向）
    emo_index = build_emo_index(cfg)
    # 逆向表：word -> (target, 类型标签)
    inv = {}
    for grp in ("suppress", "yield"):
        gcfg = cfg.get("inversion", {}).get(grp, {})
        tag = "压制" if grp == "suppress" else "示弱"
        for w in gcfg.get("words", []):
            inv[w] = (gcfg.get("target", "憋屈" if grp == "suppress" else "爽"), tag)
    inv_weight = cfg.get("inversion", {}).get("weight", 0.5)
    cat_hits = {}      # cat -> 加权总命中
    cat_evidence = {}  # cat -> [(word, weighted, 行号, 逆向标签?), ...]
    for emo, words_w in emo_index.items():
        h = 0.0
        ev = []
        for w, wgt in words_w.items():
            if _is_worn(w, cfg):
                continue
            # 单字词自动豁免（词林单字语义泛，情绪负载弱；"怪了/闷响"类误命中高发）
            if len(w) == 1:
                continue
            # 子串匹配（整节内出现即计；按行算视角权重）
            hit_lines = [i for i, ln in enumerate(lines, 1) if w in ln]
            if not hit_lines:
                continue
            inv_t, inv_tag = inv.get(w, (None, None))
            wsum = 0.0
            for i, ln in enumerate(lines, 1):
                if w not in ln:
                    continue
                if inv_t is not None:
                    # 方向性词：非主角行的命中逆转为 主角体验（对手压制=憋屈 / 对手吃瘪=爽）
                    # 权重=词权重×inversion_weight：描写对手的画面强度弱于主角亲历（0.5），可调
                    if _subject_of(ln, cfg) == "non":
                        cat_hits[inv_t] = cat_hits.get(inv_t, 0.0) + wgt * inv_weight
                        cat_evidence.setdefault(inv_t, []).append((w, round(wgt * inv_weight, 2), [i], f"←{inv_tag}"))
                        continue
                wsum += _weight_for_line(ln, cfg, mode)
            if wsum > 0:
                eff = wsum * wgt  # 词权重（口语磨损降权 / 成语提权）
                h += eff
                ev.append((w, round(eff, 2), hit_lines[:6], ""))
        if h > 0:
            # 累加而非赋值：逆向命中可能已先行写入同类别（如"爽"类），覆盖会丢分（2026-08-30 bug）
            cat_hits[emo] = round(cat_hits.get(emo, 0.0) + h, 2)
            cat_evidence.setdefault(emo, []).extend(ev)

    total_emo = sum(cat_hits.values())
    if total_emo <= 0:
        return "平淡", 0.0, {"strength": 0, "structure": 0, "dialog": 0, "purity": 0}, {"note": "无词林情绪词命中——A 档空窗节信号（或词不在词林）"}

    main_cat = max(cat_hits, key=cat_hits.get)
    main_hits = cat_hits[main_cat]

    # strength：主情绪加权命中密度（地基）
    strength_raw = min(main_hits * cfg["strength_per_hit"], W["strength"])
    strength = strength_raw
    strength_rate = strength_raw / W["strength"] if W["strength"] else 0.0
    discount = 0.5 + 0.5 * strength_rate

    # structure：铺垫/爆发/余韵 × discount
    s_ev = {}
    s_score = 0
    per = W["structure"] / 3
    for name, words in (("build", struct["build"]), ("payoff", struct["payoff"]), ("afterglow", struct["afterglow"])):
        hits = [(w, [i for i, ln in enumerate(lines, 1) if w in ln][:5]) for w in words if w in text]
        if hits:
            tier = cfg.get("structure_tier", {}).get("two_plus", 1.0) if len(hits) >= 2 else cfg.get("structure_tier", {}).get("one_word", 0.5)
            s_score += per * tier
            s_ev[name] = hits[:4]
    structure = min(s_score, W["structure"]) * discount

    # dialog × discount
    dr = _dialog_ratio(text)
    dialog_raw = min(W["dialog"], W["dialog"] * (dr / mod["dialog_target"]))
    dialog = dialog_raw * discount

    # purity：主情绪占比
    purity_ratio = main_hits / total_emo
    if purity_ratio >= cfg["purity_min"]:
        purity = W["purity"]
    else:
        purity = W["purity"] * (purity_ratio / cfg["purity_min"])

    total = strength + structure + dialog + purity
    return main_cat, round(total, 1), {
        "strength": round(strength, 1),
        "structure": round(structure, 1),
        "dialog": round(dialog, 1),
        "purity": round(purity, 1),
    }, {
        "main_hits": main_hits,
        "total_emo": total_emo,
        "dialog_ratio": round(dr, 2),
        "evidence": cat_evidence.get(main_cat, []),
        "structure_ev": s_ev,
    }


def analyze(lines, text, mode="A", config_path=None):
    cfg = load_config(config_path)
    sections = []
    for start, sec_text in split_sections(lines):
        emo, total, dims, ev = score_section(sec_text, cfg, mode)
        sections.append((start, emo, total, dims, ev))
    return [], [], sections


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = "A"
    cfg_path = None
    if "--mode" in sys.argv:
        i = sys.argv.index("--mode")
        if i + 1 < len(sys.argv):
            mode = sys.argv[i + 1].upper()
    if "--config" in sys.argv:
        i = sys.argv.index("--config")
        if i + 1 < len(sys.argv):
            cfg_path = sys.argv[i + 1]
    if not args:
        print("用法: emotion_scorer.py <章节文件> [--mode A|B] [--config config.json]")
        sys.exit(2)
    path = args[0]
    if not os.path.isfile(path):
        print(f"文件不存在: {path}")
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    cfg = load_config(cfg_path)
    mod = cfg["modes"][mode]
    print(f"=== 节级情绪解析 v3（{mode}档·{mod['label']}·词林语义类）: {path} ===")
    _, _, sections = analyze(lines, text, mode, cfg_path)
    for start, emo, total, dims, ev in sections:
        bar = "█" * int(total // 10) + "░" * (10 - int(total // 10))
        print(f"\n节起 L{start} | 主情绪: {emo} | 总分: {total}/100 {bar}")
        print(f"  强度{dims['strength']:.0f}/40 · 结构{dims['structure']:.0f}/30 · 对话{dims['dialog']:.0f}/20 · 纯净{dims['purity']:.0f}/10")
        if "note" in ev:
            print(f"  ⚠️ {ev['note']}")
            continue
        det = "、".join(f"{w}×{wh}{tag}" for w, wh, _, tag in ev["evidence"][:8])
        print(f"  主情绪词(加权{ev['main_hits']}/{ev['total_emo']}): {det}")
        if ev["structure_ev"]:
            sev = "; ".join(f"{k}:{','.join(w for w, _ in v[:3])}" for k, v in ev["structure_ev"].items())
            print(f"  结构信号: {sev}")
        print(f"  对话占比: {ev['dialog_ratio']*100:.0f}%")


if __name__ == "__main__":
    main()
