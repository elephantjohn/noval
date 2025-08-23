"""
追妻流小说生成器
"""
import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

from .client import BaiduErnieClient
from .templates_romance import build_chapter_messages_romance, build_summary_messages
from .story_manager_romance import RomanceStoryManager
from .post_processor import clean_chapter_text, extract_clean_summary
from .censor_manager import CensorManager, generate_chapter_title
from .character_consistency import CharacterConsistencyManager
from .scene_manager import SceneManager
from .fact_manager import FactManager


def ensure_dirs(base_dir: Path) -> Dict[str, Path]:
    outputs = base_dir / "outputs_romance"
    chapters_dir = outputs / "chapters"
    summaries_dir = outputs / "summaries"
    logs_dir = outputs / "logs"
    for d in (outputs, chapters_dir, summaries_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)
    return {
        "outputs": outputs,
        "chapters": chapters_dir,
        "summaries": summaries_dir,
        "logs": logs_dir,
    }


def extract_text_from_response(data: Dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return str(data)
    if "result" in data and isinstance(data["result"], str):
        return data["result"]
    if "output" in data and isinstance(data["output"], str):
        return data["output"]
    if "choices" in data and data["choices"]:
        choice = data["choices"][0]
        msg = choice.get("message") or {}
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str):
                return content
        txt = choice.get("content")
        if isinstance(txt, str):
            return txt
    return str(data)


def run_romance_generation(
    model: str,
    base_dir: Path,
    chapters: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    dry_run: bool,
    start_chapter: int = 1,
    quiet: bool = False,
    wait_seconds: int = 60,
) -> None:
    paths = ensure_dirs(base_dir)
    chapters_dir = paths["chapters"]
    summaries_dir = paths["summaries"]
    logs_dir = paths["logs"]

    # Load .env
    env_path = base_dir / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if "=" not in s:
                continue
            key, value = s.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value

    client = None if dry_run else BaiduErnieClient()

    # 初始化故事管理器
    story_manager = RomanceStoryManager(paths["outputs"] / "story_state")
    
    # 初始化人物一致性管理器
    character_manager = CharacterConsistencyManager(paths["outputs"] / "character_state")
    
    # 初始化场景管理器
    scene_manager = SceneManager()
    
    # 初始化审核管理器
    censor_manager = None
    if not dry_run:
        text_api_key = os.environ.get('TEXT_API_KEY')
        text_secret_key = os.environ.get('TEXT_SECRET_KEY')
        if text_api_key and text_secret_key:
            censor_manager = CensorManager(
                api_key=text_api_key,
                secret_key=text_secret_key,
                ernie_client=client,
                logs_dir=logs_dir
            )
            if not quiet:
                print(f"[追妻流生成器] 已启用内容审核功能", flush=True)
    
    # 如果是续写，加载状态
    if start_chapter > 1:
        loaded = story_manager.load_state(start_chapter - 1)
        if loaded and not quiet:
            print(f"[追妻流生成器] 已加载第{start_chapter - 1}章的故事状态", flush=True)
        
        # 加载人物状态
        character_manager.load_state(start_chapter - 1)
    
    prev_summary_lines: List[str] = []

    if not quiet:
        print(f"[追妻流生成器] 开始生成: 类型=现代追妻虐恋, 章节数={chapters}", flush=True)
        print(f"[追妻流生成器] 情感主线: 误会分离→真相大白→追妻火葬场→破镜重圆", flush=True)

    for idx in range(start_chapter, chapters + 1):
        if not quiet:
            print(f"[追妻流生成器] ——— 第{idx}章 开始 ———", flush=True)
            
            # 显示当前情感阶段
            if idx <= 3:
                print(f"[追妻流生成器] 当前阶段: 【虐心离别】", flush=True)
            elif idx <= 6:
                print(f"[追妻流生成器] 当前阶段: 【各自煎熬】", flush=True)
            elif idx <= 9:
                print(f"[追妻流生成器] 当前阶段: 【真相渐明】", flush=True)
            elif idx <= 12:
                print(f"[追妻流生成器] 当前阶段: 【追妻之路】", flush=True)
            else:
                print(f"[追妻流生成器] 当前阶段: 【破镜重圆】", flush=True)
        
        # 获取故事上下文
        story_context = story_manager.get_context_for_chapter(idx)
        
        # 构建消息时传入管理器
        messages = build_chapter_messages_romance(
            idx, 
            prev_summary_lines, 
            story_context=story_context,
            character_manager=character_manager,
            scene_manager=scene_manager
        )

        # 生成章节
        if dry_run:
            chapter_text = f"【干跑模式】第{idx}章追妻流小说占位文本。"
        else:
            try:
                if not quiet:
                    print(f"[追妻流生成器] 第{idx}章: 请求大模型生成...", flush=True)
                data = client.chat_completions(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                raw_chapter_text = extract_text_from_response(data)
                chapter_text = clean_chapter_text(raw_chapter_text)
                
                # 保存日志
                (logs_dir / f"chapter_{idx:02d}.response.json").write_text(
                    str(data), encoding="utf-8"
                )
                (logs_dir / f"chapter_{idx:02d}.raw.txt").write_text(
                    raw_chapter_text, encoding="utf-8"
                )
            except Exception as e:
                err_path = logs_dir / f"chapter_{idx:02d}.error.txt"
                err_path.write_text(str(e), encoding="utf-8")
                if not quiet:
                    print(f"[追妻流生成器] 第{idx}章: 生成失败 → {err_path}", flush=True)
                raise

        # 事实抽取→冲突检测→最小回写
        fact_fixed_text = chapter_text
        try:
            if not dry_run:
                fact_mgr = FactManager(paths["outputs"] / "fact_state.json", client, model=model)
                fact_fixed_text, conflicts = fact_mgr.process_chapter(idx, fact_fixed_text, logs_dir)
                if conflicts and not quiet:
                    print(f"[追妻流生成器] 第{idx}章: 一致性修订后仍有潜在冲突 {len(conflicts)} 条, 已记录。", flush=True)
        except Exception as _e:
            if not quiet:
                print(f"[追妻流生成器] 第{idx}章: 事实一致性管线异常, 已跳过。", flush=True)

        # 内容审核
        final_chapter_text = fact_fixed_text
        is_compliant = True
        
        if censor_manager and not dry_run:
            if not quiet:
                print(f"[追妻流生成器] 第{idx}章: 开始内容审核...", flush=True)
            
            is_compliant, final_chapter_text = censor_manager.censor_and_fix_loop(
                fact_fixed_text, idx, max_retries=3
            )
            time.sleep(2)
        
        # 生成章节标题和保存
        if is_compliant:
            if censor_manager and not dry_run:
                chapter_title = generate_chapter_title(final_chapter_text, idx, client)
                chapter_filename = f"第{idx}章-{chapter_title}.md"
            else:
                # 默认章节标题（追妻流风格）
                default_titles = {
                    1: "决绝离婚", 2: "心如死灰", 3: "各奔东西",
                    4: "深夜思念", 5: "意外重逢", 6: "暗流涌动",
                    7: "真相初现", 8: "悔不当初", 9: "疯狂寻找",
                    10: "苦苦哀求", 11: "为她受伤", 12: "心防动摇",
                    13: "生死考验", 14: "真心相对", 15: "余生有你"
                }
                chapter_filename = f"第{idx}章-{default_titles.get(idx, f'章节{idx}')}.md"
        else:
            chapter_filename = f"第{idx}章_审核失败.md"
            if not quiet:
                print(f"[追妻流生成器] 第{idx}章: ⚠️ 审核未通过", flush=True)
        
        chapter_path = chapters_dir / chapter_filename
        chapter_path.write_text(final_chapter_text, encoding="utf-8")
        if not quiet:
            print(f"[追妻流生成器] 第{idx}章: 已保存 → {chapter_path}", flush=True)

        # 生成概要
        if dry_run:
            summary_text = "干跑模式概要"
        else:
            try:
                if not quiet:
                    print(f"[追妻流生成器] 第{idx}章: 生成概要...", flush=True)
                sum_messages = build_summary_messages(final_chapter_text)
                sum_data = client.chat_completions(
                    model=model,
                    messages=sum_messages,
                    temperature=0.6,
                    top_p=0.85,
                    max_tokens=800,
                )
                raw_summary = extract_text_from_response(sum_data)
                summary_lines = extract_clean_summary(raw_summary)
                summary_text = '\n'.join(summary_lines)
                (logs_dir / f"summary_{idx:02d}.response.json").write_text(
                    str(sum_data), encoding="utf-8"
                )
            except Exception as e:
                err_path = logs_dir / f"summary_{idx:02d}.error.txt"
                err_path.write_text(str(e), encoding="utf-8")
                if not quiet:
                    print(f"[追妻流生成器] 第{idx}章: 概要生成失败", flush=True)
                raise

        summary_path = summaries_dir / f"summary_{idx:02d}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        
        prev_summary_lines = summary_text.splitlines() if summary_text else []
        
        # 更新故事状态
        story_manager.add_chapter_summary(idx, prev_summary_lines)
        
        # 根据章节更新情感状态
        if idx == 3:
            story_manager.update_character_emotion("男主", "开始感到空虚")
            story_manager.update_character_emotion("女主", "努力重新开始")
            character_manager.character_states["陆景深"].emotional_state = "空虚，开始怀疑自己"
            character_manager.character_states["苏念"].emotional_state = "表面坚强，内心痛苦"
        elif idx == 6:
            story_manager.update_emotion_stage("主线", "觉醒期", "男主开始意识到错误")
            character_manager.character_states["陆景深"].knowledge.add("沈雨薇在说谎")
        elif idx == 9:
            story_manager.update_character_emotion("男主", "悔恨交加，疯狂追妻")
            story_manager.update_emotion_stage("主线", "追求期", "男主开始追回女主")
            character_manager.character_states["陆景深"].emotional_state = "崩溃，不顾一切"
            character_manager.character_states["陆景深"].current_goal = "不惜一切代价挽回苏念"
        elif idx == 12:
            story_manager.update_character_emotion("女主", "心防松动，内心挣扎")
            character_manager.character_states["苏念"].emotional_state = "动摇，想原谅但害怕"
        elif idx == 15:
            story_manager.update_emotion_stage("主线", "圆满期", "历经考验，终成眷属")
            character_manager.character_states["陆景深"].emotional_state = "珍惜，深情"
            character_manager.character_states["苏念"].emotional_state = "幸福，安心"
        
        # 保存所有状态
        story_manager.save_state(idx)
        character_manager.save_state(idx)
        
        # 章节间等待
        if not dry_run and idx < chapters:
            if not quiet:
                print(f"[追妻流生成器] 第{idx}章完成, 等待{wait_seconds}秒...", flush=True)
            time.sleep(wait_seconds)

        if not quiet:
            print(f"[追妻流生成器] ——— 第{idx}章 结束 ———", flush=True)

    # 合并全书
    merged_path = paths["outputs"] / "追妻流_全文.md"
    with merged_path.open("w", encoding="utf-8") as f:
        f.write("# 追妻火葬场\n\n")
        f.write("## 简介\n")
        f.write("一段从误会到分离，从悔恨到追回的虐恋情深。\n")
        f.write("当真相大白，他才知道自己错得有多离谱。\n")
        f.write("这一次，换他来守护这份爱情。\n\n")
        
        for idx in range(1, chapters + 1):
            chapter_files = list(chapters_dir.glob(f"第{idx}章*.md"))
            if chapter_files:
                chapter_file = chapter_files[0]
                part = chapter_file.read_text(encoding="utf-8")
                f.write(f"## {chapter_file.stem}\n\n")
                f.write(part)
                f.write("\n\n---\n\n")
    
    if not quiet:
        print(f"[追妻流生成器] 全书合并完成 → {merged_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="追妻流虐恋小说自动生成器")
    parser.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--model", default="ernie-x1-turbo-32k")
    parser.add_argument("--chapters", type=int, default=15, help="默认15章完整剧情")
    parser.add_argument("--temperature", type=float, default=0.75, help="更稳的情感叙事")
    parser.add_argument("--top-p", type=float, default=0.85)
    parser.add_argument("--max-tokens", type=int, default=4600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start-chapter", type=int, default=1)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=60)
    
    args = parser.parse_args()
    base_dir = Path(args.base_dir)
    
    run_romance_generation(
        model=args.model,
        base_dir=base_dir,
        chapters=args.chapters,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        dry_run=args.dry_run,
        start_chapter=args.start_chapter,
        quiet=args.quiet,
        wait_seconds=args.wait_seconds,
    )


if __name__ == "__main__":
    main()