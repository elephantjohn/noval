#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面向业务复用的文本审核与自动修复服务类。

功能：
- 审核单个文件，打印可读进度
- 审核不通过时，调用大模型（默认 ernie-4.5-turbo-128k）进行合规化重写
- 支持就地覆盖或输出到副本
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional

from text_censor_batch import (
    BaiduTextCensor,
    analyze_censor_result,
    auto_repair_text,
)
from novel_runner.client import BaiduErnieClient


class TextCensorAndRepairService:
    """文本审核+自动修复一体化服务。

    参数：
      - text_api_key/text_secret_key: 文本审核所需的 AK/SK
      - llm_api_key: 大模型调用所用的密钥（不传则读取 BAIDU_API_KEY）
      - llm_model: 修复使用的模型，默认 'ernie-4.5-turbo-128k'
      - verbose: 是否打印过程信息
    """

    def __init__(
        self,
        text_api_key: str,
        text_secret_key: str,
        llm_api_key: Optional[str] = None,
        llm_model: str = "ernie-4.5-turbo-128k",
        verbose: bool = True,
    ) -> None:
        self.verbose = verbose
        self.censor_client = BaiduTextCensor(text_api_key, text_secret_key)
        self.repair_model = llm_model

        # 允许外部通过 env 提供 BAIDU_API_KEY
        api_key = llm_api_key or os.getenv("BAIDU_API_KEY", "")
        self.repair_client: Optional[BaiduErnieClient]
        if api_key:
            self.repair_client = BaiduErnieClient(api_key=api_key)
        else:
            self.repair_client = None

    def _print(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)

    def censor_file(self, file_path: Path) -> Dict[str, Any]:
        """仅执行审核，返回原始结果与解析后的结论。"""
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"文件不存在或不可读: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        self._print(f"[FILE] 审核文件: {file_path.name}")
        self._print(f"  📄 文件大小: {len(content)} 字符")
        result = self.censor_client.censor_text(content)
        is_ok, detail = analyze_censor_result(result)
        return {
            "ok": is_ok,
            "detail": detail,
            "raw": result,
            "content": content,
        }

    def repair(self, original_text: str, violation_hint: str) -> str:
        """调用大模型修复文本。"""
        if self.repair_client is None:
            raise RuntimeError("未配置 BAIDU_API_KEY，无法执行自动修复")
        return auto_repair_text(
            repair_client=self.repair_client,
            model=self.repair_model,
            original_text=original_text,
            violation_hint=violation_hint,
        )

    def process_file(self, file_path: Path, inplace: bool = True) -> Dict[str, Any]:
        """审核并在必要时修复，返回最终状态。"""
        info = self.censor_file(file_path)
        if info["ok"]:
            self._print(f"  ✅ {info['detail']}")
            return {"status": "compliant", "path": str(file_path), "detail": info["detail"]}

        # 审核不通过，尝试修复
        self._print("  ❌ 审核不通过，准备自动修复…")
        self._print("     " + info["detail"].replace("\n", "\n     "))
        fixed_text = self.repair(info["content"], info["detail"])

        if inplace:
            file_path.write_text(fixed_text, encoding="utf-8")
            saved_path = file_path
        else:
            saved_path = file_path.with_suffix(file_path.suffix.replace(".md", "") + "_修复.md")
            saved_path.write_text(fixed_text, encoding="utf-8")

        self._print(f"  ✅ 修复完成 → {saved_path}")
        return {
            "status": "fixed",
            "path": str(saved_path),
            "detail": info["detail"],
        }


__all__ = ["TextCensorAndRepairService"]


