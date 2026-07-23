#!/usr/bin/env python3
# error-cases 通用机检运行器（技能级，书无关）
# 扫描任意章节文件，对 _rules.json 中「通用可机检」规则报命中行号+案例号。
# 不自动修改；假阳性人工甄别，真违规即修。
import json, re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "_rules.json")


def load_rules():
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)["rules"]


def scan_regex(text, rule):
    pat = re.compile(rule["pattern"])
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in pat.finditer(line):
            hits.append((i, m.group(0)))
    return hits


def scan_threshold(text, rule):
    target = rule.get("repeat") or rule.get("char", "")
    count = text.count(target)
    maxc = rule.get("max", 0)
    if count > maxc:
        return [("全文", f"出现 {count} 次，上限 {maxc}")]
    return []


def main():
    if len(sys.argv) < 2:
        print("用法: check_error_cases.py <章节文件>")
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"文件不存在: {path}")
        sys.exit(2)
    rules = load_rules()
    with open(path, encoding="utf-8") as f:
        text = f.read()
    total = 0
    print(f"=== error-cases 通用机检：{path} ===")
    for rule in rules:
        if rule["type"] == "regex":
            hits = scan_regex(text, rule)
        elif rule["type"] == "threshold":
            hits = scan_threshold(text, rule)
        else:
            hits = []
        if hits:
            total += len(hits)
            print(f"\n[{rule['id']}] {rule['name']}（{rule.get('severity','')}）命中 {len(hits)} 处")
            for ln, frag in hits[:60]:
                print(f"  L{ln}: {frag}")
            if len(hits) > 60:
                print(f"  … 其余 {len(hits)-60} 处略")
            if rule.get("note"):
                print(f"  注：{rule['note']}")
    if total == 0:
        print("\n=== 通用机检项全部干净 ===")
    else:
        print(f"\n=== 合计命中 {total} 处（假阳性请人工甄别，真违规即修） ===")


if __name__ == "__main__":
    main()
