from typing import List, Dict, Optional


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
) -> List[Dict[str, str]]:
    """
    Build messages for a given chapter.
    - chapter_index starts from 1
    - summary_lines are 8-12 concise bullets from previous chapter(s)
    - character_notes may include delta updates for main characters
    """
    summary_block = _join_summary_lines(summary_lines)

    character_delta = ""
    if character_notes:
        lines = [f"{k}: {v}" for k, v in character_notes.items() if v]
        if lines:
            character_delta = "\n人物小传增量:\n" + "\n".join(lines)

    style_block = (
        "风格要求: 想象力奔涌, 心怀高远理想与不凡愿望; 语言可宏阔但不空喊口号, "
        "以细节与行动承载理想; 不低俗, 不血腥, 不狂躁; 叙事以因果推进, 人物以选择承担代价。"
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
        "只输出正文, 不写标题与编号; 文末补一句极短的下一章写作意图, 不超过三十字, 以句号结尾。"
    )

    word_count_block = "字数为三千四百至三千六百字。"

    user_prompt = (
        f"请写第{chapter_index}章正文。\n"
        f"{summary_block}{character_delta}\n"
        f"世界观: {WORLD_SETTING}\n"
        f"本章目标: {chapter_goal}\n"
        f"{style_block}\n{structure_block}\n{word_count_block}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "你是一位擅长中国古代玄幻长篇创作的作家, "+
                "将平台价值观内化为写作底线, 保证内容有思想厚度与人性温度。\n"+PLATFORM_VALUES
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


