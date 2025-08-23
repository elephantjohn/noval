#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 text_censor_batch.py 的“审核失败→只改命中词句子→复审直至通过”方案
封装为可供 run_romance_novel.py 直接调用的集成模块。

用法（被动集成）：
  from romance_censor_integration import censor_and_repair_chapter
  ok, out_path = censor_and_repair_chapter(Path(path_to_chapter), inplace=True)

命令行（主动批量）：
  python3 -m romance_censor_integration --dir /path/to/outputs_romance/chapters
  python3 -m romance_censor_integration --file /path/to/one.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime
import json
import re

from text_censor_batch import (
    BaiduTextCensor,
    load_env_file,
    read_text_file,
    analyze_censor_result,
    extract_hit_words,
    auto_repair_text,
)
try:
    from novel_runner.client import BaiduErnieClient  # type: ignore
except Exception:  # noqa: BLE001
    BaiduErnieClient = None  # type: ignore


def _prepare_clients() -> Tuple[BaiduTextCensor, Optional["BaiduErnieClient"]]:
    env = load_env_file(Path('.env'))
    text_ak = env.get('TEXT_API_KEY') or os.getenv('TEXT_API_KEY')
    text_sk = env.get('TEXT_SECRET_KEY') or os.getenv('TEXT_SECRET_KEY')
    if not text_ak or not text_sk:
        raise RuntimeError('缺少 TEXT_API_KEY / TEXT_SECRET_KEY')
    censor = BaiduTextCensor(text_ak, text_sk)
    llm = None
    if BaiduErnieClient is not None and (env.get('BAIDU_API_KEY') or os.getenv('BAIDU_API_KEY')):
        llm = BaiduErnieClient()
    return censor, llm


def censor_and_repair_chapter(
    file_path: Path,
    *,
    inplace: bool = True,
    model: str = 'ernie-4.5-turbo-128k',
    max_rounds: int = 10,
    audit_log_path: Optional[Path] = None,
) -> Tuple[bool, Path]:
    """
    对单章执行：审核 → 如不合规仅改命中词所在句子 → 复审，直至通过或达上限。
    返回 (是否合规, 最终文件路径)。
    """
    censor, llm = _prepare_clients()
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    original = read_text_file(file_path)

    # 标题提取与命名辅助
    chapter_no, title = _infer_chapter_meta(file_path, original)
    fail_suffix = "_审核失败"
    base_stem = f"{chapter_no}-{title}" if chapter_no else (file_path.stem)
    sanitized_stem = _sanitize_filename(base_stem)
    failed_name = f"{sanitized_stem}{fail_suffix}{file_path.suffix}"
    final_name = f"{sanitized_stem}{file_path.suffix}"

    current = original
    out_path: Optional[Path] = None
    for round_idx in range(max_rounds + 1):
        result = censor.censor_text(current)
        ok, detail = analyze_censor_result(result)
        if ok:
            # 写回
            if out_path is None:
                # 成功时命名应为 “第X章-标题.md”，若当前文件名包含“审核失败/修复_round”等，统一收敛
                target = file_path.with_name(final_name)
                out_path = target
            out_path.write_text(current, encoding='utf-8')
            # 若存在失败记录, 写入修复完成日志
            _append_audit_log(audit_log_path, {
                "timestamp": _now(),
                "status": "compliant",
                "chapter_no": chapter_no,
                "title": title,
                "old_filename": str(file_path.name),
                "final_filename": str(out_path.name),
                "rounds": round_idx,
            })
            return True, out_path
        # 需要修复
        if llm is None or round_idx >= max_rounds:
            # 无法修复或超限
            if out_path is None:
                # 首次失败时重命名为“第X章-标题_审核失败.md”
                fail_target = file_path.with_name(failed_name)
                try:
                    if file_path.name != fail_target.name:
                        file_path.rename(fail_target)
                        file_path = fail_target
                except Exception:
                    pass
                out_path = file_path
            _append_audit_log(audit_log_path, {
                "timestamp": _now(),
                "status": "non_compliant",
                "chapter_no": chapter_no,
                "title": title,
                "hit_words": _safe_extract_hits(detail),
                "old_filename": str(file_path.name),
                "final_filename": str(out_path.name),
                "rounds": round_idx,
            })
            return False, out_path
        hits = extract_hit_words(detail)
        # 首次失败时，立即重命名标记“审核失败”
        if round_idx == 0:
            fail_target = file_path.with_name(failed_name)
            try:
                if file_path.name != fail_target.name:
                    file_path.rename(fail_target)
                    file_path = fail_target
            except Exception:
                pass
        # 写入失败日志（中间轮次）
        _append_audit_log(audit_log_path, {
            "timestamp": _now(),
            "status": "fix_round",
            "chapter_no": chapter_no,
            "title": title,
            "hit_words": hits,
            "old_filename": str(file_path.name),
            "round": round_idx + 1,
        })
        current = auto_repair_text(
            repair_client=llm,
            model=model,
            original_text=current,
            violation_hint=detail,
            hit_words=hits,
        )
        # 保存中间轮次
        tmp = file_path.with_name(f"{file_path.stem}_修复_round{round_idx+1}{file_path.suffix}")
        tmp.write_text(current, encoding='utf-8')
        out_path = tmp

    return False, out_path or file_path


def _sanitize_filename(name: str) -> str:
    # 去除非法与多余空白
    name = re.sub(r"[\\/:*?\"<>|]", "", name)
    return name.strip().replace(" ", "")


def _infer_chapter_meta(file_path: Path, content: str) -> Tuple[str, str]:
    """推断章节号与标题。优先文件名中的“第X章-标题”，否则从正文首行抓取。"""
    m = re.match(r"^(第\d+章)[-_—]*(.+)?\.md$", file_path.name)
    if m:
        chapter_no = m.group(1)
        title = (m.group(2) or "无题").replace("_审核失败", "").replace("_修复", "")
        return chapter_no, title
    # 退化：正文首行作为标题尝试
    first_line = (content.splitlines() or ["无题"])[0].strip()
    # 简化为最多12字
    title = first_line[:12] if first_line else "无题"
    # 尝试从文件夹顺序中获取“第X章”，否则空
    m2 = re.match(r"^(第\d+章)", file_path.stem)
    chapter_no = m2.group(1) if m2 else ""
    if not chapter_no:
        # 最后保底
        chapter_no = "第1章"
    return chapter_no, title or "无题"


def _append_audit_log(audit_log_path: Optional[Path], record: Dict[str, Any]) -> None:
    if audit_log_path is None:
        # 默认日志位置：outputs_romance/audit/censor_failures.jsonl
        base = Path(__file__).resolve().parent / "outputs_romance" / "audit"
        base.mkdir(parents=True, exist_ok=True)
        audit_log_path = base / "censor_failures.jsonl"
    else:
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _main(argv: list[str]) -> None:
    if not argv or argv[0] in ('-h', '--help'):
        print('用法: python -m romance_censor_integration (--file PATH | --dir DIR) [--no-inplace]')
        return
    inplace = True
    target: Optional[Path] = None
    is_dir = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--file' and i + 1 < len(argv):
            target = Path(argv[i+1]); i += 2
        elif a == '--dir' and i + 1 < len(argv):
            target = Path(argv[i+1]); is_dir = True; i += 2
        elif a == '--no-inplace':
            inplace = False; i += 1
        else:
            i += 1
    if target is None:
        print('缺少 --file 或 --dir'); return
    if is_dir:
        for p in sorted(target.glob('*.md')):
            ok, outp = censor_and_repair_chapter(p, inplace=inplace)
            print(f"[{p.name}] → {'合规' if ok else '未通过'} → {outp}")
    else:
        ok, outp = censor_and_repair_chapter(target, inplace=inplace)
        print(f"[{target.name}] → {'合规' if ok else '未通过'} → {outp}")


if __name__ == '__main__':
    _main(sys.argv[1:])


