"""
场景管理器 - 管理场景描写、环境氛围和情节节奏
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import random


@dataclass
class Scene:
    """场景定义"""
    name: str
    location_type: str  # 室内/室外/车内等
    atmosphere: str  # 氛围
    time_of_day: str  # 时间
    weather: str  # 天气
    sensory_details: Dict[str, List[str]] = field(default_factory=dict)  # 感官细节
    props: List[str] = field(default_factory=list)  # 道具
    mood_impact: str = ""  # 对情绪的影响
    symbolism: str = ""  # 象征意义


class SceneManager:
    """场景和情节节奏管理"""
    
    def __init__(self):
        self.scenes = self._init_romance_scenes()
        self.plot_rhythm = self._init_plot_rhythm()
        self.scene_transitions = self._init_transitions()
    
    def _init_romance_scenes(self) -> Dict[str, Scene]:
        """初始化追妻流常用场景"""
        scenes = {}
        
        # 家/卧室 - 亲密空间
        scenes["主卧"] = Scene(
            name="两人曾经的主卧",
            location_type="室内",
            atmosphere="空虚冷清/曾经温馨",
            time_of_day="深夜",
            weather="",
            sensory_details={
                "视觉": ["空了一半的衣柜", "床头只剩一个枕头", "梳妆台上她的物品都不见了", "结婚照面朝下"],
                "嗅觉": ["她惯用的香水味逐渐消散", "只剩下冰冷的空气"],
                "触觉": ["床单冰凉", "她那侧的床铺整齐得像从未有人睡过"],
                "听觉": ["只有钟表的滴答声", "窗外偶尔的车声"]
            },
            props=["结婚照", "她落下的发圈", "枕头上的长发丝"],
            mood_impact="孤独、懊悔、思念",
            symbolism="关系的终结和空虚"
        )
        
        # 办公室 - 权力空间
        scenes["总裁办公室"] = Scene(
            name="陆氏集团顶层办公室",
            location_type="室内",
            atmosphere="压抑严肃/表面光鲜",
            time_of_day="工作时间",
            weather="透过落地窗看到的城市",
            sensory_details={
                "视觉": ["落地窗外的城市天际线", "巨大的办公桌", "冷色调装修", "她曾经坐过的沙发"],
                "听觉": ["键盘敲击声", "电话铃声", "中央空调的低鸣"],
                "触觉": ["真皮座椅的冰冷", "钢笔的重量"],
                "嗅觉": ["咖啡香", "皮革味", "消毒水味"]
            },
            props=["她送的钢笔", "抽屉里的合照", "咖啡杯", "文件堆"],
            mood_impact="疏离、压力、控制",
            symbolism="男主的精神堡垒"
        )
        
        # 雨夜街头 - 情绪爆发场景
        scenes["雨夜街头"] = Scene(
            name="城市街头",
            location_type="室外",
            atmosphere="凄凉绝望",
            time_of_day="深夜",
            weather="暴雨",
            sensory_details={
                "视觉": ["雨幕朦胧", "街灯昏黄", "水洼倒影", "她消失在雨中的背影"],
                "听觉": ["雨声如注", "雷声轰鸣", "她的名字在风中破碎"],
                "触觉": ["冰冷的雨水", "湿透的衣服贴在身上", "寒意刺骨"],
                "嗅觉": ["雨水的腥味", "柏油路的味道"]
            },
            props=["破碎的伞", "湿透的西装", "手机在雨中闪烁"],
            mood_impact="绝望、崩溃、懊悔",
            symbolism="情感的暴风雨"
        )
        
        # 医院 - 转折场景
        scenes["医院"] = Scene(
            name="市中心医院",
            location_type="室内",
            atmosphere="紧张焦虑",
            time_of_day="任何时间",
            weather="",
            sensory_details={
                "视觉": ["白色的墙壁", "匆忙的医护", "病床", "输液架", "她苍白的脸"],
                "听觉": ["仪器的滴滴声", "脚步声", "低声的交谈"],
                "嗅觉": ["消毒水味", "药品味"],
                "触觉": ["冰冷的金属椅", "她虚弱的手"]
            },
            props=["病历本", "B超单", "药品", "陪护椅"],
            mood_impact="担心、恐惧、悔恨",
            symbolism="生死考验，真情显露"
        )
        
        # 咖啡厅 - 对峙/相遇场景
        scenes["咖啡厅"] = Scene(
            name="她常去的咖啡厅",
            location_type="室内",
            atmosphere="表面平静暗流涌动",
            time_of_day="下午",
            weather="窗外阳光",
            sensory_details={
                "视觉": ["温暖的装潢", "角落的卡座", "她惯坐的位置", "窗外的梧桐树"],
                "听觉": ["轻柔的音乐", "咖啡机的声音", "低声交谈"],
                "嗅觉": ["咖啡香", "甜点香", "她的香水"],
                "触觉": ["杯子的温度", "柔软的沙发"]
            },
            props=["两杯咖啡", "她爱吃的提拉米苏", "手机", "她的设计稿"],
            mood_impact="尴尬、紧张、克制",
            symbolism="曾经的甜蜜与现在的疏离"
        )
        
        # 机场 - 离别/重逢场景
        scenes["机场"] = Scene(
            name="国际机场",
            location_type="室内",
            atmosphere="离别的伤感/重逢的激动",
            time_of_day="清晨/深夜",
            weather="",
            sensory_details={
                "视觉": ["人来人往", "巨大的航班显示屏", "玻璃幕墙", "她拖着行李的身影"],
                "听觉": ["广播声", "行李轮子的声音", "此起彼伏的告别声"],
                "触觉": ["拥挤的人群", "行李的重量"],
                "情感": ["离别的不舍", "重逢的激动"]
            },
            props=["机票", "行李箱", "护照", "告别的拥抱"],
            mood_impact="离别/重逢，转折点",
            symbolism="人生的岔路口"
        )
        
        return scenes
    
    def _init_plot_rhythm(self) -> Dict[int, Dict]:
        """初始化情节节奏控制"""
        rhythm = {
            1: {
                "intensity": 9,  # 情节强度 1-10
                "pace": "急",  # 快/中/慢/急
                "emotion_peak": "误会爆发，关系破裂",
                "key_scenes": ["主卧争吵", "她收拾东西", "摔门而去"],
                "cliffhanger": "她手中的验孕单掉落"
            },
            2: {
                "intensity": 8,
                "pace": "中",
                "emotion_peak": "决绝离开",
                "key_scenes": ["律师事务所", "冷漠签字", "最后一面"],
                "cliffhanger": "她隐瞒了什么重要的事"
            },
            3: {
                "intensity": 7,
                "pace": "慢",
                "emotion_peak": "各自的空虚",
                "key_scenes": ["空荡的家", "她的新住处", "偶然得知她的消息"],
                "cliffhanger": "男配出现在她身边"
            },
            4: {
                "intensity": 5,
                "pace": "慢",
                "emotion_peak": "思念煎熬",
                "key_scenes": ["深夜独饮", "翻看照片", "梦中惊醒"],
                "cliffhanger": "收到她住院的消息"
            },
            5: {
                "intensity": 7,
                "pace": "中",
                "emotion_peak": "意外重逢的慌乱",
                "key_scenes": ["商务酒会相遇", "她挽着别人的手", "对视后的逃离"],
                "cliffhanger": "发现她憔悴很多"
            },
            6: {
                "intensity": 6,
                "pace": "中",
                "emotion_peak": "暗中关注",
                "key_scenes": ["偷偷跟随", "远远看着", "通过别人打听"],
                "cliffhanger": "白月光说出当年真相的一角"
            },
            7: {
                "intensity": 8,
                "pace": "急",
                "emotion_peak": "真相初现的震惊",
                "key_scenes": ["调查当年", "发现被骗", "白月光承认"],
                "cliffhanger": "原来她为他付出那么多"
            },
            8: {
                "intensity": 9,
                "pace": "急",
                "emotion_peak": "悔恨崩溃",
                "key_scenes": ["雨夜寻找", "她的拒绝", "跪地哀求"],
                "cliffhanger": "她晕倒在他面前"
            },
            9: {
                "intensity": 10,
                "pace": "急",
                "emotion_peak": "生死考验",
                "key_scenes": ["医院抢救", "得知她怀孕", "差点失去她"],
                "cliffhanger": "她醒来第一句话是让他走"
            },
            10: {
                "intensity": 6,
                "pace": "慢",
                "emotion_peak": "小心靠近",
                "key_scenes": ["医院陪护", "她的冷漠", "默默照顾"],
                "cliffhanger": "男配的出现"
            },
            11: {
                "intensity": 7,
                "pace": "中",
                "emotion_peak": "争夺与守护",
                "key_scenes": ["三人对峙", "她的选择", "他的坚持"],
                "cliffhanger": "她说了句谢谢"
            },
            12: {
                "intensity": 6,
                "pace": "慢",
                "emotion_peak": "心防松动",
                "key_scenes": ["日常相处", "他的改变", "她偷偷流泪"],
                "cliffhanger": "她主动问他累不累"
            },
            13: {
                "intensity": 8,
                "pace": "中",
                "emotion_peak": "最后的考验",
                "key_scenes": ["家族阻挠", "他的选择", "为她对抗全世界"],
                "cliffhanger": "她终于说出真心话"
            },
            14: {
                "intensity": 7,
                "pace": "慢",
                "emotion_peak": "冰释前嫌",
                "key_scenes": ["深夜长谈", "互诉衷肠", "相拥而泣"],
                "cliffhanger": "他重新求婚"
            },
            15: {
                "intensity": 9,
                "pace": "中",
                "emotion_peak": "圆满结局",
                "key_scenes": ["婚礼", "孩子出生", "一家三口"],
                "cliffhanger": None  # 结局不需要悬念
            }
        }
        return rhythm
    
    def _init_transitions(self) -> Dict[str, List[str]]:
        """初始化场景转换模板"""
        return {
            "时间过渡": [
                "三个月后，初春的阳光终于穿透了阴霾...",
                "那一夜的暴雨下了整整一夜，天亮时...",
                "时间是最残忍的刽子手，一晃眼...",
                "日子一天天过去，他以为自己能够习惯..."
            ],
            "空间转换": [
                "与此同时，在城市的另一端...",
                "当他在办公室里发呆时，她正在...",
                "离开那个令人窒息的地方后...",
                "从医院出来，外面的世界依然喧嚣..."
            ],
            "情绪转折": [
                "就在他以为一切都结束时...",
                "命运总是爱开玩笑，就在她决定放下时...",
                "有些真相来得太晚，却又刚刚好...",
                "心防崩塌只在一瞬间..."
            ],
            "悬念设置": [
                "她没有看到的是，他转身后的崩溃...",
                "如果他知道真相，一定不会放手...",
                "命运的齿轮开始转动，谁也无法预料...",
                "这个秘密，终究还是被发现了..."
            ]
        }
    
    def get_scene_description(self, scene_name: str, emotion: str = "", time: str = "") -> str:
        """获取场景描写"""
        if scene_name not in self.scenes:
            return ""
        
        scene = self.scenes[scene_name]
        description = []
        
        # 构建场景描写
        description.append(f"{time or scene.time_of_day}，{scene.name}。")
        
        # 添加感官细节
        if "视觉" in scene.sensory_details:
            visual = random.choice(scene.sensory_details["视觉"])
            description.append(visual)
        
        if emotion == "悲伤" and "触觉" in scene.sensory_details:
            touch = random.choice(scene.sensory_details["触觉"])
            description.append(touch)
        
        # 添加氛围
        if scene.atmosphere:
            description.append(f"整个空间弥漫着{scene.atmosphere}的气息。")
        
        # 添加道具细节
        if scene.props:
            prop = random.choice(scene.props)
            description.append(f"{prop}静静地诉说着过往。")
        
        return " ".join(description)
    
    def get_chapter_rhythm(self, chapter: int) -> Dict:
        """获取章节的节奏控制"""
        return self.plot_rhythm.get(chapter, {
            "intensity": 5,
            "pace": "中",
            "emotion_peak": "",
            "key_scenes": [],
            "cliffhanger": ""
        })
    
    def get_transition(self, transition_type: str) -> str:
        """获取场景转换语句"""
        if transition_type in self.scene_transitions:
            return random.choice(self.scene_transitions[transition_type])
        return ""
    
    def suggest_scene_sequence(self, chapter: int) -> List[Tuple[str, str]]:
        """建议章节的场景序列"""
        rhythm = self.get_chapter_rhythm(chapter)
        suggestions = []
        
        if chapter == 1:
            suggestions = [
                ("主卧", "争吵爆发"),
                ("总裁办公室", "冷漠处理"),
                ("主卧", "她离开")
            ]
        elif chapter == 5:
            suggestions = [
                ("咖啡厅", "意外相遇"),
                ("总裁办公室", "他的失神"),
                ("雨夜街头", "远远跟随")
            ]
        elif chapter == 8:
            suggestions = [
                ("雨夜街头", "疯狂寻找"),
                ("她的住处", "苦苦哀求"),
                ("医院", "她晕倒")
            ]
        elif chapter == 15:
            suggestions = [
                ("主卧", "重新布置"),
                ("咖啡厅", "甜蜜约会"),
                ("医院", "孩子出生")
            ]
        
        return suggestions
    
    def get_scene_prompt(self, chapter: int) -> str:
        """生成场景描写提示"""
        rhythm = self.get_chapter_rhythm(chapter)
        scenes = self.suggest_scene_sequence(chapter)
        
        prompt = f"本章节奏：{rhythm['pace']}，情绪强度：{rhythm['intensity']}/10\n"
        prompt += f"情感高潮：{rhythm['emotion_peak']}\n"
        prompt += f"关键场景：{', '.join(rhythm['key_scenes'])}\n"
        
        if scenes:
            prompt += "\n建议场景序列：\n"
            for scene, purpose in scenes:
                scene_obj = self.scenes.get(scene)
                if scene_obj:
                    prompt += f"- {scene}（{purpose}）：{scene_obj.atmosphere}\n"
        
        if rhythm.get('cliffhanger'):
            prompt += f"\n章节悬念：{rhythm['cliffhanger']}"
        
        return prompt