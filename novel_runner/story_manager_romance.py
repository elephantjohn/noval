"""
追妻流小说故事管理器
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class RomanceCharacter:
    """追妻流人物档案"""
    name: str
    role: str  # 男主/女主/男配/女配/家人
    age: int
    occupation: str  # 职业
    personality: List[str] = field(default_factory=list)
    background: str = ""  # 背景故事
    relationships: Dict[str, str] = field(default_factory=dict)
    emotional_state: str = ""  # 当前情感状态
    secrets: List[str] = field(default_factory=list)  # 隐藏的秘密
    growth: str = ""  # 成长变化
    
    def to_prompt_text(self) -> str:
        """转换为提示词文本"""
        lines = [f"{self.name}（{self.role}，{self.age}岁，{self.occupation}）："]
        if self.personality:
            lines.append(f"  性格：{'、'.join(self.personality)}")
        if self.background:
            lines.append(f"  背景：{self.background}")
        if self.relationships:
            rel_text = '；'.join([f"与{k}{v}" for k, v in self.relationships.items()])
            lines.append(f"  关系：{rel_text}")
        if self.emotional_state:
            lines.append(f"  情感状态：{self.emotional_state}")
        if self.secrets:
            lines.append(f"  秘密：{'、'.join(self.secrets)}")
        if self.growth:
            lines.append(f"  成长：{self.growth}")
        return '\n'.join(lines)


@dataclass
class EmotionThread:
    """情感线索"""
    name: str
    stage: str  # 当前阶段
    description: str
    key_events: List[str] = field(default_factory=list)
    tension_level: int = 5  # 1-10 紧张程度
    
    def to_prompt_text(self) -> str:
        lines = [f"【{self.name}】{self.stage}（强度:{self.tension_level}/10）"]
        lines.append(f"  {self.description}")
        if self.key_events:
            recent = self.key_events[-3:] if len(self.key_events) > 3 else self.key_events
            lines.append(f"  关键事件：{'→'.join(recent)}")
        return '\n'.join(lines)


class RomanceStoryManager:
    """追妻流故事管理器"""
    
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.characters: Dict[str, RomanceCharacter] = {}
        self.emotion_threads: Dict[str, EmotionThread] = {}
        self.chapter_summaries: Dict[int, List[str]] = {}
        self.emotion_arc: List[str] = []  # 情感曲线记录
        
        # 初始化基础设定
        self._init_base_settings()
    
    def _init_base_settings(self):
        """初始化追妻流基础设定"""
        
        # 男主设定
        self.characters["男主"] = RomanceCharacter(
            name="陆景深",
            role="男主",
            age=32,
            occupation="跨国集团总裁",
            personality=["冷漠", "霸道", "占有欲强", "后期深情"],
            background="豪门继承人，年少成名，商界传奇",
            emotional_state="初期：自负傲慢；后期：悔恨追妻",
            secrets=["其实一直深爱女主", "被人设计陷害"]
        )
        
        # 女主设定
        self.characters["女主"] = RomanceCharacter(
            name="苏念",
            role="女主",
            age=28,
            occupation="独立设计师",
            personality=["坚强", "善良", "倔强", "重感情"],
            background="普通家庭，靠自己打拼，曾为爱付出一切",
            emotional_state="初期：心死绝望；后期：慢慢心软",
            secrets=["怀有身孕", "患有疾病", "另有身世"]
        )
        
        # 男配设定
        self.characters["男配"] = RomanceCharacter(
            name="顾北辰",
            role="男配",
            age=30,
            occupation="医生/律师",
            personality=["温柔", "体贴", "默默守护"],
            background="女主的朋友，一直暗恋女主",
            relationships={"苏念": "暗恋守护"},
            emotional_state="愿意等待，但会适时退出"
        )
        
        # 女配设定（白月光）
        self.characters["女配"] = RomanceCharacter(
            name="沈雨薇",
            role="女配",
            age=29,
            occupation="明星/千金",
            personality=["心机", "表面柔弱", "善于伪装"],
            background="男主的初恋/青梅竹马",
            relationships={"陆景深": "前女友/白月光"},
            emotional_state="想要夺回男主"
        )
        
        # 主要情感线
        self.emotion_threads["主线"] = EmotionThread(
            name="男女主情感",
            stage="破裂期",
            description="从深爱到误会，从分离到追回",
            key_events=["相爱结婚", "误会产生", "痛苦分离"],
            tension_level=8
        )
        
        # 辅助情感线
        self.emotion_threads["男配线"] = EmotionThread(
            name="男配守护",
            stage="陪伴期",
            description="男配默默守护女主，成为对比",
            tension_level=4
        )
        
        self.emotion_threads["反派线"] = EmotionThread(
            name="白月光搅局",
            stage="挑拨期",
            description="女配不断制造误会和麻烦",
            tension_level=6
        )
    
    def update_character_emotion(self, name: str, new_state: str, growth: str = None):
        """更新人物情感状态"""
        if name in self.characters:
            self.characters[name].emotional_state = new_state
            if growth:
                self.characters[name].growth = growth
    
    def add_emotion_event(self, thread_name: str, event: str, new_tension: int = None):
        """添加情感事件"""
        if thread_name in self.emotion_threads:
            self.emotion_threads[thread_name].key_events.append(event)
            if new_tension:
                self.emotion_threads[thread_name].tension_level = new_tension
    
    def update_emotion_stage(self, thread_name: str, new_stage: str, description: str = None):
        """更新情感阶段"""
        if thread_name in self.emotion_threads:
            self.emotion_threads[thread_name].stage = new_stage
            if description:
                self.emotion_threads[thread_name].description = description
    
    def get_context_for_chapter(self, chapter: int) -> Dict[str, Any]:
        """获取章节上下文"""
        context = {
            "characters": {},
            "emotion_threads": {},
            "recent_summaries": []
        }
        
        # 获取主要人物状态
        for name, char in self.characters.items():
            if char.role in ["男主", "女主", "男配", "女配"]:
                context["characters"][name] = char.to_prompt_text()
        
        # 获取情感线索
        for name, thread in self.emotion_threads.items():
            context["emotion_threads"][name] = thread.to_prompt_text()
        
        # 获取最近章节概要
        window_size = 3
        start_chapter = max(1, chapter - window_size)
        for ch in range(start_chapter, chapter):
            if ch in self.chapter_summaries:
                for line in self.chapter_summaries[ch][-5:]:
                    context["recent_summaries"].append(f"第{ch}章：{line}")
        
        return context
    
    def add_chapter_summary(self, chapter: int, summary_lines: List[str]):
        """添加章节概要"""
        self.chapter_summaries[chapter] = summary_lines
        
        # 记录情感曲线
        if "心碎" in str(summary_lines):
            self.emotion_arc.append(f"第{chapter}章：虐心")
        elif "甜蜜" in str(summary_lines) or "和好" in str(summary_lines):
            self.emotion_arc.append(f"第{chapter}章：甜蜜")
        else:
            self.emotion_arc.append(f"第{chapter}章：过渡")
    
    def save_state(self, chapter: int):
        """保存状态"""
        state_file = self.save_dir / f"romance_state_ch{chapter:02d}.json"
        state = {
            "chapter": chapter,
            "characters": {
                name: {
                    "name": char.name,
                    "role": char.role,
                    "age": char.age,
                    "occupation": char.occupation,
                    "personality": char.personality,
                    "background": char.background,
                    "relationships": char.relationships,
                    "emotional_state": char.emotional_state,
                    "secrets": char.secrets,
                    "growth": char.growth
                }
                for name, char in self.characters.items()
            },
            "emotion_threads": {
                name: {
                    "name": thread.name,
                    "stage": thread.stage,
                    "description": thread.description,
                    "key_events": thread.key_events,
                    "tension_level": thread.tension_level
                }
                for name, thread in self.emotion_threads.items()
            },
            "chapter_summaries": self.chapter_summaries,
            "emotion_arc": self.emotion_arc
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def load_state(self, chapter: int) -> bool:
        """加载状态"""
        state_file = self.save_dir / f"romance_state_ch{chapter:02d}.json"
        if not state_file.exists():
            return False
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # 恢复人物
        self.characters = {}
        for name, char_data in state.get("characters", {}).items():
            self.characters[name] = RomanceCharacter(**char_data)
        
        # 恢复情感线
        self.emotion_threads = {}
        for name, thread_data in state.get("emotion_threads", {}).items():
            self.emotion_threads[name] = EmotionThread(**thread_data)
        
        self.chapter_summaries = {
            int(k): v for k, v in state.get("chapter_summaries", {}).items()
        }
        self.emotion_arc = state.get("emotion_arc", [])
        
        return True