"""
故事管理器 - 管理人物档案、剧情线索和世界观设定
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class Character:
    """人物档案"""
    name: str
    role: str  # 主角/配角/反派
    personality: List[str] = field(default_factory=list)  # 性格特征
    abilities: List[str] = field(default_factory=list)  # 能力/技能
    relationships: Dict[str, str] = field(default_factory=dict)  # 与其他角色的关系
    arc: str = ""  # 人物成长弧线
    current_state: str = ""  # 当前状态/心境
    key_items: List[str] = field(default_factory=list)  # 重要物品
    
    def to_prompt_text(self) -> str:
        """转换为提示词文本"""
        lines = [f"{self.name}（{self.role}）："]
        if self.personality:
            lines.append(f"  性格：{'、'.join(self.personality)}")
        if self.abilities:
            lines.append(f"  能力：{'、'.join(self.abilities)}")
        if self.relationships:
            rel_text = '；'.join([f"与{k}{v}" for k, v in self.relationships.items()])
            lines.append(f"  关系：{rel_text}")
        if self.arc:
            lines.append(f"  成长线：{self.arc}")
        if self.current_state:
            lines.append(f"  当前：{self.current_state}")
        if self.key_items:
            lines.append(f"  物品：{'、'.join(self.key_items)}")
        return '\n'.join(lines)


@dataclass
class PlotThread:
    """剧情线索"""
    name: str
    description: str
    status: str = "进行中"  # 进行中/已解决/搁置
    key_events: List[str] = field(default_factory=list)
    related_characters: List[str] = field(default_factory=list)
    
    def to_prompt_text(self) -> str:
        """转换为提示词文本"""
        lines = [f"【{self.name}】（{self.status}）：{self.description}"]
        if self.key_events:
            lines.append(f"  关键事件：{'→'.join(self.key_events[-3:])}")  # 只保留最近3个
        return '\n'.join(lines)


@dataclass 
class WorldDetail:
    """世界观细节"""
    category: str  # 地理/势力/法术体系/历史等
    name: str
    description: str
    importance: int = 1  # 1-5 重要度
    
    def to_prompt_text(self) -> str:
        return f"[{self.category}] {self.name}：{self.description}"


class StoryManager:
    """故事状态管理器"""
    
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # 核心数据结构
        self.characters: Dict[str, Character] = {}
        self.plot_threads: Dict[str, PlotThread] = {}
        self.world_details: List[WorldDetail] = []
        self.chapter_summaries: Dict[int, List[str]] = {}  # 章节号 -> 概要列表
        
        # 初始化基础设定
        self._init_base_settings()
        
    def _init_base_settings(self):
        """初始化基础人物和设定"""
        # 主角设定
        self.characters["主角"] = Character(
            name="待定",
            role="主角",
            personality=["坚韧", "善良", "有理想"],
            abilities=["穿越者记忆", "潜在天赋未觉醒"],
            arc="从凡人到英雄的成长之路",
            current_state="初入异世"
        )
        
        # 核心剧情线
        self.plot_threads["主线"] = PlotThread(
            name="天地大劫",
            description="千年一遇的天地大劫即将来临，需要集合众人之力方能化解",
            key_events=["血触古卷现世", "天机预言显现"]
        )
        
        # 世界观要素
        self.world_details.extend([
            WorldDetail("修行体系", "心性为本", "修行以心性为根本，气脉星象为辅助", 5),
            WorldDetail("地理", "中原王朝", "架空的中原王朝，山海奇观与礼乐法度并立", 4),
            WorldDetail("势力", "仙门与朝廷", "修行门派与世俗朝廷相互制衡", 4),
        ])
    
    def update_character(self, name: str, updates: Dict[str, Any]):
        """更新人物信息"""
        if name not in self.characters:
            self.characters[name] = Character(name=name, role="配角")
        
        char = self.characters[name]
        for key, value in updates.items():
            if hasattr(char, key):
                if isinstance(getattr(char, key), list):
                    current = getattr(char, key)
                    if isinstance(value, list):
                        current.extend(value)
                    else:
                        current.append(value)
                elif isinstance(getattr(char, key), dict):
                    getattr(char, key).update(value)
                else:
                    setattr(char, key, value)
    
    def add_plot_thread(self, name: str, description: str, **kwargs):
        """添加新的剧情线索"""
        self.plot_threads[name] = PlotThread(name=name, description=description, **kwargs)
    
    def update_plot_thread(self, name: str, event: str = None, status: str = None):
        """更新剧情线索"""
        if name in self.plot_threads:
            thread = self.plot_threads[name]
            if event:
                thread.key_events.append(event)
            if status:
                thread.status = status
    
    def add_world_detail(self, category: str, name: str, description: str, importance: int = 1):
        """添加世界观细节"""
        self.world_details.append(
            WorldDetail(category, name, description, importance)
        )
    
    def add_chapter_summary(self, chapter: int, summary_lines: List[str]):
        """添加章节概要"""
        self.chapter_summaries[chapter] = summary_lines
    
    def get_context_for_chapter(self, chapter: int, window_size: int = 3) -> Dict[str, Any]:
        """获取指定章节的上下文信息"""
        context = {
            "characters": {},
            "plot_threads": {},
            "world_details": [],
            "recent_summaries": []
        }
        
        # 获取主要人物（主角和重要配角）
        for name, char in self.characters.items():
            if char.role in ["主角", "重要配角"] or char.current_state:
                context["characters"][name] = char.to_prompt_text()
        
        # 获取活跃的剧情线索
        for name, thread in self.plot_threads.items():
            if thread.status != "已解决":
                context["plot_threads"][name] = thread.to_prompt_text()
        
        # 获取重要的世界观细节
        important_details = sorted(self.world_details, key=lambda x: x.importance, reverse=True)[:5]
        context["world_details"] = [d.to_prompt_text() for d in important_details]
        
        # 获取最近几章的概要（滑动窗口）
        start_chapter = max(1, chapter - window_size)
        for ch in range(start_chapter, chapter):
            if ch in self.chapter_summaries:
                context["recent_summaries"].extend([
                    f"第{ch}章：{line}" for line in self.chapter_summaries[ch][-5:]  # 每章保留5条关键
                ])
        
        return context
    
    def save_state(self, chapter: int):
        """保存当前状态到文件"""
        state_file = self.save_dir / f"story_state_ch{chapter:02d}.json"
        state = {
            "chapter": chapter,
            "characters": {
                name: {
                    "name": char.name,
                    "role": char.role,
                    "personality": char.personality,
                    "abilities": char.abilities,
                    "relationships": char.relationships,
                    "arc": char.arc,
                    "current_state": char.current_state,
                    "key_items": char.key_items
                }
                for name, char in self.characters.items()
            },
            "plot_threads": {
                name: {
                    "name": thread.name,
                    "description": thread.description,
                    "status": thread.status,
                    "key_events": thread.key_events,
                    "related_characters": thread.related_characters
                }
                for name, thread in self.plot_threads.items()
            },
            "world_details": [
                {
                    "category": d.category,
                    "name": d.name,
                    "description": d.description,
                    "importance": d.importance
                }
                for d in self.world_details
            ],
            "chapter_summaries": self.chapter_summaries
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def load_state(self, chapter: int) -> bool:
        """从文件加载状态"""
        state_file = self.save_dir / f"story_state_ch{chapter:02d}.json"
        if not state_file.exists():
            return False
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # 恢复人物
        self.characters = {}
        for name, char_data in state.get("characters", {}).items():
            self.characters[name] = Character(**char_data)
        
        # 恢复剧情线索
        self.plot_threads = {}
        for name, thread_data in state.get("plot_threads", {}).items():
            self.plot_threads[name] = PlotThread(**thread_data)
        
        # 恢复世界观细节
        self.world_details = [
            WorldDetail(**d) for d in state.get("world_details", [])
        ]
        
        # 恢复章节概要
        self.chapter_summaries = {
            int(k): v for k, v in state.get("chapter_summaries", {}).items()
        }
        
        return True
    
    def analyze_chapter_for_updates(self, chapter_text: str, chapter_num: int) -> Dict[str, List[str]]:
        """分析章节文本，提取需要更新的信息（简单规则）"""
        updates = {
            "new_characters": [],
            "new_locations": [],
            "new_items": [],
            "plot_events": []
        }
        
        # 这里可以后续接入NLP或LLM来智能提取
        # 目前使用简单的规则匹配
        
        lines = chapter_text.split('\n')
        for line in lines:
            # 检测可能的人名（简单示例）
            if "结识" in line or "遇见" in line or "认识" in line:
                updates["new_characters"].append(line[:50])
            
            # 检测地点
            if "来到" in line or "抵达" in line or "前往" in line:
                updates["new_locations"].append(line[:50])
            
            # 检测物品
            if "得到" in line or "获得" in line or "发现" in line:
                updates["new_items"].append(line[:50])
        
        return updates