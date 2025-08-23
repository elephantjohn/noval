from typing import List, Dict, Optional, Any
from .templates_base import style_rules_common_user, style_rules_common_system


PLATFORM_VALUES = (
    "2. 有价值、有深度的原创内容\n"
    "3. 提供良好的阅读体验\n"
    "=== 我们坚决避免的内容 ===\n"
    "1. 违反法律法规的内容\n"
    "2. 不实或误导性信息\n"
    "3. 违背公序良俗的内容\n"
    "4. 纯营销性质的内容\n"
)


WORLD_SETTING = (
    "时代为架空中原王朝, 山海奇观与礼乐法度并立, 修行以心性为本, 以气脉与星象为辅, "
    "凡俗与仙门相互牵引而非割裂。"
)


def _join_summary_lines(summary_lines: List[str]) -> str:
    if not summary_lines:
        return "前情提要为空, 因为是开篇。"
    cleaned = [line.strip() for line in summary_lines if line.strip()]
    bullet = "\n".join(f"- {s}" for s in cleaned)
    return f"前情提要如下, 仅含关键因果与心性变化:\n{bullet}"


def build_chapter_messages(
    chapter_index: int,
    summary_lines: List[str],
    character_notes: Optional[Dict[str, str]] = None,
    story_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """
    Build messages for a given chapter.
    - chapter_index starts from 1
    - summary_lines are 8-12 concise bullets from previous chapter(s)
    - character_notes may include delta updates for main characters
    - story_context includes characters, plot threads, world details from StoryManager
    """
    summary_block = _join_summary_lines(summary_lines)

    # 构建人物档案块
    character_block = ""
    if story_context and "characters" in story_context:
        char_lines = list(story_context["characters"].values())
        if char_lines:
            character_block = "\n【人物档案】\n" + "\n".join(char_lines)
    elif character_notes:
        lines = [f"{k}: {v}" for k, v in character_notes.items() if v]
        if lines:
            character_block = "\n人物小传增量:\n" + "\n".join(lines)
    
    # 构建剧情线索块
    plot_block = ""
    if story_context and "plot_threads" in story_context:
        plot_lines = list(story_context["plot_threads"].values())
        if plot_lines:
            plot_block = "\n【剧情线索】\n" + "\n".join(plot_lines)
    
    # 构建世界观细节块
    world_detail_block = ""
    if story_context and "world_details" in story_context:
        if story_context["world_details"]:
            world_detail_block = "\n【世界设定补充】\n" + "\n".join(story_context["world_details"])
    
    # 构建历史章节概要块（改进：使用多章概要而非单章）
    enhanced_summary_block = summary_block
    if story_context and "recent_summaries" in story_context:
        if story_context["recent_summaries"]:
            recent = "\n".join(f"- {s}" for s in story_context["recent_summaries"])
            enhanced_summary_block = f"【近期剧情脉络】\n{recent}\n\n【上章详细】\n{summary_block}"

    style_block = (
        "风格要求: 想象力奔涌, 心怀高远理想与不凡愿望; 语言可宏阔但不空喊口号, "
        "以细节与行动承载理想; 不低俗, 不血腥, 不狂躁; 叙事以因果推进, 人物以选择承担代价。\n"
        + style_rules_common_user
    )

    chapter_goal_map = {
        1: "写出穿越的契机与清晰代价, 确立世界规则与初始冲突, 主角作出一次承担代价的选择。",
        2: "初涉江湖与结义同道, 小胜引出更大难题, 得入门法器与关键线索。",
        3: "门墙抉择与旧债牵引, 为传承与自由付出可见代价, 立志不做笼中人。",
        4: "秘境试炼与情愫初生, 在共同风险中见真心, 立下并肩之约而不急于表白。",
        5: "都城风云与权术回潮, 理想与秩序碰撞, 挚友受牵连, 主角择义护人。",
        6: "遗族秘史与身世反转, 愿望代价提升, 爱情遭遇误解又见坚守。",
        7: "劫兆初临众议分歧, 群心难齐, 主角以担当凝聚各方但不强行。",
        8: "群峰夜会伏笔揭幕, 真相与牺牲并至, 理想由个人火焰迈向众人灯塔。",
        9: "终局回响与长路启程, 主线收束而不封死, 留下可持续的光与愿。",
    }
    chapter_goal = chapter_goal_map.get(
        chapter_index,
        "推进主线与人物成长, 留下温火悬念并种下下一章目标。",
    )

    structure_block = (
        "结构为起承转合四段, 每段约八百至九百字; 结尾留下温火而有力的悬念; "
        "只输出纯小说正文, 不写任何标题、编号、分隔符或元信息; "
        "不要在文末写下一章预告或写作意图。"
    )

    word_count_block = "字数为三千四百至三千六百字。"

    user_prompt = (
        f"请写第{chapter_index}章正文。\n"
        f"{enhanced_summary_block}"
        f"{character_block}"
        f"{plot_block}"
        f"{world_detail_block}\n"
        f"世界观: {WORLD_SETTING}\n"
        f"本章目标: {chapter_goal}\n"
        f"{style_block}\n{structure_block}\n{word_count_block}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "你是一位擅长中国古代玄幻长篇创作的作家, "+
                "将平台价值观内化为写作底线, 保证内容有思想厚度与人性温度。"+
                "重要：只输出小说正文内容，不要输出任何其他信息。\n"+
                style_rules_common_system + "\n"+
                PLATFORM_VALUES
            ),
        },
        {"role": "user", "content": user_prompt},
    ]
    return messages


def build_summary_messages(chapter_text: str) -> List[Dict[str, str]]:
    """
    Ask model to summarize the chapter into 8-12 concise Chinese bullet lines.
    """
    prompt = (
        "请将以下正文提炼为前情提要, 要求: 只写关键因果与人物心性变化; "
        "每条二十至三十字; 共八至十二条; 使用换行分条; 不写编号与多余符号。\n\n"
        "【正文】\n" + chapter_text
    )
    return [
        {"role": "system", "content": "你是严谨的文学编辑, 擅长提炼剧情要点。"},
        {"role": "user", "content": prompt},
    ]


