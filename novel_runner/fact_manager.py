"""
轻量事实管理器:
- 从章节正文里抽取人物事实与关键事件
- 与已有事实库对比, 发现矛盾
- 必要时请求大模型对章节做一致性微调

注意: 这里做弱一致性约束, 只尝试一次自动修订; 若仍冲突, 记录日志供人工处理。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _safe_load(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


class FactManager:
    def __init__(self, state_file: Path, client, model: str = "ernie-x1-turbo-32k") -> None:
        self.state_file = state_file
        self.client = client
        self.model = model
        self.state: Dict[str, Any] = _safe_load(state_file)
        if "characters" not in self.state:
            self.state["characters"] = {}
        if "events" not in self.state:
            self.state["events"] = []

    # -------- 抽取 / 检测 / 合并 --------
    def extract_facts(self, chapter_text: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": "你是严谨的小说事实抽取器, 只输出JSON。"},
            {
                "role": "user",
                "content": (
                    "请从以下正文抽取稳定事实, 输出JSON, 键包括: characters(人物词典), events(关键事件数组)。\n"
                    "characters 的结构: {姓名: {年龄?:str, 职业?:str, 关系?:str, 其他?:str}};\n"
                    "events: 每项二十字以内的关键事件或设定。\n"
                    "正文:\n" + chapter_text
                ),
            },
        ]
        data = self.client.chat_completions(
            model=self.model,
            messages=messages,
            temperature=0.3,
            top_p=0.85,
            max_tokens=1200,
        )
        try:
            # 兼容多种返回
            import json as _json

            if isinstance(data, dict) and "result" in data and isinstance(data["result"], str):
                return _json.loads(data["result"])  # type: ignore
            if isinstance(data, dict) and "choices" in data:
                text = data["choices"][0].get("message", {}).get("content")
                return _json.loads(text)
        except Exception:
            return {"characters": {}, "events": []}
        return {"characters": {}, "events": []}

    def detect_conflicts(self, new_facts: Dict[str, Any]) -> List[str]:
        conflicts: List[str] = []
        old_chars: Dict[str, Any] = self.state.get("characters", {})
        for name, attrs in new_facts.get("characters", {}).items():
            if name in old_chars:
                for k, v in attrs.items():
                    ov = old_chars[name].get(k)
                    if ov and v and str(ov) != str(v):
                        conflicts.append(f"人物[{name}] 字段[{k}] 不一致: 旧={ov} 新={v}")
        # 事件简单去重对比
        old_events = set(self.state.get("events", []))
        for ev in new_facts.get("events", []):
            if isinstance(ev, str) and len(ev) > 0 and ev not in old_events:
                # 不算冲突, 只是新增
                pass
        return conflicts

    def merge_facts(self, new_facts: Dict[str, Any]) -> None:
        chars = self.state.setdefault("characters", {})
        for name, attrs in new_facts.get("characters", {}).items():
            dst = chars.setdefault(name, {})
            for k, v in attrs.items():
                if v and not dst.get(k):
                    dst[k] = v
        # 事件追加去重
        events: List[str] = self.state.setdefault("events", [])
        for ev in new_facts.get("events", []):
            if isinstance(ev, str) and len(ev) > 0 and ev not in events:
                events.append(ev)

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    # -------- 执行管线 --------
    def process_chapter(self, chapter_index: int, chapter_text: str, logs_dir: Path) -> Tuple[str, List[str]]:
        facts = self.extract_facts(chapter_text)
        conflicts = self.detect_conflicts(facts)
        (logs_dir / f"facts_{chapter_index:02d}.json").write_text(
            json.dumps({"extracted": facts, "conflicts": conflicts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not conflicts:
            self.merge_facts(facts)
            self.save()
            return chapter_text, []

        # 存在冲突: 尝试一次一致性修订
        fix_messages = [
            {"role": "system", "content": "你是小说一致性编辑, 只输出修订后正文。"},
            {
                "role": "user",
                "content": (
                    "【既有事实库】\n" + json.dumps(self.state, ensure_ascii=False) +
                    "\n\n【检测到的冲突】\n" + "\n".join(conflicts) +
                    "\n\n请在严格不改变故事关键事件顺序与情感走向的前提下, 对正文进行最小幅度修订, 确保与事实库一致。\n"
                    "不要扩写或删减段落, 仅在冲突处做替换。只输出修订后的正文。\n\n"
                    "【待修订正文】\n" + chapter_text
                ),
            },
        ]
        data = self.client.chat_completions(
            model=self.model,
            messages=fix_messages,
            temperature=0.4,
            top_p=0.85,
            max_tokens=4600,
        )
        try:
            if isinstance(data, dict) and "result" in data and isinstance(data["result"], str):
                fixed = data["result"]
            elif isinstance(data, dict) and "choices" in data:
                fixed = data["choices"][0].get("message", {}).get("content", chapter_text)
            else:
                fixed = chapter_text
        except Exception:
            fixed = chapter_text

        # 再抽取/合并
        facts2 = self.extract_facts(fixed)
        conflicts2 = self.detect_conflicts(facts2)
        (logs_dir / f"facts_{chapter_index:02d}_fixed.json").write_text(
            json.dumps({"extracted": facts2, "conflicts": conflicts2}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not conflicts2:
            self.merge_facts(facts2)
            self.save()
        return fixed, conflicts2


