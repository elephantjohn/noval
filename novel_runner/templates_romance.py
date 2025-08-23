"""
追妻/后悔流虐文小说模板
"""
from typing import List, Dict, Optional, Any
from .templates_base import style_rules_common_user, style_rules_common_system


PLATFORM_VALUES = (
    "1. 情感真实、细腻、打动人心\n"
    "2. 剧情合理、冲突强烈、转折自然\n"
    "3. 人物立体、性格鲜明、成长清晰\n"
    "=== 我们坚决避免的内容 ===\n"
    "1. 违反法律法规的内容\n"
    "2. 过度暴力或不当描写\n"
    "3. 违背公序良俗的内容\n"
    "4. 缺乏逻辑的狗血剧情\n"
)


WORLD_SETTING = (
    "现代都市背景，商业精英与豪门世家的生活圈。"
    "男女主角曾是夫妻，因误会、背叛或家族利益而分离。"
    "涉及商战、家族恩怨、亲子关系等多重矛盾。"
    "情感基调：虐恋情深，先虐后甜，追妻火葬场。"
)


# 追妻流经典剧情结构
STORY_STRUCTURE = {
    "arc1_虐心离别": {
        "chapters": [1, 2, 3],
        "theme": "误会重重，关系破裂，痛苦分离",
        "emotion": "压抑、心碎、绝望"
    },
    "arc2_各自煎熬": {
        "chapters": [4, 5, 6],
        "theme": "分离后的生活，表面坚强内心痛苦",
        "emotion": "隐忍、思念、悔恨初现"
    },
    "arc3_真相渐明": {
        "chapters": [7, 8, 9],
        "theme": "误会解开，男主醒悟，开始追妻",
        "emotion": "懊悔、自责、急切"
    },
    "arc4_追妻之路": {
        "chapters": [10, 11, 12],
        "theme": "男主各种追求，女主心防难破",
        "emotion": "执着、心软、纠结"
    },
    "arc5_破镜重圆": {
        "chapters": [13, 14, 15],
        "theme": "历经考验，重新在一起",
        "emotion": "释然、感动、甜蜜"
    }
}


def _join_summary_lines(summary_lines: List[str]) -> str:
    if not summary_lines:
        return "前情提要：故事开始。"
    cleaned = [line.strip() for line in summary_lines if line.strip()]
    bullet = "\n".join(f"- {s}" for s in cleaned)
    return f"前情提要：\n{bullet}"


def _join_recent_window(recent_summaries: List[str]) -> str:
    if not recent_summaries:
        return ""
    cleaned = [s.strip() for s in recent_summaries if s.strip()]
    if not cleaned:
        return ""
    body = "\n".join(f"- {s}" for s in cleaned)
    return f"\n【近期剧情脉络】(近3-5章)\n{body}\n"


def build_chapter_messages_romance(
    chapter_index: int,
    summary_lines: List[str],
    character_notes: Optional[Dict[str, str]] = None,
    story_context: Optional[Dict[str, Any]] = None,
    character_manager=None,
    scene_manager=None,
) -> List[Dict[str, str]]:
    """
    构建追妻流小说章节的提示词
    """
    summary_block = _join_summary_lines(summary_lines)
    recent_block = ""
    if story_context and "recent_summaries" in story_context:
        recent_block = _join_recent_window(story_context.get("recent_summaries", []))
    
    # 构建人物档案块
    character_block = ""
    if story_context and "characters" in story_context:
        char_lines = list(story_context["characters"].values())
        if char_lines:
            character_block = "\n【人物状态】\n" + "\n".join(char_lines)
    
    # 构建情感线索块
    emotion_block = ""
    if story_context and "emotion_threads" in story_context:
        emotion_lines = list(story_context["emotion_threads"].values())
        if emotion_lines:
            emotion_block = "\n【情感进展】\n" + "\n".join(emotion_lines)
    
    # 根据章节确定当前阶段
    if chapter_index <= 3:
        arc = "arc1_虐心离别"
        emotion_guide = "重点描写：误会的产生、信任的崩塌、离别的痛苦。要让读者心疼女主，对男主又爱又恨。"
    elif chapter_index <= 6:
        arc = "arc2_各自煎熬"
        emotion_guide = "重点描写：分离后的空虚、对往事的回忆、内心的挣扎。展现两人都在受煎熬。"
    elif chapter_index <= 9:
        arc = "arc3_真相渐明"
        emotion_guide = "重点描写：真相的冲击、男主的悔恨、想要挽回的急切。让读者期待他们重新在一起。"
    elif chapter_index <= 12:
        arc = "arc4_追妻之路"
        emotion_guide = "重点描写：男主的真诚悔改、各种追求手段、女主的内心动摇。制造推拉感。"
    else:
        arc = "arc5_破镜重圆"
        emotion_guide = "重点描写：最后的考验、真心的证明、重新在一起的感动。要甜要治愈。"
    
    current_arc = STORY_STRUCTURE.get(arc, {})
    
    # 章节具体目标
    chapter_goals = {
        1: "开篇即虐：展现曾经恩爱的片段，然后急转直下，男主因误会/白月光回归而伤害女主，女主心死决定离婚/分手。",
        2: "决绝离去：女主坚决离开，男主还在自以为是，女主隐瞒重要秘密（如怀孕、病情等），制造强烈冲突。",
        3: "各奔东西：正式分离，女主开始新生活，男主还沉浸在过去，但开始感到不对劲。",
        4: "表面平静：女主努力重新开始，但夜深人静时的脆弱；男主开始频繁想起女主，但还在压抑。",
        5: "意外相遇：两人因工作/社交意外重逢，表面冷漠，内心波澜，旁人看出端倪。",
        6: "暗流涌动：通过他人视角展现两人的改变，男主开始调查当年的事，初见端倪。",
        7: "真相一角：部分真相曝光，男主震惊，开始意识到自己的错误，急于见女主。",
        8: "悔恨交加：男主知道全部真相，崩溃懊悔，开始疯狂寻找女主，女主刻意躲避。",
        9: "初次追求：男主找到女主，真诚道歉，女主冷漠拒绝，但内心已有波动。",
        10: "持续努力：男主用各种方式追求（送花、等待、保护等），女主表面不为所动。",
        11: "心防松动：通过某个事件（如女主遇险），男主奋不顾身，女主心防开始松动。",
        12: "进退两难：女主内心挣扎，想原谅但怕再次受伤，男主表现出改变和成长。",
        13: "最后考验：出现新的危机/考验，考验男主的真心，男主证明自己。",
        14: "冰释前嫌：女主终于原谅，两人坦诚相对，解开所有心结。",
        15: "甜蜜结局：重新在一起，弥补过去的遗憾，展望美好未来，温馨收尾。",
    }
    
    chapter_goal = chapter_goals.get(chapter_index, "推进剧情，深化情感冲突，为下一章做铺垫。")
    
    style_block = (
        "文风要求：情感细腻真实，对话贴近生活，心理描写深入，"
        "场景描写生动，节奏张弛有度。要让读者有代入感，情绪跟着起伏。"
        "多用细节展现情感，少用直白说教。虐要虐到心坎，甜要甜到发齁。\n"
        + style_rules_common_user
    )
    
    structure_block = (
        "结构为起承转合四段，每段约八百至九百字；"
        "开头要有钩子吸引读者，结尾要有悬念或情感爆点；"
        "只输出纯小说正文，不写任何标题、编号、分隔符或元信息。"
    )
    
    word_count_block = "字数为三千四百至三千六百字。"
    
    # 添加具体写作技巧
    technique_block = (
        "写作技巧：\n"
        "1. 多用动作和细节展现情感，如'手指微颤''眼眶泛红'等\n"
        "2. 对话要符合人物性格和当前情绪状态\n"
        "3. 适当使用倒叙、插叙增加张力\n"
        "4. 内心独白展现人物真实想法\n"
        "5. 环境描写烘托情绪氛围"
    )
    
    # 增强人物一致性提示
    character_consistency_block = ""
    if character_manager:
        # 获取主要人物的详细档案
        male_lead = character_manager.get_character_profile("陆景深", chapter_index)
        female_lead = character_manager.get_character_profile("苏念", chapter_index)
        
        if male_lead:
            traits = male_lead.get("traits")
            behavior = male_lead.get("chapter_specific", {})
            if traits:
                character_consistency_block += f"\n【陆景深人物一致性】\n"
                character_consistency_block += f"核心性格：{', '.join(traits.core_personality)}\n"
                character_consistency_block += f"说话习惯：{traits.common_phrases[0] if traits.common_phrases else ''}\n"
                character_consistency_block += f"行为习惯：{traits.habits[0] if traits.habits else ''}\n"
                character_consistency_block += f"本章表现：{behavior.get('态度', '')}，{behavior.get('语言', '')}\n"
        
        if female_lead:
            traits = female_lead.get("traits")
            behavior = female_lead.get("chapter_specific", {})
            if traits:
                character_consistency_block += f"\n【苏念人物一致性】\n"
                character_consistency_block += f"核心性格：{', '.join(traits.core_personality)}\n"
                character_consistency_block += f"说话习惯：{traits.common_phrases[0] if traits.common_phrases else ''}\n"
                character_consistency_block += f"行为习惯：{traits.habits[0] if traits.habits else ''}\n"
                character_consistency_block += f"本章表现：{behavior.get('态度', '')}，{behavior.get('语言', '')}\n"
    
    # 增强场景和节奏提示
    scene_rhythm_block = ""
    if scene_manager:
        scene_prompt = scene_manager.get_scene_prompt(chapter_index)
        if scene_prompt:
            scene_rhythm_block = f"\n【场景与节奏指导】\n{scene_prompt}\n"
    
    user_prompt = (
        f"请写第{chapter_index}章正文。\n"
        f"{summary_block}"
        f"{character_block}"
        f"{emotion_block}\n"
        f"{recent_block}"
        f"背景设定：{WORLD_SETTING}\n"
        f"当前阶段：{current_arc.get('theme', '')}（{current_arc.get('emotion', '')}）\n"
        f"本章目标：{chapter_goal}\n"
        f"{emotion_guide}\n"
        f"{character_consistency_block}"
        f"{scene_rhythm_block}"
        f"{style_block}\n"
        f"{technique_block}\n"
        f"{structure_block}\n{word_count_block}"
    )
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一位擅长现代都市情感小说创作的作家，尤其精通虐恋、追妻流等题材。"
                "你的作品情感真挚，虐点精准，能够深深打动读者的心。"
                "你懂得如何营造情感张力，制造冲突和转折。\n"
                + style_rules_common_system + "\n"
                + PLATFORM_VALUES
            ),
        },
        {"role": "user", "content": user_prompt},
    ]
    return messages


def build_summary_messages(chapter_text: str) -> List[Dict[str, str]]:
    """
    生成章节概要
    """
    prompt = (
        "请将以下正文提炼为前情提要，要求：\n"
        "1. 重点提取情感变化和关系进展\n"
        "2. 记录关键事件和转折点\n"
        "3. 每条二十至三十字\n"
        "4. 共八至十二条\n"
        "5. 不写编号与多余符号\n\n"
        "【正文】\n" + chapter_text
    )
    return [
        {"role": "system", "content": "你是专业的情感小说编辑，擅长提炼剧情要点和情感脉络。"},
        {"role": "user", "content": prompt},
    ]