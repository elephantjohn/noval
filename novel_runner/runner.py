import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

from .client import BaiduErnieClient
from .templates import build_chapter_messages, build_summary_messages


def ensure_dirs(base_dir: Path) -> Dict[str, Path]:
    outputs = base_dir / "outputs"
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
    # Qianfan responses may vary; try common fields
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
    # Fallback pretty print
    return str(data)


def run_generation(
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

    # Load .env from base dir if present (simple parser)
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

    # Accumulated summary lines to feed into next chapter
    prev_summary_lines: List[str] = []

    if not quiet:
        print(f"[NovelRunner] 开始生成: 模型={model}, 章节数={chapters}, 起始章节={start_chapter}, 干跑={dry_run}", flush=True)

    for idx in range(start_chapter, chapters + 1):
        if not quiet:
            print(f"[NovelRunner] ——— 第{idx}章 开始 ———", flush=True)
            print(f"[NovelRunner] 生成第{idx}章: 构建提示词…", flush=True)
        messages = build_chapter_messages(idx, prev_summary_lines, character_notes=None)

        # Call model for chapter text
        if dry_run:
            chapter_text = (
                f"【干跑模式】第{idx}章正文占位。该模式不调用接口, 仅用于验证流程与提示词。\n\n"
                f"提示词示例:\n{messages[-1]['content']}"
            )
        else:
            try:
                if not quiet:
                    print(f"[NovelRunner] 第{idx}章: 请求大模型…", flush=True)
                data = client.chat_completions(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                chapter_text = extract_text_from_response(data)
                # Persist raw response for审计
                (logs_dir / f"chapter_{idx:02d}.response.json").write_text(
                    str(data), encoding="utf-8"
                )
            except Exception as e:  # noqa: BLE001
                err_path = logs_dir / f"chapter_{idx:02d}.error.txt"
                err_path.write_text(str(e), encoding="utf-8")
                if not quiet:
                    print(f"[NovelRunner] 第{idx}章: 失败 → {err_path}", flush=True)
                raise

        # Save chapter text
        chapter_path = chapters_dir / f"chapter_{idx:02d}.md"
        chapter_path.write_text(chapter_text, encoding="utf-8")
        if not quiet:
            print(f"[NovelRunner] 第{idx}章: 正文已写入 → {chapter_path}", flush=True)

        # Summarize for next chapter prompt
        if dry_run:
            summary_text = "干跑模式: 以八到十二条二三十字要点代替。"
        else:
            try:
                if not quiet:
                    print(f"[NovelRunner] 第{idx}章: 生成前情提要…", flush=True)
                sum_messages = build_summary_messages(chapter_text)
                sum_data = client.chat_completions(
                    model=model,
                    messages=sum_messages,
                    temperature=0.6,
                    top_p=0.85,
                    max_tokens=800,
                )
                summary_text = extract_text_from_response(sum_data)
                (logs_dir / f"summary_{idx:02d}.response.json").write_text(
                    str(sum_data), encoding="utf-8"
                )
            except Exception as e:  # noqa: BLE001
                err_path = logs_dir / f"summary_{idx:02d}.error.txt"
                err_path.write_text(str(e), encoding="utf-8")
                if not quiet:
                    print(f"[NovelRunner] 第{idx}章: 提要失败 → {err_path}", flush=True)
                raise

        # Persist summary text
        summary_path = summaries_dir / f"summary_{idx:02d}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        if not quiet:
            print(f"[NovelRunner] 第{idx}章: 提要已写入 → {summary_path}", flush=True)

        # Update prev_summary_lines for next round
        prev_summary_lines = [
            line.strip(" \t\r\n-•*0123456789.")
            for line in summary_text.splitlines()
            if line.strip()
        ]

        # Per-chapter visible countdown to respect TPM, only for real calls
        if not dry_run and idx < chapters:
            if not quiet:
                print(f"[NovelRunner] 第{idx}章完成, 进入节流等待 {wait_seconds} 秒…", flush=True)
            for remain in range(wait_seconds, 0, -1):
                if not quiet:
                    print(f"[NovelRunner] 下一章倒计时: {remain} 秒", flush=True)
                time.sleep(1)
            if not quiet:
                print(f"[NovelRunner] 倒计时结束, 准备开始第{idx+1}章。", flush=True)

        if not quiet:
            print(f"[NovelRunner] ——— 第{idx}章 结束 ———", flush=True)

    # Merge all chapters
    merged_path = paths["outputs"] / "novel_full.md"
    with merged_path.open("w", encoding="utf-8") as f:
        for idx in range(1, chapters + 1):
            part = (chapters_dir / f"chapter_{idx:02d}.md").read_text(encoding="utf-8")
            f.write(part)
            f.write("\n\n")
    if not quiet:
        print(f"[NovelRunner] 全书合并完成 → {merged_path}", flush=True)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ERNIE X1 Turbo 32K 小说九章自动生成器")
    parser.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--model", default="ernie-x1-turbo-32k")
    parser.add_argument("--chapters", type=int, default=9)
    parser.add_argument("--temperature", type=float, default=0.85)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=4600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start-chapter", type=int, default=1)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=60)
    return parser.parse_args(argv)


def main(argv: List[str]) -> None:
    args = parse_args(argv)
    base_dir = Path(args.base_dir)
    run_generation(
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
    main(sys.argv[1:])


