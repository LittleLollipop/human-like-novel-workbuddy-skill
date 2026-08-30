#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""情绪评估机检（技能级，书无关）——human-like-novel「情绪评估机制·双轨」的工具层。
按读者心智模型档位（A=情绪消费向 / B=结构情绪向）扫描任意章节文本，输出对应清单的命中报告。

判据（唯一）：读者能不能接受延迟满足（攒情绪等大高潮）？
  A 档 = 不能，活在情绪里，只对情绪反应 → 每章即时结算、单点写法满格
  B 档 = 能，为整体结构攒情绪 → 结构性分配、克制优先、爆发只给结构高点

注意：情绪评估本质需语义判断，本工具输出**提示级**命中（⚠️），供人工裁量，
不设硬禁（❌）——"写偏了"是方向问题不是词法问题，机器只能指出信号，拉回由人做。

复用：analyze(lines, text, mode) 返回 (errs, warns)——项目机检
（如新书 tools/check_chapter.py）通过 importlib 加载调用，单一权威源不双实现。

用法:
    python3 check_emotion.py <章节文件> --mode A|B
"""
import re
import sys
import os

# ── A 档：情绪消费向 ──
A_EMO_WORDS = [
    # 爽/解气
    "爽", "解气", "扬眉吐气", "痛快", "过瘾", "值了", "赚了", "得劲", "打脸", "噎住",
    # 乐/喜剧
    "愣住", "瞪眼", "脸都绿了", "眼睛一亮", "乐了", "笑了", "哄地", "炸了锅", "憋笑",
    "笑成一片", "哭笑不得", "嘴角抽了抽", "嘿嘿",
    # 紧张/恐惧
    "心凉", "发毛", "腿软", "脸都白了", "咽了口唾沫", "头皮发麻", "冷汗", "后脖颈",
    "倒吸", "绷紧", "攥紧", "大气不敢出",
    # 震撼/错愕
    "愣在当场", "僵在原地", "安静得可怕", "鸦雀无声", "目瞪口呆", "回过神来", "一动不动",
    # 期待/钓住
    "钓", "钩子", "等什么", "咽了咽", "屏住",
]
# A 档信号：对话密度参考（直给型 ≥50% 是节奏维度，这里只提示）
A_ZERO_EMO_SENT = r"^[^“”!?！？…]*[。；：,，]?\s*$"  # 弱信号，配合上下文人工判断

# ── B 档：结构情绪向（廉价情绪/撒狗血信号）──
B_CHEAP_EMO = [
    "泪流满面", "热泪盈眶", "眼泪夺眶而出", "泣不成声", "嚎啕大哭",
    "热血沸腾", "激情澎湃", "心潮澎湃", "浑身颤抖", "激动得", "感动得",
    "震撼人心", "无以言表", "无法用语言形容", "潸然泪下",
]
# B 档：每章强行爽信号（感叹号密集/连续短爆句）
B_SHOUT = r"[！]{2,}"
B_HYPE_PAT = r"(太|真|简直|竟然|居然|果然|终于|总算)(爽|牛|强|神|绝|燃|炸|顶)"

# 情绪点写法完整度（两档共用，A 档要求全，B 档要求克制）
EFFECT_SIGNS = ["爆发", "一锤定音", "鸦雀无声", "安静", "沉默", "半天", "半晌", "回过神来"]


def split_paras(lines):
    """按 ※※※ 分隔符分节（空行不算节分隔——普通空行只是段落换行），返回 [(节起始行号, 节文本), ...]"""
    paras = []
    cur = []
    start = 1
    for i, ln in enumerate(lines, 1):
        if ln.strip() == "※※※":
            if cur:
                paras.append((start, "\n".join(cur)))
                cur = []
            start = i + 1
        elif ln.strip():
            cur.append(ln)
    if cur:
        paras.append((start, "\n".join(cur)))
    return paras


def analyze(lines, text, mode="A"):
    """核心分析：返回 (errs, warns)。mode='A' 或 'B'。
    errs 恒为空（情绪评估无硬禁）；warns=本档位清单命中报告。"""
    warns = []
    full = "\n".join(lines)

    if mode == "A":
        warns.extend(_analyze_a(lines, text, full))
    elif mode == "B":
        warns.extend(_analyze_b(lines, text, full))
    else:
        warns.append(f"[情绪·配置] 未知档位 mode={mode}，应为 A 或 B")
    return [], warns


def _analyze_a(lines, text, full):
    warns = []
    # 1. 整章情绪点数量（提示：太少=情绪供给不足信号）
    hits = sum(full.count(w) for w in A_EMO_WORDS)
    if hits < 4:
        warns.append(f"[情绪A·供给⚠️] 全章情绪信号词仅 {hits} 处（基准≥4）——情绪消费向读者每章要足额情绪，检查是否有平淡章")
    # 2. 零情绪节（整节无对话无情绪词，纯叙述铺陈）
    for start, para in split_paras(lines):
        if len(para) < 30:
            continue
        has_dialog = "“" in para or "”" in para
        has_emo = any(w in para for w in A_EMO_WORDS)
        if not has_dialog and not has_emo:
            warns.append(f"[情绪A·空窗节⚠️] 节起 L{start}：整节无对话无情绪词（{len(para)}字）——A 档不存在空窗节，检查是否纯铺陈")
    # 3. 单点写法草率信号（情绪词出现但无效果收尾/余韵，弱信号）
    if hits >= 2 and not any(s in full for s in EFFECT_SIGNS):
        warns.append("[情绪A·写法⚠️] 有情绪词但缺「爆发/安静/回过神来」类效果收尾——每个情绪点要走全 铺垫→蓄势→爆发→余韵，检查是否意思到了没写透")
    # 4. 情绪类型单一（只有乐没有爽/紧张，或反之；按感叹/疑问/省略占比粗判）
    excl = full.count("！") + full.count("!")
    ques = full.count("？") + full.count("?")
    if excl > 0 and ques == 0 and hits < 6:
        warns.append(f"[情绪A·类型⚠️] 感叹{excl}处但疑问0处——情绪类型可能单一（只有宣泄没有紧张/期待），检查连续章节是否同一种情绪")
    return warns


def _analyze_b(lines, text, full):
    warns = []
    # 1. 廉价情绪词（撒狗血信号）
    cheap = [(w, full.count(w)) for w in B_CHEAP_EMO if w in full]
    if cheap:
        det = "、".join(f"「{w}」×{c}" for w, c in cheap)
        warns.append(f"[情绪B·廉价⚠️] 撒狗血词 {det}——B 档克制优先，该严肃场景禁直给情绪，改留白/余韵/暗示（删情绪泡沫）")
    # 2. 每章强行爽信号（感叹号堆叠/口号式爆点）
    shout = len(re.findall(B_SHOUT, full))
    hype = [(m.group(0), m.start()) for m in re.finditer(B_HYPE_PAT, full)]
    if shout >= 3:
        warns.append(f"[情绪B·强爽⚠️] 连续感叹号 {shout} 处——B 档禁每章强行爽，爆点只给到结构高点，其余收着写")
    if hype:
        det = "、".join(f"「{m}」" for m, _ in hype[:6])
        warns.append(f"[情绪B·口号⚠️] 口号式爆点 {det}（L{min(p for _, p in hype)} 起）——B 档爆点靠场面/因果/留白，不靠感叹口号")
    # 3. 情绪服从结构（弱信号：全章无情绪低谷痕迹——全是高强度=没有蓄势）
    calm = ["看了看", "坐着", "站着", "想了", "望着", "沉默", "没说话", "没接话", "半晌"]
    calm_hits = sum(full.count(c) for c in calm)
    if calm_hits < 3 and len(full) > 500:
        warns.append(f"[情绪B·蓄势⚠️] 全章平静/思考类动作仅 {calm_hits} 处——B 档需要低谷蓄力，检查是否一路高潮（该蓄力时克制）")
    return warns


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = "A"
    if "--mode" in sys.argv:
        i = sys.argv.index("--mode")
        if i + 1 < len(sys.argv):
            mode = sys.argv[i + 1].upper()
    if not args:
        print("用法: check_emotion.py <章节文件> --mode A|B")
        sys.exit(2)
    path = args[0]
    if not os.path.isfile(path):
        print(f"文件不存在: {path}")
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    _, warns = analyze(lines, text, mode)
    print(f"=== 情绪评估（{mode}档 · 提示级，人工裁量）: {path} ===")
    if not warns:
        print("  ✅ 本档位清单无命中（情绪评估以人审为准，此为辅助信号）")
    for w in warns:
        print("  " + w)


if __name__ == "__main__":
    main()
