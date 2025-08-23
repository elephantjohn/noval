"""
人物一致性管理系统 - 确保人物性格、行为、语言风格的连贯性
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class CharacterTraits:
    """人物特征追踪"""
    # 核心性格特征（不变）
    core_personality: List[str] = field(default_factory=list)
    
    # 说话风格
    speech_patterns: Dict[str, str] = field(default_factory=dict)  # 场合->说话方式
    common_phrases: List[str] = field(default_factory=list)  # 口头禅
    tone: str = ""  # 语气特点
    
    # 行为模式
    habits: List[str] = field(default_factory=list)  # 习惯动作
    reactions: Dict[str, str] = field(default_factory=dict)  # 情况->反应方式
    
    # 外貌特征（固定）
    appearance: Dict[str, str] = field(default_factory=dict)
    clothing_style: str = ""
    distinctive_features: List[str] = field(default_factory=list)
    
    # 背景细节（固定）
    family_background: str = ""
    education: str = ""
    past_experiences: List[str] = field(default_factory=list)
    
    # 人际关系细节
    relationship_dynamics: Dict[str, Dict] = field(default_factory=dict)  # 人物->互动模式
    
    # 动机和目标
    core_motivation: str = ""
    fears: List[str] = field(default_factory=list)
    desires: List[str] = field(default_factory=list)


@dataclass
class CharacterState:
    """人物当前状态（会变化）"""
    emotional_state: str = ""
    physical_state: str = ""
    location: str = ""
    current_goal: str = ""
    recent_events: List[str] = field(default_factory=list)
    knowledge: Set[str] = field(default_factory=set)  # 已知信息
    relationships_status: Dict[str, str] = field(default_factory=dict)  # 当前关系状态


class CharacterConsistencyManager:
    """人物一致性管理器"""
    
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # 人物特征库（不变的）
        self.character_traits: Dict[str, CharacterTraits] = {}
        
        # 人物状态库（会变的）
        self.character_states: Dict[str, CharacterState] = {}
        
        # 人物互动历史
        self.interaction_history: List[Dict] = []
        
        # 重要物品和地点
        self.important_items: Dict[str, Dict] = {}
        self.locations: Dict[str, Dict] = {}
        
        self._init_romance_characters()
    
    def _init_romance_characters(self):
        """初始化追妻流人物详细档案"""
        
        # 男主：陆景深
        self.character_traits["陆景深"] = CharacterTraits(
            core_personality=["理性", "控制欲强", "骄傲", "内心深情", "不善表达"],
            speech_patterns={
                "商务": "简洁有力，命令式",
                "对女主前期": "冷漠疏离，偶尔嘲讽",
                "对女主后期": "小心翼翼，恳求讨好",
                "对下属": "威严简短",
                "愤怒时": "声音低沉，咬牙切齿"
            },
            common_phrases=["够了", "你以为你是谁", "苏念，你听我解释", "我错了"],
            tone="低沉磁性，情绪激动时会颤抖",
            habits=[
                "生气时会松领带",
                "思考时会揉眉心", 
                "紧张时会握紧拳头",
                "看女主时目光会柔和"
            ],
            reactions={
                "被拒绝": "先是愣住，然后固执坚持",
                "看到女主受伤": "失控，不顾一切保护",
                "面对情敌": "占有欲爆发，冷face威胁"
            },
            appearance={
                "身高": "188cm",
                "体型": "宽肩窄腰，身材挺拔",
                "脸型": "轮廓分明，下颌线锐利",
                "眼睛": "深邃黑眸，生气时锐利，看女主时温柔",
                "头发": "黑色短发，一丝不苟"
            },
            clothing_style="高定西装，深色系为主，领带夹是女主送的",
            distinctive_features=["左手无名指有戒痕", "右肩有旧伤疤"],
            family_background="陆氏集团独子，母亲早逝，父亲强势",
            education="哈佛MBA，少年天才",
            past_experiences=[
                "18岁接手家族企业",
                "曾因商战失去挚友",
                "初恋被背叛（其实是误会）"
            ],
            relationship_dynamics={
                "苏念": {
                    "前期": "占有但不珍惜，理所当然",
                    "中期": "悔恨交加，卑微恳求",
                    "后期": "珍惜呵护，害怕失去"
                },
                "沈雨薇": {
                    "态度": "从信任到看清真面目",
                    "转变": "第7章后完全决裂"
                }
            },
            core_motivation="前期：维护骄傲；后期：挽回爱人",
            fears=["失去苏念", "重蹈覆辙", "父亲的阴影"],
            desires=["苏念的原谅", "真正的家庭", "弥补过错"]
        )
        
        # 女主：苏念
        self.character_traits["苏念"] = CharacterTraits(
            core_personality=["坚强", "善良", "倔强", "细腻", "缺乏安全感"],
            speech_patterns={
                "平常": "温柔但有距离感",
                "对男主前期": "决绝冷漠，不留余地",
                "对男主中期": "刻意疏离，偶尔动摇",
                "对男主后期": "口是心非，言不由衷",
                "对朋友": "真诚温暖"
            },
            common_phrases=["没必要了", "我们已经结束了", "陆景深，放过彼此吧", "我累了"],
            tone="清冷中带着疲惫，动情时会哽咽",
            habits=[
                "难过时会咬下唇",
                "紧张时会攥衣角",
                "思念时会摸无名指（曾经的戒指位置）",
                "疲惫时会靠窗发呆"
            ],
            reactions={
                "见到男主": "下意识后退，眼神躲闪",
                "被关心": "先是抗拒，然后眼眶泛红",
                "提到过去": "身体僵硬，强装镇定"
            },
            appearance={
                "身高": "165cm",
                "体型": "纤细但不柔弱",
                "脸型": "巴掌脸，精致小巧",
                "眼睛": "杏眼，哭过会肿",
                "头发": "栗色长发，离婚后剪短"
            },
            clothing_style="简约优雅，色彩素净，不再穿男主喜欢的红色",
            distinctive_features=["左肩有痣", "手腕细白", "怀孕后憔悴"],
            family_background="父母早亡，靠自己打拼",
            education="设计学院top1",
            past_experiences=[
                "为男主放弃出国深造",
                "曾经流产过一次（男主不知）",
                "独自撑过最难的时光"
            ],
            relationship_dynamics={
                "陆景深": {
                    "前期": "死心，不想有任何交集",
                    "中期": "动摇但不敢相信",
                    "后期": "想原谅但害怕"
                },
                "顾北辰": {
                    "态度": "感激但无法回应",
                    "界限": "始终保持距离"
                }
            },
            core_motivation="保护自己不再受伤",
            fears=["再次被抛弃", "孩子没有父亲", "重蹈覆辙"],
            desires=["平静的生活", "孩子健康", "内心深处仍爱男主"]
        )
        
        # 男配：顾北辰
        self.character_traits["顾北辰"] = CharacterTraits(
            core_personality=["温柔", "理性", "隐忍", "绅士", "知进退"],
            speech_patterns={
                "对女主": "关切温柔，点到为止",
                "对男主": "表面客气，暗中较量",
                "工作中": "专业严谨"
            },
            common_phrases=["你要照顾好自己", "我一直都在", "他不懂珍惜"],
            tone="温润如玉",
            habits=[
                "推眼镜",
                "永远带着得体的笑",
                "默默做事不邀功"
            ],
            appearance={
                "身高": "182cm",
                "体型": "清瘦儒雅",
                "眼镜": "金丝眼镜"
            },
            clothing_style="休闲西装，浅色系",
            core_motivation="守护苏念的笑容",
            relationship_dynamics={
                "苏念": {"态度": "默默守护，知道没结果但甘愿"},
                "陆景深": {"态度": "既是情敌又惺惺相惜"}
            }
        )
        
        # 女配：沈雨薇  
        self.character_traits["沈雨薇"] = CharacterTraits(
            core_personality=["心机", "自私", "善于伪装", "偏执"],
            speech_patterns={
                "表面": "柔弱无辜，楚楚可怜",
                "私下": "尖酸刻薄，咄咄逼人"
            },
            common_phrases=["景深哥哥", "我不是故意的", "苏念姐姐不要误会"],
            habits=[
                "假装柔弱博同情",
                "恰到好处地出现",
                "制造误会"
            ],
            appearance={
                "身高": "168cm", 
                "特点": "妖娆妩媚"
            },
            core_motivation="得到陆景深",
            relationship_dynamics={
                "陆景深": {"手段": "利用过去，装可怜"},
                "苏念": {"态度": "表面示好，暗中陷害"}
            }
        )
        
        # 初始化状态
        self.character_states["陆景深"] = CharacterState(
            emotional_state="自负，认为女主在闹脾气",
            location="陆氏集团",
            current_goal="维持表面的骄傲"
        )
        
        self.character_states["苏念"] = CharacterState(
            emotional_state="心死，决心离开",
            location="两人的家（准备搬走）",
            current_goal="彻底离开这段关系",
            knowledge={"怀孕", "沈雨薇的真面目"}
        )
    
    def get_character_profile(self, name: str, chapter: int) -> Dict:
        """获取人物在特定章节的完整档案"""
        if name not in self.character_traits:
            return {}
        
        traits = self.character_traits[name]
        state = self.character_states.get(name, CharacterState())
        
        # 根据章节调整表现
        profile = {
            "traits": traits,
            "state": state,
            "chapter_specific": self._get_chapter_specific_behavior(name, chapter)
        }
        
        return profile
    
    def _get_chapter_specific_behavior(self, name: str, chapter: int) -> Dict:
        """获取特定章节的行为指导"""
        behaviors = {}
        
        if name == "陆景深":
            if chapter <= 3:
                behaviors = {
                    "态度": "冷漠自负，认为女主无理取闹",
                    "行为": "工作为重，忽视女主感受",
                    "语言": "命令式，不容反驳"
                }
            elif chapter <= 6:
                behaviors = {
                    "态度": "开始空虚，但还在强撑",
                    "行为": "频繁看手机，下意识寻找女主身影",
                    "语言": "对别人更加暴躁"
                }
            elif chapter <= 9:
                behaviors = {
                    "态度": "悔恨交加，疯狂寻找",
                    "行为": "失去理智，不顾一切",
                    "语言": "哀求，自责，崩溃"
                }
            elif chapter <= 12:
                behaviors = {
                    "态度": "卑微追求，小心翼翼",
                    "行为": "各种讨好，默默守护",
                    "语言": "温柔恳切，不敢大声"
                }
            else:
                behaviors = {
                    "态度": "成熟深情，懂得珍惜",
                    "行为": "行动证明，不只是说",
                    "语言": "真诚坦率，敢于示弱"
                }
        
        elif name == "苏念":
            if chapter <= 3:
                behaviors = {
                    "态度": "决绝，不留余地",
                    "行为": "收拾东西，删除痕迹",
                    "语言": "冷漠简短，拒绝交流"
                }
            elif chapter <= 6:
                behaviors = {
                    "态度": "强装坚强，内心煎熬",
                    "行为": "努力工作，照顾自己",
                    "语言": "对别人正常，提到男主会沉默"
                }
            elif chapter <= 9:
                behaviors = {
                    "态度": "躲避，不想面对",
                    "行为": "刻意避开，转身就走",
                    "语言": "拒绝交流，言辞决绝"
                }
            elif chapter <= 12:
                behaviors = {
                    "态度": "动摇，但装作不在意",
                    "行为": "偷偷关注，口是心非",
                    "语言": "嘴硬心软，偶尔破防"
                }
            else:
                behaviors = {
                    "态度": "想原谅但还在犹豫",
                    "行为": "不再躲避，愿意倾听",
                    "语言": "语气软化，偶尔关心"
                }
        
        return behaviors
    
    def update_interaction(self, chapter: int, character1: str, character2: str, 
                          interaction_type: str, details: str):
        """记录人物互动"""
        self.interaction_history.append({
            "chapter": chapter,
            "characters": [character1, character2],
            "type": interaction_type,
            "details": details,
            "impact": self._evaluate_impact(character1, character2, interaction_type)
        })
    
    def _evaluate_impact(self, char1: str, char2: str, interaction_type: str) -> str:
        """评估互动对关系的影响"""
        if char1 == "陆景深" and char2 == "苏念":
            if interaction_type in ["争吵", "冷战"]:
                return "关系恶化"
            elif interaction_type in ["道歉", "守护"]:
                return "关系缓和"
            elif interaction_type in ["误会", "伤害"]:
                return "关系破裂"
        return "关系不变"
    
    def get_relationship_status(self, char1: str, char2: str, chapter: int) -> str:
        """获取两个人物在特定章节的关系状态"""
        # 根据章节和互动历史判断
        if char1 == "陆景深" and char2 == "苏念":
            if chapter <= 3:
                return "婚姻破裂中"
            elif chapter <= 6:
                return "已离婚，无交集"
            elif chapter <= 9:
                return "男方追求，女方抗拒"
            elif chapter <= 12:
                return "关系缓和，女方动摇"
            else:
                return "破镜重圆"
        return "普通关系"
    
    def validate_consistency(self, chapter_text: str, character_name: str) -> List[str]:
        """验证章节文本中的人物一致性"""
        issues = []
        
        if character_name not in self.character_traits:
            return issues
        
        traits = self.character_traits[character_name]
        
        # 检查是否符合核心性格
        # 检查说话风格是否一致
        # 检查行为是否符合习惯
        # （这里可以接入NLP分析）
        
        return issues
    
    def save_state(self, chapter: int):
        """保存人物状态"""
        state_file = self.save_dir / f"character_consistency_ch{chapter:02d}.json"
        
        state_data = {
            "chapter": chapter,
            "character_states": {
                name: {
                    "emotional_state": state.emotional_state,
                    "physical_state": state.physical_state,
                    "location": state.location,
                    "current_goal": state.current_goal,
                    "recent_events": state.recent_events,
                    "knowledge": list(state.knowledge),
                    "relationships_status": state.relationships_status
                }
                for name, state in self.character_states.items()
            },
            "interaction_history": self.interaction_history[-20:],  # 保留最近20条
            "important_items": self.important_items,
            "locations": self.locations
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
    
    def load_state(self, chapter: int) -> bool:
        """加载人物状态"""
        state_file = self.save_dir / f"character_consistency_ch{chapter:02d}.json"
        if not state_file.exists():
            return False
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        # 恢复状态
        for name, state_dict in state_data.get("character_states", {}).items():
            if name not in self.character_states:
                self.character_states[name] = CharacterState()
            
            state = self.character_states[name]
            state.emotional_state = state_dict.get("emotional_state", "")
            state.physical_state = state_dict.get("physical_state", "")
            state.location = state_dict.get("location", "")
            state.current_goal = state_dict.get("current_goal", "")
            state.recent_events = state_dict.get("recent_events", [])
            state.knowledge = set(state_dict.get("knowledge", []))
            state.relationships_status = state_dict.get("relationships_status", {})
        
        self.interaction_history = state_data.get("interaction_history", [])
        self.important_items = state_data.get("important_items", {})
        self.locations = state_data.get("locations", {})
        
        return True