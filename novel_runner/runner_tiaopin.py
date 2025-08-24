import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有 python-dotenv，尝试手动加载
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

from baidu_client.client import BaiduErnieClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('runner_tiaopin.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_ROOT = "outputs_调频_失谐"
CHAPTERS_DIR = os.path.join(OUTPUT_ROOT, "chapters")
SUMMARIES_DIR = os.path.join(OUTPUT_ROOT, "summaries")
LOGS_DIR = os.path.join(OUTPUT_ROOT, "logs")
STATE_PATH = os.path.join(OUTPUT_ROOT, "state.json")


def ensure_dirs() -> None:
    logger.info("创建输出目录...")
    os.makedirs(CHAPTERS_DIR, exist_ok=True)
    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    logger.info(f"输出目录已准备: {OUTPUT_ROOT}")


def sanitize_filename(title: str, chapter_number: int) -> str:
    # 保留汉字+英文+数字+下划线+中划线
    name = f"第{chapter_number}章-" + title
    # 替换空格为下划线
    name = name.replace(" ", "_")
    # 保留汉字、英文字母、数字、下划线和中划线
    name = re.sub(r"[^\u4e00-\u9fffa-zA-Z0-9_-]", "", name)
    if not name or name == f"第{chapter_number}章-":
        name = f"第{chapter_number}章"
    return name + ".md"


def read_blueprint() -> Dict[str, Any]:
    # 动态 import Python 蓝图，获取 story_blueprint 变量
    logger.info("加载故事蓝图...")
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from 调频.上部_失谐_创作蓝图 import story_blueprint  # type: ignore
    
    chapters_count = len(story_blueprint.get("story_blueprint", {}).get("chapters", []))
    characters_count = len(story_blueprint.get("character_dossier", {}))
    logger.info(f"蓝图加载完成: {chapters_count}章节, {characters_count}个角色")
    return story_blueprint


def extract_world_brief(world_md_path: str) -> str:
    # 读取完整文件，提取指定章节段落全文（简单做法：直接全量注入用户指定的五块）
    logger.info(f"读取世界观设定: {world_md_path}")
    with open(world_md_path, "r", encoding="utf-8") as f:
        content = f.read()
    logger.info(f"世界观设定已加载，长度: {len(content)}字符")
    # 简化：直接返回全文，由上层保证这是需要的五部分的文件（用户已确认）
    return content


def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        return {"generated_chapters": {}, "summaries": {}}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_existing_summary(label: str) -> Optional[str]:
    # label 形如 "01-20", "21-40" 等
    base = os.path.join(SUMMARIES_DIR, f"summary_{label}.txt")
    if os.path.exists(base):
        with open(base, "r", encoding="utf-8") as f:
            return f.read()
    return None


def write_text_with_conflict(dirpath: str, filename: str, text: str) -> str:
    # 若文件存在，追加日期后缀 YYYYMMDD-HHMM；同分钟内再次生成则追加序号
    target = os.path.join(dirpath, filename)
    if not os.path.exists(target):
        with open(target, "w", encoding="utf-8") as f:
            f.write(text)
        return target
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    name, ext = os.path.splitext(filename)
    candidate = os.path.join(dirpath, f"{name}_{ts}{ext}")
    if not os.path.exists(candidate):
        with open(candidate, "w", encoding="utf-8") as f:
            f.write(text)
        return candidate
    # 追加序号
    serial = 2
    while True:
        candidate = os.path.join(dirpath, f"{name}_{ts}_{serial}{ext}")
        if not os.path.exists(candidate):
            with open(candidate, "w", encoding="utf-8") as f:
                f.write(text)
            return candidate
        serial += 1


def build_system_prompt(genre_label: str, world_brief: str) -> str:
    # 专业科幻作家，强调口语化和自然表达
    rules = (
        "你是一位擅长口语化表达的科幻小说作家。写作风格要求：\n"
        "0. 【关键】字数要求：每章必须写满4000-5000汉字！当前只有1000多汉字远远不够！\n"
        "   汉字概念举例：'今天天气很好。'这句话包含6个汉字。你需要写4000-5000个这样的汉字！\n"
        "   汉字≠token！一个汉字=一个字符！必须数汉字字符数量达到4000-5000个！\n"
        "1. 语言极度口语化：用简单词汇，避免复杂书面语，多用短句和碎句\n"
        "2. 句式不规整：允许省略、倒装、插话，模拟真实对话和内心独白\n"
        "3. 表达自然随意：可以有'嗯''啊''这个''那个'等口语词，语序可以不完整\n"
        "4. 避免文绉绉：不用'然而''因此''倘若'等书面连词，改用'不过''所以''要是'\n"
        "5. 技术描述平衡：关键科幻设定需要精确描述，但表达方式要口语化\n"
        "6. 场景描写优先：重点描写环境、氛围、动作，营造画面感和文学性\n"
        "7. 详细描写要求：每个场景都要详细描写，包括环境细节、人物动作、心理活动、感官体验\n"
        "8. 叙事为主：按照剧情要点推进故事，对话适量即可，不要全是对话\n"
        "9. 对话格式：人物说话独占一行，用引号包围，如：\n"
        "   \"老七，给我看看数据。\"\n"
        "   \"好的，周工。\"\n"
        "仅输出纯正文，严禁出现任何元信息，如'正文开始''正文结束''以下是正文'等表述。\n"
    )
    system_prompt = f"{rules}\n[体裁主题]{genre_label}\n[世界观]\n{world_brief}"
    return system_prompt


def build_user_prompt(
    chapter: Dict[str, Any],
    character_dossier: Dict[str, Any],
    involved_characters: List[str],
    history_block: str,
) -> str:
    # 组装人物卡（去掉 name_analysis）
    cards: List[str] = []
    for name in involved_characters:
        if name in character_dossier:
            role = character_dossier[name].copy()
            role.pop("name_analysis", None)
            cards.append(json.dumps({name: role}, ensure_ascii=False, indent=2))
    cards_text = "\n".join(cards)

    fields = [
        ("编号", chapter.get("chapter_number")),
        ("标题建议", chapter.get("title_suggestion")),
        ("叙事弧", chapter.get("narrative_arc")),
        ("核心情节要点", chapter.get("core_plot_points")),
        ("场景", chapter.get("setting")),
        ("本章目的", chapter.get("purpose_in_story")),
        ("从此处开场", chapter.get("starts_from")),
        ("建议结尾悬念", chapter.get("ending_hook")),
    ]
    chapter_block = "\n".join(f"{k}: {v}" for k, v in fields if v is not None)

    user_prompt = (
        f"[此前剧情回顾]\n{history_block}\n\n"
        f"[本章出现人物]\n{', '.join(involved_characters)}\n\n"
        f"[人物设定]\n{cards_text}\n\n"
        f"[当前章节指令]\n{chapter_block}\n\n"
        f"[写作要求]\n"
        f"- 【重要】字数要求：必须写满4000-5000汉字！现在只有1000多汉字远远不够！\n"
        f"  汉字概念举例：'今天天气很好。'这句话包含6个汉字。你需要写4000-5000个这样的汉字！\n"
        f"  汉字≠token！一个汉字=一个字符！必须数汉字字符数量达到4000-5000个！\n"
        f"  请通过详细的场景描写、心理描写、环境描写、感官体验描写来达到字数要求！\n"
        f"- 仅输出纯正文，严禁出现'正文开始''正文结束''以下是正文'等元信息表述\n"
        f"- 保持时间线一致，不剧透未来\n"
        f"- 写作重点：\n"
        f"  * 场景描写优先：重点描写环境、氛围、人物动作和心理\n"
        f"  * 详细描写：每个场景都要详细描写环境细节、人物动作、心理活动、感官体验\n"
        f"  * 按照核心剧情要点叙事，营造画面感和文学性\n"
        f"  * 对话适量即可，不要全是对话，叙事描写为主\n"
        f"- 语言要极度口语化：\n"
        f"  * 多用短句、碎句，避免长难句\n"
        f"  * 用简单词汇，不要复杂书面语\n"
        f"  * 句式可以不完整，允许省略、插话\n"
        f"  * 对话和内心独白要像真人说话\n"
        f"  * 关键科幻设定保持精确，但表达要口语化\n"
        f"- 对话格式：人物说话独占一行，用引号包围\n"
        f"- 允许自然的'废话'和停顿，增加真实感\n"
    )
    return user_prompt


def gather_history_block(
    story: Dict[str, Any],
    summaries: Dict[str, str],
    current_idx: int,
) -> str:
    # 任意章节启动兜底：优先使用现有20章总结，再拼接剩余未总结章节的 core_plot_points 原文
    chapters: List[Dict[str, Any]] = story["story_blueprint"]["chapters"]
    parts: List[str] = []

    # 依序加入成段总结
    if "01-20" in summaries:
        parts.append(summaries["01-20"])
    if "21-40" in summaries:
        parts.append(summaries["21-40"])
    if "41-60" in summaries:
        parts.append(summaries["41-60"])

    # 拼接必要的未总结章节 core_plot_points（例如 41-当前-1）
    for idx in range(max(0, current_idx - 1) - 1, -1, -1):
        # 上面 parts 已经包含阶段总结，剩余拼接的范围由调用方确保（例如当有 21-40 总结时，只需拼接 41~current-1）
        break

    # 简化：调用方会构造合适的文本，这里直接返回拼好的段（在 run loop 中具体实现）
    return "\n\n".join(parts)


def call_llm(
    client: BaiduErnieClient,
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    logs_key: str,
) -> str:
    logger.info(f"准备调用LLM - 模型: {model_name}")
    logger.info(f"系统提示长度: {len(system_prompt)}字符")
    logger.info(f"用户提示长度: {len(user_prompt)}字符")
    
    # 追溯日志保存
    req_log = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }
    with open(os.path.join(LOGS_DIR, f"{logs_key}.request.json"), "w", encoding="utf-8") as f:
        json.dump(req_log, f, ensure_ascii=False, indent=2)

    logger.info("开始调用百度千帆API...")
    start_time = time.time()
    
    # 调用
    resp = client.chat_with_prompts(
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompts=user_prompt,
        temperature=0.35,
        top_p=0.9,
        penalty_score=1.1,
        frequency_penalty=0.2,
        presence_penalty=0.1,
        max_completion_tokens=12000,
        seed=2025,
    )
    
    elapsed_time = time.time() - start_time
    logger.info(f"API调用完成，耗时: {elapsed_time:.2f}秒")

    # 响应日志
    resp_log = {
        "timestamp": datetime.now().isoformat(),
        "model": resp.model,
        "finish_reason": resp.finish_reason,
        "usage": resp.usage,
        "error": resp.error,
    }
    with open(os.path.join(LOGS_DIR, f"{logs_key}.response.json"), "w", encoding="utf-8") as f:
        json.dump(resp_log, f, ensure_ascii=False, indent=2)

    if resp.error:
        logger.error(f"API调用失败: {resp.error}")
        raise RuntimeError(resp.error)
    
    content_length = len(resp.content or "")
    input_tokens = resp.usage.get("prompt_tokens", 0)
    output_tokens = resp.usage.get("completion_tokens", 0)
    logger.info(f"生成成功 - 内容长度: {content_length}字符")
    logger.info(f"Token使用 - 输入: {input_tokens}, 输出: {output_tokens}")
    
    return resp.content or ""


def run(args: argparse.Namespace) -> None:
    logger.info("=== 调频-失谐 长篇生成器启动 ===")
    ensure_dirs()
    state = load_state()
    story = read_blueprint()
    chapters: List[Dict[str, Any]] = story["story_blueprint"]["chapters"]
    character_dossier: Dict[str, Any] = story["character_dossier"]

    # 世界观全文（按约定直接注入）
    world_md = os.path.join(os.path.dirname(__file__), "..", "调频", "《调频》故事构思与世界观设定.md")
    world_brief = extract_world_brief(os.path.abspath(world_md))

    logger.info("初始化百度千帆客户端...")
    client = BaiduErnieClient()

    # 选择章节范围
    total = len(chapters)
    indices: List[int] = list(range(total))
    if args.only:
        indices = [i - 1 for i in args.only if 1 <= i <= total]
        logger.info(f"指定章节模式: 将生成第 {args.only} 章")
    else:
        start_idx = max(1, args.start) - 1
        end_idx = min(total, args.end) - 1 if args.end else total - 1
        indices = list(range(start_idx, end_idx + 1))
        logger.info(f"范围模式: 将生成第 {start_idx + 1} 到第 {end_idx + 1} 章 (共 {len(indices)} 章)")
    
    logger.info(f"预计总耗时: 约 {len(indices)} 小时 (每章1小时包含60s休眠)")

    # 预加载已存在的阶段总结
    summaries: Dict[str, str] = {}
    for label in ("01-20", "21-40", "41-60", "61-68"):
        s = load_existing_summary(label)
        if s:
            summaries[label] = s

    for i, idx in enumerate(indices, 1):
        chapter = chapters[idx]
        chapter_number = int(chapter.get("chapter_number", idx + 1))
        title = str(chapter.get("title_suggestion", f"第{chapter_number}章"))
        involved = str(chapter.get("main_focus_characters", "")).split()
        involved = [name.strip() for name in involved if name.strip()]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"开始生成第 {chapter_number} 章: {title}")
        logger.info(f"进度: {i}/{len(indices)} ({i/len(indices)*100:.1f}%)")
        logger.info(f"涉及角色: {', '.join(involved) if involved else '无'}")
        logger.info(f"{'='*60}")

        # 构造历史回顾块：根据当前进度与已有总结拼接
        logger.info("构建历史回顾上下文...")
        history_parts: List[str] = []
        
        # 阶段总结装入（若存在）
        summary_used = []
        if "01-20" in summaries and chapter_number >= 21:
            history_parts.append(summaries["01-20"])
            summary_used.append("01-20")
        if "21-40" in summaries and chapter_number >= 41:
            history_parts.append(summaries["21-40"])
            summary_used.append("21-40")
        if "41-60" in summaries and chapter_number >= 61:
            history_parts.append(summaries["41-60"])
            summary_used.append("41-60")
        
        if summary_used:
            logger.info(f"使用阶段总结: {', '.join(summary_used)}")
        
        # 追加最近未总结章节 core_plot_points 原文（例如 41~(n-1)）
        # 计算未总结起点
        if chapter_number <= 20:
            start_unrolled = 1
        elif 21 <= chapter_number <= 40:
            start_unrolled = 21
        elif 41 <= chapter_number <= 60:
            start_unrolled = 41
        else:
            start_unrolled = 61
            
        individual_chapters = []
        for j in range(start_unrolled, chapter_number):
            cp = chapters[j - 1].get("core_plot_points")
            if cp:
                history_parts.append(str(cp))
                individual_chapters.append(j)
        
        if individual_chapters:
            logger.info(f"添加未总结章节要点: 第{individual_chapters[0]}到第{individual_chapters[-1]}章")
        
        history_block = "\n\n".join(history_parts)
        logger.info(f"历史回顾构建完成，总长度: {len(history_block)}字符")

        system_prompt = build_system_prompt("科幻", world_brief)
        user_prompt = build_user_prompt(
            chapter=chapter,
            character_dossier=character_dossier,
            involved_characters=involved,
            history_block=history_block,
        )

        logs_key = f"chapter_{chapter_number:02d}"

        # 调用，失败重试一次
        attempt = 0
        last_err: Optional[Exception] = None
        while attempt < 2:
            try:
                content = call_llm(
                    client=client,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_name="ernie-x1-turbo-32k",
                    logs_key=logs_key,
                )
                # 写章节
                filename = sanitize_filename(title, chapter_number)
                path = write_text_with_conflict(CHAPTERS_DIR, filename, content)
                logger.info(f"章节文件已保存: {path}")
                
                # 更新状态
                state.setdefault("generated_chapters", {})[str(chapter_number)] = {
                    "path": path,
                    "timestamp": datetime.now().isoformat(),
                }
                save_state(state)
                logger.info(f"第 {chapter_number} 章生成完成！")
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                attempt += 1
                logger.error(f"第 {chapter_number} 章生成失败 (尝试 {attempt}/2): {str(e)}")
                if attempt < 2:
                    logger.info("20秒后重试...")
                    time.sleep(20)
                else:
                    # 错误日志
                    error_path = os.path.join(LOGS_DIR, f"{logs_key}.error.txt")
                    with open(error_path, "w", encoding="utf-8") as f:
                        f.write(str(e))
                    logger.error(f"第 {chapter_number} 章生成彻底失败，错误日志已保存: {error_path}")
                    raise

        # 间隔 60s
        logger.info("等待60秒后继续下一章...")
        time.sleep(60)

        # 阶段性总结生成（在边界生成）：20, 40, 60, 68
        if chapter_number in (20, 40, 60, 68):
            logger.info(f"\n{'*'*50}")
            logger.info(f"开始生成阶段总结 - 第 {chapter_number} 章边界")
            logger.info(f"{'*'*50}")
            
            # 汇总该阶段的 core_plot_points 原文
            if chapter_number == 20:
                label = "01-20"
                start_k = 1
            elif chapter_number == 40:
                label = "21-40"
                start_k = 21
            elif chapter_number == 60:
                label = "41-60"
                start_k = 41
            else:
                label = "61-68"
                start_k = 61

            logger.info(f"汇总第 {start_k} 到第 {chapter_number} 章的核心要点...")
            segment_points = []
            for j in range(start_k, chapter_number + 1):
                cp = chapters[j - 1].get("core_plot_points")
                if cp:
                    segment_points.append(str(cp))
            segment_source = "\n\n".join(segment_points)
            logger.info(f"要点汇总完成，总长度: {len(segment_source)}字符")

            # 用更大模型做事实复述总结
            sum_logs_key = f"summary_{label}"
            sum_system = (
                "你是一位严谨的剧情整理者。只基于给定文本做时间顺序复述，"
                "不新增设定/不改写因果/不评价，输出纯中文正文，目标2000字，允许上限2500字。\n"
            )
            sum_user = (
                "请将以下章节要点按时间顺序复述为连贯剧情，字数≈2000（≤2500）：\n\n"
                f"{segment_source}"
            )
            # 记录请求
            with open(os.path.join(LOGS_DIR, f"{sum_logs_key}.request.json"), "w", encoding="utf-8") as f:
                json.dump({"system": sum_system, "user": sum_user}, f, ensure_ascii=False, indent=2)

            # 调用总结模型（使用同一客户端但不同模型名）
            logger.info("调用大模型生成阶段总结...")
            start_time = time.time()
            summary_resp = client.chat_with_prompts(
                model_name="ernie-4.5-turbo-128k",
                system_prompt=sum_system,
                user_prompts=sum_user,
                temperature=0.0,
                top_p=0.8,
                max_completion_tokens=6500,
                seed=2025,
            )
            elapsed_time = time.time() - start_time
            logger.info(f"总结生成完成，耗时: {elapsed_time:.2f}秒")
            
            with open(os.path.join(LOGS_DIR, f"{sum_logs_key}.response.json"), "w", encoding="utf-8") as f:
                json.dump({"usage": summary_resp.usage, "error": summary_resp.error}, f, ensure_ascii=False, indent=2)
            if summary_resp.error:
                logger.error(f"阶段总结生成失败: {summary_resp.error}")
                raise RuntimeError(summary_resp.error)
            summary_text = summary_resp.content or ""
            logger.info(f"总结内容长度: {len(summary_text)}字符")
            
            # 写入总结文件
            base_name = f"summary_{label}.txt"
            path = write_text_with_conflict(SUMMARIES_DIR, base_name, summary_text)
            summaries[label] = summary_text
            logger.info(f"阶段总结已保存: {path}")
            
            # 更新状态
            state.setdefault("summaries", {})[label] = {"path": path, "timestamp": datetime.now().isoformat()}
            save_state(state)
            logger.info(f"阶段总结 {label} 生成完成！")
    
    logger.info(f"\n{'='*60}")
    logger.info("🎉 所有章节生成完成！")
    logger.info(f"共生成 {len(indices)} 章节")
    logger.info(f"输出目录: {OUTPUT_ROOT}")
    logger.info(f"{'='*60}")


def build_argparser() -> argparse.ArgumentParser:
    description = (
        "调频-失谐 长篇生成器 (单章一次调用，自动装配上下文)\n\n"
        "使用说明:\n"
        "- 本程序每一章只调用一次大模型；上下文来自：\n"
        "  1) 《调频》故事构思与世界观设定.md 指定的五大块全文\n"
        "  2) 本章出现人物的 character_dossier（除 name_analysis）\n"
        "  3) 历史回顾: 读取已有的20章总结；其余章节使用 core_plot_points 原文拼接\n"
        "- 严格串行执行；每章结束后自动休眠60s；失败最多重试1次（重试前等待20s）。\n\n"
        "输出位置:\n"
        "- 正文: outputs_调频_失谐/chapters/ 第N章_章节名.md（仅汉字+数字+下划线；冲突追加时间戳及序号）\n"
        "- 总结: outputs_调频_失谐/summaries/ summary_01-20.txt 等（存在则追加时间戳）\n"
        "- 日志: outputs_调频_失谐/logs/ 请求与响应快照\n\n"
        "运行示例 (推荐使用 -m 模块方式运行):\n"
        "- 生成全部68章 (完整小说):\n"
        "  python -m novel_runner.runner_tiaopin --start 1 --end 68\n"
        "- 生成1到3章:\n"
        "  python -m novel_runner.runner_tiaopin --start 1 --end 3\n"
        "- 仅生成指定章节（上下文仍会自动装入前序章节要点）:\n"
        "  python -m novel_runner.runner_tiaopin --only 5 12 20\n"
    )
    p = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--start", type=int, default=1, help="起始章节号(1-based)，默认1")
    p.add_argument("--end", type=int, default=0, help="结束章节号(含)。0表示直到最后一章")
    p.add_argument("--only", type=int, nargs="*", help="仅生成指定章节号列表（空格分隔）")
    return p


if __name__ == "__main__":
    parser = build_argparser()
    run(parser.parse_args())


