#!/usr/bin/env python3
"""
追妻流小说快速启动脚本
1) 调用生成器产出章节
2) 自动执行文本审核 → 命中词句子最小改写 → 复审直至通过
   （复用 romance_censor_integration 的内置逻辑，无需额外参数）
"""
import sys
from pathlib import Path
from novel_runner.runner_romance import main

try:
    from romance_censor_integration import censor_and_repair_chapter
except Exception:
    censor_and_repair_chapter = None  # type: ignore


def _auto_censor_after_generation() -> None:
    # 自动审核与修复 outputs_romance/chapters 下的所有 md 文件
    base = Path(__file__).resolve().parent / "outputs_romance" / "chapters"
    if not base.exists():
        return
    if censor_and_repair_chapter is None:
        print("[审核] 跳过：未找到审核修复模块。")
        return
    print("\n[审核] 开始批量合规检测与自动修复…")
    count = 0
    for p in sorted(base.glob("*.md")):
        ok, outp = censor_and_repair_chapter(p, inplace=True)
        print(f"[审核] {p.name} → {'合规' if ok else '未通过'} → {outp}")
        count += 1
    if count == 0:
        print("[审核] 未发现可检测的章节文件。")


if __name__ == "__main__":
    print("=" * 60)
    print("追妻火葬场 - 虐恋情深小说生成器")
    print("=" * 60)
    print("\n剧情主线：")
    print("第1-3章：【虐心离别】误会重重，痛苦分离")
    print("第4-6章：【各自煎熬】分离后的思念与痛苦")
    print("第7-9章：【真相渐明】误会解开，男主悔恨")
    print("第10-12章：【追妻之路】男主追求，女主动摇")
    print("第13-15章：【破镜重圆】历经考验，重新相爱")
    print("\n开始生成...\n")

    # 运行主流程
    main()