#!/usr/bin/env python3
"""
仿人类小说创作 - CLI工具
从根源上解决AI生成痕迹问题
"""
import sys
import os
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录（相对于当前工作目录）
PROJECT_DIR = Path(".")

def safe_name(name):
    """校验项目名，防止路径穿越"""
    if not name:
        return None
    if '..' in name:
        return None
    # 允许字母、数字、下划线、中划线、汉字
    if not re.match(r'^[\w\-\u4e00-\u9fff]+$', name):
        return None
    return name

def resolve_project():
    """解析当前项目路径（自动查找项目根目录）"""
    current = Path.cwd()
    # 向上查找 state.json
    for parent in [current] + list(current.parents):
        if (parent / "state.json").exists():
            return parent
    return None

def cmd_init(project_name):
    """初始化新项目: novel init <项目名>"""
    if not safe_name(project_name):
        print("❌ 项目名只能包含字母、数字、下划线、中划线、汉字")
        return
    
    project = PROJECT_DIR / project_name
    if project.exists():
        print(f"❌ 项目 {project_name} 已存在")
        return
    
    # 创建目录结构
    project.mkdir(parents=True, exist_ok=True)
    (project / "settings").mkdir(exist_ok=True)
    (project / "settings" / "characters").mkdir(exist_ok=True)
    (project / "settings" / "geography").mkdir(exist_ok=True)
    (project / "settings" / "examples").mkdir(exist_ok=True)
    (project / "chapters").mkdir(exist_ok=True)
    (project / "chapters" / "plans").mkdir(exist_ok=True)
    (project / "tracker").mkdir(exist_ok=True)
    (project / "references").mkdir(exist_ok=True)
    
    # 创建状态文件
    state = {
        "name": project_name,
        "current_arc": 1,
        "current_chapter": 0,
        "word_count_today": 0,
        "last_updated": "",
        "setting_completion": 0,
        "example_coverage": 0,
        "plan_completion": 0
    }
    with open(project / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    # 创建基础文件
    (project / "settings" / "world.md").write_text("# 世界观设定\n\n", encoding="utf-8")
    (project / "settings" / "rules.md").write_text("# 世界规则\n\n", encoding="utf-8")
    (project / "chapters" / "outline.md").write_text("# 大纲\n\n", encoding="utf-8")
    (project / "tracker" / "foreshadowing.md").write_text("# 伏笔追踪\n\n", encoding="utf-8")
    (project / "tracker" / "conflicts.md").write_text("# 冲突记录\n\n", encoding="utf-8")
    (project / "tracker" / "feedback.md").write_text("# 读者反馈\n\n", encoding="utf-8")
    
    print(f"✅ 项目 {project_name} 创建成功")
    print(f"   目录：{project}/")
    print(f"\n下一步：")
    print(f"  1. 录入设定：novel setting world <内容>")
    print(f"  2. 创建设定点范例：novel example <设定点名> <范例内容>")
    print(f"  3. 创建角色情绪词库：novel emotion <角色名>")

def cmd_setting(setting_type, content, example_content=""):
    """录入设定: novel setting <类型> <内容> [--example 范例内容]
    
    类型: world / character / rule / geography
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    if setting_type not in ("world", "character", "rule", "geography"):
        print("❌ 类型必须是: world / character / rule / geography")
        return
    
    # 录入设定
    if setting_type == "character":
        # 角色设定存到独立文件
        char_name = content.split('\n')[0].strip('# ') if '\n' in content else "unknown"
        char_file = project / "settings" / "characters" / f"{char_name}.md"
        char_file.write_text(content, encoding="utf-8")
        
        # 同时创建情绪词库模板
        emotion_file = project / "settings" / "characters" / f"{char_name}-emotion.md"
        if not emotion_file.exists():
            emotion_template = """# 角色：{char_name}

## 情绪状态 → 用词特征映射

### 愤怒
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：

### 自卑/怯懦
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：

### 悲伤/绝望
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：

### 兴奋/喜悦
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：

### 冷静/算计
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：

### 紧张/恐惧
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：

### 疲惫/麻木
- 动词倾向：
- 形容词倾向：
- 句式倾向：
- 禁忌：
""".format(char_name=char_name)
            emotion_file.write_text(emotion_template, encoding="utf-8")
            print(f"✅ 已创建情绪词库模板：{emotion_file}")
    else:
        # 其他设定追加到对应文件
        type_map = {
            "world": "world.md",
            "rule": "rules.md",
            "geography": "geography.md"
        }
        setting_file = project / "settings" / type_map[setting_type]
        entry = f"\n## {setting_type.capitalize()}设定\n\n{content}\n"
        with open(setting_file, "a", encoding="utf-8") as f:
            f.write(entry)
    
    print(f"✅ {setting_type} 设定已录入")
    
    # 如果提供了范例内容，创建设定点范例
    if example_content:
        example_file = project / "settings" / "examples" / f"{content[:20]}.md"
        example_content_full = f"# 设定点：{content[:50]}\n\n{example_content}\n"
        example_file.write_text(example_content_full, encoding="utf-8")
        print(f"✅ 已创建设定点范例：{example_file}")

def cmd_example(setting_point, example_content):
    """创建设定点写作范例: novel example <设定点名> <范例内容>
    
    范例内容格式：
    ## 角度一：直接描写
    <内容>
    
    ## 角度二：对话体现
    <内容>
    ...
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    example_file = project / "settings" / "examples" / f"{setting_point}.md"
    
    if example_file.exists():
        # 追加新角度
        with open(example_file, "a", encoding="utf-8") as f:
            f.write(f"\n{example_content}\n")
        print(f"✅ 已追加范例角度到：{example_file}")
    else:
        # 创建新范例文件
        content = f"# 设定点：{setting_point}\n\n{example_content}\n"
        example_file.write_text(content, encoding="utf-8")
        print(f"✅ 已创建设定点范例：{example_file}")
    
    # 更新状态中的范例覆盖度
    update_example_coverage(project)

def update_example_coverage(project):
    """更新状态中的范例覆盖度"""
    state_file = project / "state.json"
    if not state_file.exists():
        return
    
    state = json.loads(state_file.read_text(encoding="utf-8"))
    
    # 统计设定点数和范例数
    settings_count = 0
    examples_count = len(list((project / "settings" / "examples").glob("*.md")))
    
    # 简单估算：每个设定文件中的设定点数
    for md_file in (project / "settings").rglob("*.md"):
        if md_file.stat().st_size > 50:  # 非空文件
            content = md_file.read_text(encoding="utf-8")
            settings_count += content.count("##")  # 粗略统计
    
    if settings_count > 0:
        state["example_coverage"] = round(examples_count / settings_count * 100, 1)
    
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def cmd_emotion(character_name, emotion_state, word_features):
    """更新角色情绪词库: novel emotion <角色名> <情绪状态> <用词特征>
    
    用词特征格式：
    动词倾向：砸、撕、掐
    形容词倾向：尖锐、滚烫
    句式倾向：短句、断句
    禁忌：平静叙述
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    emotion_file = project / "settings" / "characters" / f"{character_name}-emotion.md"
    
    if not emotion_file.exists():
        print(f"❌ 角色 {character_name} 的情绪词库不存在")
        print(f"   请先创建角色设定：novel setting character <角色设定>")
        return
    
    # 读取现有内容
    content = emotion_file.read_text(encoding="utf-8")
    
    # 检查情绪状态是否已存在
    if f"### {emotion_state}" in content:
        # 更新现有情绪状态
        # 简单实现：直接追加到文件末尾，实际使用时应该解析并替换
        print(f"⚠️  情绪状态 {emotion_state} 已存在，请手动编辑文件：{emotion_file}")
    else:
        # 追加新情绪状态
        new_section = f"\n### {emotion_state}\n{word_features}\n"
        with open(emotion_file, "a", encoding="utf-8") as f:
            f.write(new_section)
        print(f"✅ 已添加情绪状态 {emotion_state} 到 {character_name} 的情绪词库")

def cmd_plan(chapter, plan_content=""):
    """创建/更新章节计划: novel plan <章节号> [计划内容]
    
    如果不提供计划内容，将创建空白模板
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    try:
        chapter = int(chapter)
    except ValueError:
        print("❌ 章节号必须是数字")
        return
    
    plan_dir = project / "chapters" / "plans"
    plan_file = plan_dir / f"ch-{chapter:03d}-plan.md"
    
    if plan_content:
        # 如果提供了计划内容，直接写入
        plan_file.write_text(plan_content, encoding="utf-8")
    elif plan_file.exists():
        # 如果计划已存在，提示用户编辑
        print(f"📋 第{chapter}章计划已存在：{plan_file}")
        print(f"   请直接编辑该文件")
    else:
        # 创建空白计划模板
        template = f"""# 第{chapter}章 创作计划

## 基本信息
- 章节标题：
- 所属卷：
- 预计字数：

## ★ 三要素约束

### 要素①：行文风格
- 节奏分布：[快-慢-快] / [慢-快-慢] / [匀速紧张] / [舒缓铺陈]
- 单句段落：至少___处
- 长段落（>200字）：不超过___处
- 对话占比：约___%
- 章节开头方式：<必须与前章不同>
- 章节结尾方式：<禁止总结性点题>

### 要素②：创作重点
- 核心偏向：[ ] 感情戏 [ ] 剧情推进 [ ] 背景介绍 [ ] 环境描写 [ ] 动作场面 [ ] 内心戏 [ ] 对话戏
- 重点说明：
- 内容比重：

### 要素③：情绪基调
- 主情绪：
- 情绪变化：起始→转折→结尾
- 角色情绪：
  - 主角：→ 参照情绪词库
  - 配角：→ 参照情绪词库
- 用词约束：

## ★ 负面约束
- [ ] 禁止直白点题
- [ ] 禁止精确数字（例外：___）
- [ ] 禁止重复前章用词
- [ ] 禁止连续3段相同句式
- [ ] 禁止节奏均匀分布
- [ ] 禁止使用水字数过渡词

## 设定点引用
| 设定点 | 选用范例角度 | 改编说明 |
|--------|-------------|---------|

## 伏笔计划
- 埋入：
- 收回：
"""
        plan_file.write_text(template, encoding="utf-8")
        print(f"✅ 第{chapter}章计划模板已创建：{plan_file}")
        print(f"   请编辑该文件，填写三要素")
    
    # 更新状态中的计划完成度
    update_plan_completion(project)

def update_plan_completion(project):
    """更新状态中的计划完成度"""
    state_file = project / "state.json"
    if not state_file.exists():
        return
    
    state = json.loads(state_file.read_text(encoding="utf-8"))
    total_chapters = state.get("current_chapter", 0)
    
    if total_chapters > 0:
        planned = len(list((project / "chapters" / "plans").glob("ch-*-plan.md")))
        state["plan_completion"] = round(planned / total_chapters * 100, 1)
    
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def cmd_write(chapter, content, from_file=""):
    """撰写章节: novel write <章节号> <正文> [--file 文件路径]
    
    写前检查章节计划是否存在
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    try:
        chapter = int(chapter)
    except ValueError:
        print("❌ 章节号必须是数字")
        return
    
    # 检查章节计划是否存在
    plan_file = project / "chapters" / "plans" / f"ch-{chapter:03d}-plan.md"
    if not plan_file.exists():
        print(f"⚠️  警告：第{chapter}章的章节计划不存在")
        print(f"   建议先创建计划：novel plan {chapter}")
        resp = input("   是否继续写作？（y/N）")
        if resp.lower() != 'y':
            return
    
    # 读取正文内容
    if from_file:
        try:
            content = Path(from_file).read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ 无法读取文件: {e}")
            return
    
    # 保存章节
    arc = (chapter - 1) // 30 + 1
    arc_dir = project / "chapters" / f"arc-{arc}"
    arc_dir.mkdir(exist_ok=True)
    chapter_file = arc_dir / f"chapter-{chapter:03d}.txt"
    chapter_file.write_text(content, encoding="utf-8")
    
    # 更新状态
    state_file = project / "state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["current_chapter"] = chapter
    state["current_arc"] = arc
    state["word_count_today"] = state.get("word_count_today", 0) + len(content)
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ 第{chapter}章已保存（字数：{len(content)}）")
    print(f"   建议下一步：执行自检 novel selfcheck {chapter}")

def cmd_selfcheck(chapter):
    """章节自检: novel selfcheck <章节号>
    
    检测AI痕迹：
    1. 精确数字
    2. 直白点题
    3. 水字数过渡词
    4. 段落长度均匀度
    5. 用词重复
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    try:
        chapter = int(chapter)
    except ValueError:
        print("❌ 章节号必须是数字")
        return
    
    # 读取章节正文
    arc = (chapter - 1) // 30 + 1
    chapter_file = project / "chapters" / f"arc-{arc}" / f"chapter-{chapter:03d}.txt"
    
    if not chapter_file.exists():
        print(f"❌ 第{chapter}章正文不存在")
        return
    
    content = chapter_file.read_text(encoding="utf-8")
    
    # 执行自检
    issues = []
    suggestions = []
    
    # 1. 精确数字检测
    precise_numbers = re.findall(r'\d+\.?\d*', content)
    if precise_numbers:
        issues.append(f"⚠️  发现精确数字 {len(precise_numbers)} 处")
        suggestions.append(f"   建议：将精确数字替换为模糊表达（如'{precise_numbers[0]}' → '数...'/'百来...'）")
    
    # 2. 直白点题检测
    point_themes = re.findall(r'(这说明|他意识到|这一刻他明白|从此以后他)', content)
    if point_themes:
        issues.append(f"⚠️  发现直白点题表达 {len(point_themes)} 处")
        suggestions.append(f"   建议：删除直白总结句，让主题通过情节/动作/对话自然体现")
    
    # 3. 水字数过渡词检测
    filler_words = ['略过', '跳过', '很快', '不久之后', '转眼间', '数日后']
    found_fillers = [w for w in filler_words if w in content]
    if found_fillers:
        issues.append(f"⚠️  发现水字数过渡词：{', '.join(found_fillers)}")
        suggestions.append(f"   建议：用场景切换或时间锚点代替过渡词")
    
    # 4. 段落长度均匀度检测
    paragraphs = content.split('\n\n')
    para_lengths = [len(p) for p in paragraphs if p.strip()]
    if para_lengths:
        avg_len = sum(para_lengths) / len(para_lengths)
        variance = sum((l - avg_len) ** 2 for l in para_lengths) / len(para_lengths)
        if variance < 500:  # 方差小说明分布均匀
            issues.append(f"⚠️  段落长度分布可能过于均匀（方差={variance:.0f}）")
            suggestions.append(f"   建议：有意混合短段（1-2句）和长段（>200字）")
    
    # 5. 高频词检测（简化版）
    words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
    
    high_freq = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
    high_freq_words = [w for w, c in high_freq if c > 10]
    
    if high_freq_words:
        issues.append(f"⚠️  高频词（出现>10次）：{', '.join(high_freq_words[:5])}")
        suggestions.append(f"   建议：替换部分高频词，增加用词多样性")
    
    # 6. 情绪词库合规检查（新增）
    emotion_words_used = []
    emotion_words_missing = []
    
    # 读取章节计划中的强制用词清单
    plan_file = project / "chapters" / "plans" / f"ch-{chapter:03d}-plan.md"
    if plan_file.exists():
        plan_content = plan_file.read_text(encoding="utf-8")
        
        # 检查是否填写了强制用词清单
        if "★ 强制用词清单" in plan_content:
            print(f"\n📋 检测到章节计划中有强制用词清单，执行合规检查...")
            
            # 简化检查：检测是否使用了"说/道"
            if "说" in content or "道" in content:
                issues.append(f"⚠️  检测到'说/道'对话标签，建议使用情绪标签")
                suggestions.append(f"   建议：打开 references/style-guide.md 的'对话标签词库'，选择合适的情绪标签")
            
            # 简化检查：检测是否使用了AI常用空词
            ai_empty_words = ["非常", "十分", "极其", "相当", "颇为"]
            found_ai_words = [w for w in ai_empty_words if w in content]
            if found_ai_words:
                issues.append(f"⚠️  检测到AI常用空词：{', '.join(found_ai_words)}")
                suggestions.append(f"   建议：用具体感官细节代替程度副词")
        else:
            print(f"\n⚠️  章节计划中未填写强制用词清单，跳过词库合规检查")
            print(f"   建议：编辑章节计划，填写'★ 强制用词清单'部分")
    
    # 7. 精确数字检查增强（新增）
    # 检查是否有未模糊化的数字
    precise_numbers = re.findall(r'\d+\.?\d*', content)
    if precise_numbers:
        # 读取章节计划中的例外说明
        exception_count = 0
        if plan_file.exists():
            plan_content = plan_file.read_text(encoding="utf-8")
            # 简单统计"例外"出现的次数
            exception_count = plan_content.count("例外")
        
        if len(precise_numbers) > exception_count:
            issues.append(f"⚠️  发现 {len(precise_numbers)} 处精确数字，但计划中只注明了 {exception_count} 处例外")
            suggestions.append(f"   建议：将多余精确数字替换为模糊表达（参考 references/style-guide.md 的'模糊数字表达词库'）")
    
    # 输出报告
    print(f"📋 第{chapter}章 自检报告")
    print(f"=" * 50)
    
    if issues:
        for i, issue in enumerate(issues):
            print(issue)
            if i < len(suggestions):
                print(suggestions[i])
    else:
        print("✅ 未发现明显AI痕迹")
    
    # 生成自检报告文件
    report_file = project / "tracker" / f"selfcheck-ch{chapter:03d}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# 第{chapter}章 自检报告\n\n")
        f.write(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if issues:
            for issue in issues:
                f.write(f"- {issue}\n")
        else:
            f.write("✅ 未发现明显AI痕迹\n")
    
    print(f"\n📄 详细报告已保存：{report_file}")

def cmd_outline(outline_text):
    """追加大纲内容: novel outline <大纲内容>"""
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    outline_file = project / "chapters" / "outline.md"
    
    # 计算下一个大纲编号
    if outline_file.exists():
        content = outline_file.read_text(encoding="utf-8")
        matches = re.findall(r'## 第(\d+)节', content)
        next_num = max([int(m) for m in matches]) + 1 if matches else 1
    else:
        next_num = 1
    
    entry = f"\n## 第{next_num}节\n\n{outline_text}\n"
    with open(outline_file, "a", encoding="utf-8") as f:
        f.write(entry)
    
    print(f"✅ 大纲已追加（第{next_num}节）")
    print(f"💡 提示：写正文前请先创建章节计划（novel plan <章号>）")

def cmd_check(chapter=None):
    """伏笔检测: novel check [章节号]"""
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    fs_file = project / "tracker" / "foreshadowing.md"
    if not fs_file.exists():
        print("⚠️ 无伏笔记录")
        return
    
    content = fs_file.read_text(encoding="utf-8")
    pending = []
    for line in content.split("\n"):
        if "[章" in line and "→" in line and line.strip() and not line.strip().startswith("#"):
            pending.append(line.strip())
    
    if pending:
        print(f"⚠️ 当前有 {len(pending)} 条伏笔待回收：")
        for p in pending:
            print(f"   {p}")
    else:
        print("✅ 无待回收伏笔")
    
    if chapter:
        try:
            ch = int(chapter)
        except ValueError:
            print("❌ 章节号必须是数字")
            return
        in_chapter = [p for p in pending if f"章{ch}" in p]
        print(f"\n📖 第{ch}章相关伏笔：{len(in_chapter)} 条")
        for p in in_chapter:
            print(f"   {p}")

def cmd_feedback(chapter, feedback, feedback_type="general"):
    """读者反馈入库: novel feedback <章节号> <反馈内容> [--type 类型]
    
    类型：ai-trace / plot / other
    """
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    try:
        ch = int(chapter)
    except ValueError:
        print("❌ 章节号必须是数字")
        return
    
    fb_file = project / "tracker" / "feedback.md"
    
    # 分类标记
    type_mark = ""
    if feedback_type == "ai-trace":
        type_mark = "【AI痕迹】"
    elif feedback_type == "plot":
        type_mark = "【剧情】"
    
    entry = f"- [章{ch}] {type_mark} {feedback} ({datetime.now().strftime('%Y-%m-%d')})\n"
    with open(fb_file, "a", encoding="utf-8") as f:
        f.write(entry)
    
    print(f"✅ 反馈已入库（第{ch}章）")
    
    # 如果是AI痕迹类反馈，提示
    if feedback_type == "ai-trace":
        print(f"💡 提示：AI痕迹类反馈已记录，请在下一章计划中针对性改进")

def cmd_conflict(new_content):
    """冲突检测: novel conflict <待检测内容>"""
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    # 读取所有设定文件
    settings = {}
    for md in (project / "settings").rglob("*.md"):
        settings[md.name] = md.read_text(encoding="utf-8")
    
    # 读取已有章节
    for arc_dir in (project / "chapters").iterdir():
        if arc_dir.is_dir() and arc_dir.name.startswith("arc-"):
            for ch_file in arc_dir.glob("chapter-*.txt"):
                key = f"chapters/{arc_dir.name}/{ch_file.name}"
                settings[key] = ch_file.read_text(encoding="utf-8")
    
    # 检测冲突（简化版：检查关键词是否重复）
    conflicts = []
    words = re.findall(r'[\w\u4e00-\u9fff]{2,}', new_content)
    checked = set()
    
    for word in words[:50]:  # 限制检查前50个词
        if word in checked:
            continue
        checked.add(word)
        
        for fname, text in settings.items():
            if word in text and len(word) > 1:
                conflicts.append(f"⚠️ 关键词 '{word}' 已在 {fname} 中出现")
                break
    
    if conflicts:
        print(f"⚠️ 发现 {len(conflicts)} 处潜在冲突：")
        for c in conflicts[:10]:
            print(f"   {c}")
    else:
        print("✅ 未检测到明显冲突")

def cmd_status():
    """查看项目状态: novel status"""
    project = resolve_project()
    if not project:
        print("❌ 未找到项目，请先在项目目录下运行")
        return
    
    state_file = project / "state.json"
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
        print(f"📖 项目：{state.get('name', '未知')}")
        print(f"   当前章节：第{state.get('current_chapter',0)}章 / 第{state.get('current_arc',1)}卷")
        print(f"   今日字数：{state.get('word_count_today',0)}")
        print(f"   最后更新：{state.get('last_updated','')}")
        print(f"   设定完成度：{state.get('setting_completion',0)}%")
        print(f"   范例覆盖度：{state.get('example_coverage',0)}%")
        print(f"   计划完成度：{state.get('plan_completion',0)}%")
    
    # 伏笔统计
    fs_file = project / "tracker" / "foreshadowing.md"
    if fs_file.exists():
        pending = [l for l in fs_file.read_text(encoding="utf-8").split("\n") 
                   if "[章" in l and "→" in l and not l.startswith("#")]
        print(f"   待回收伏笔：{len(pending)} 条")
    
    # 反馈统计
    fb_file = project / "tracker" / "feedback.md"
    if fb_file.exists():
        fb_content = fb_file.read_text(encoding="utf-8")
        ai_trace_count = fb_content.count("【AI痕迹】")
        print(f"   AI痕迹类反馈：{ai_trace_count} 条")

def main():
    """主函数：解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="仿人类小说创作 CLI 工具",
        prog="novel"
    )
    
    sub = parser.add_subparsers(dest="command", help="可用命令")
    
    # init: 初始化项目
    p_init = sub.add_parser("init", help="初始化新项目: novel init <项目名>")
    p_init.add_argument("name", help="项目名")
    
    # setting: 录入设定
    p_set = sub.add_parser("setting", help="录入设定: novel setting <类型> <内容> [--example 范例]")
    p_set.add_argument("type", choices=["world", "character", "rule", "geography"], help="设定类型")
    p_set.add_argument("content", nargs="*", default=[], help="设定内容")
    p_set.add_argument("--example", dest="example", help="设定点写作范例")
    
    # example: 创建设定点范例
    p_example = sub.add_parser("example", help="创建设定点范例: novel example <设定点名> <范例内容>")
    p_example.add_argument("name", help="设定点名")
    p_example.add_argument("content", nargs="*", default=[], help="范例内容")
    
    # emotion: 更新角色情绪词库
    p_emotion = sub.add_parser("emotion", help="更新角色情绪词库: novel emotion <角色名> <情绪状态> <用词特征>")
    p_emotion.add_argument("character", help="角色名")
    p_emotion.add_argument("emotion", help="情绪状态")
    p_emotion.add_argument("features", nargs="*", default=[], help="用词特征")
    
    # plan: 创建章节计划
    p_plan = sub.add_parser("plan", help="创建章节计划: novel plan <章节号> [计划内容]")
    p_plan.add_argument("chapter", type=int, help="章节号")
    p_plan.add_argument("plan", nargs="*", default=[], help="计划内容（可选）")
    
    # write: 撰写章节
    p_write = sub.add_parser("write", help="撰写章节: novel write <章节号> <正文> [--file 文件路径]")
    p_write.add_argument("chapter", type=int, help="章节号")
    p_write.add_argument("content", nargs="*", default=[], help="章节正文")
    p_write.add_argument("--file", dest="from_file", help="从文件读取正文")
    
    # selfcheck: 章节自检
    p_check_ai = sub.add_parser("selfcheck", help="章节AI痕迹自检: novel selfcheck <章节号>")
    p_check_ai.add_argument("chapter", type=int, help="章节号")
    
    # outline: 大纲
    p_outline = sub.add_parser("outline", help="追加大纲: novel outline <大纲内容>")
    p_outline.add_argument("content", nargs="*", default=[], help="大纲内容")
    
    # check: 伏笔检测
    p_check = sub.add_parser("check", help="伏笔检测: novel check [章节号]")
    p_check.add_argument("chapter", nargs="?", default=None, help="章节号")
    
    # feedback: 读者反馈
    p_fb = sub.add_parser("feedback", help="读者反馈: novel feedback <章节号> <反馈内容> [--type 类型]")
    p_fb.add_argument("chapter", type=int, help="章节号")
    p_fb.add_argument("content", nargs="*", default=[], help="反馈内容")
    p_fb.add_argument("--type", dest="fb_type", default="general", 
                      choices=["general", "ai-trace", "plot"], help="反馈类型")
    
    # conflict: 冲突检测
    p_conf = sub.add_parser("conflict", help="冲突检测: novel conflict <待检测内容>")
    p_conf.add_argument("content", nargs="*", default=[], help="待检测内容")
    
    # status: 查看状态
    p_status = sub.add_parser("status", help="查看项目状态: novel status")
    
    # 解析参数
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    # 命令分发
    if args.command == "init":
        cmd_init(args.name)
    elif args.command == "setting":
        content = " ".join(args.content)
        example = args.example if hasattr(args, 'example') and args.example else ""
        cmd_setting(args.type, content, example)
    elif args.command == "example":
        content = " ".join(args.content)
        cmd_example(args.name, content)
    elif args.command == "emotion":
        features = " ".join(args.features)
        cmd_emotion(args.character, args.emotion, features)
    elif args.command == "plan":
        plan = " ".join(args.plan) if args.plan else ""
        cmd_plan(args.chapter, plan)
    elif args.command == "write":
        content = ""
        if hasattr(args, 'from_file') and args.from_file:
            try:
                content = Path(args.from_file).read_text(encoding="utf-8")
            except Exception as e:
                print(f"❌ 无法读取文件: {e}")
                sys.exit(1)
        else:
            content = " ".join(args.content)
        cmd_write(args.chapter, content, "" if not hasattr(args, 'from_file') else args.from_file)
    elif args.command == "selfcheck":
        cmd_selfcheck(args.chapter)
    elif args.command == "outline":
        cmd_outline(" ".join(args.content))
    elif args.command == "check":
        cmd_check(args.chapter)
    elif args.command == "feedback":
        fb_type = args.fb_type if hasattr(args, 'fb_type') else "general"
        cmd_feedback(args.chapter, " ".join(args.content), fb_type)
    elif args.command == "conflict":
        cmd_conflict(" ".join(args.content))
    elif args.command == "status":
        cmd_status()

if __name__ == "__main__":
    main()
