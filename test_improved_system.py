#!/usr/bin/env python3
"""
测试改进后的小说生成系统
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from novel_runner.story_manager import StoryManager, Character, PlotThread, WorldDetail


def test_story_manager():
    """测试故事管理器功能"""
    print("=" * 60)
    print("测试故事管理器")
    print("=" * 60)
    
    # 创建临时目录
    test_dir = Path("test_story_state")
    test_dir.mkdir(exist_ok=True)
    
    # 初始化管理器
    manager = StoryManager(test_dir)
    
    # 测试1: 添加人物
    print("\n1. 测试人物管理")
    print("-" * 40)
    
    manager.update_character("林风", {
        "role": "主角",
        "personality": ["坚毅", "智慧", "重情义"],
        "abilities": ["血触古卷传承", "星辰之力"],
        "current_state": "初步掌握血触古卷的力量"
    })
    
    manager.update_character("苏雨", {
        "role": "重要配角",
        "personality": ["聪慧", "温柔", "勇敢"],
        "relationships": {"林风": "青梅竹马，暗生情愫"},
        "current_state": "与林风并肩作战"
    })
    
    print("已添加人物：")
    for name, char in manager.characters.items():
        print(f"\n{char.to_prompt_text()}")
    
    # 测试2: 添加剧情线索
    print("\n\n2. 测试剧情线索管理")
    print("-" * 40)
    
    manager.add_plot_thread(
        "血触古卷之谜",
        "上古神器血触古卷隐藏着改变天地的秘密",
        key_events=["古卷现世", "林风获得传承", "力量初现"]
    )
    
    manager.update_plot_thread("主线", event="各方势力开始关注林风")
    
    print("当前剧情线索：")
    for name, thread in manager.plot_threads.items():
        print(f"\n{thread.to_prompt_text()}")
    
    # 测试3: 添加世界观细节
    print("\n\n3. 测试世界观管理")
    print("-" * 40)
    
    manager.add_world_detail("势力", "青云门", "正道大派，掌门心怀天下", 4)
    manager.add_world_detail("地理", "龙王庙", "藏有上古石碑的神秘之地", 3)
    manager.add_world_detail("法宝", "血触古卷", "记载天地秘法的上古神器", 5)
    
    print("重要世界观设定：")
    for detail in sorted(manager.world_details, key=lambda x: x.importance, reverse=True)[:5]:
        print(f"  {detail.to_prompt_text()}")
    
    # 测试4: 章节概要管理
    print("\n\n4. 测试章节概要管理")
    print("-" * 40)
    
    manager.add_chapter_summary(1, [
        "林风意外穿越异世",
        "血触古卷认主",
        "初遇神秘势力追杀",
        "展现惊人潜力"
    ])
    
    manager.add_chapter_summary(2, [
        "结识苏雨等同伴",
        "祭天台上立下誓言",
        "初战告捷",
        "发现更大阴谋"
    ])
    
    # 测试5: 获取章节上下文
    print("\n\n5. 测试章节上下文生成")
    print("-" * 40)
    
    context = manager.get_context_for_chapter(3, window_size=2)
    
    print("为第3章准备的上下文信息：")
    print("\n人物档案：")
    for char_text in context["characters"].values():
        print(char_text)
        print()
    
    print("剧情线索：")
    for plot_text in context["plot_threads"].values():
        print(plot_text)
    
    print("\n近期剧情：")
    for summary in context["recent_summaries"]:
        print(f"  {summary}")
    
    # 测试6: 状态保存和加载
    print("\n\n6. 测试状态持久化")
    print("-" * 40)
    
    manager.save_state(2)
    print("已保存第2章状态")
    
    # 创建新管理器并加载
    new_manager = StoryManager(test_dir)
    loaded = new_manager.load_state(2)
    
    if loaded:
        print("成功加载状态")
        print(f"已加载 {len(new_manager.characters)} 个人物")
        print(f"已加载 {len(new_manager.plot_threads)} 条剧情线索")
        print(f"已加载 {len(new_manager.world_details)} 个世界观细节")
        print(f"已加载 {len(new_manager.chapter_summaries)} 章概要")
    
    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir)
    print("\n测试完成，已清理临时文件")
    
    return True


def test_improved_prompt():
    """测试改进后的提示词构建"""
    print("\n" + "=" * 60)
    print("测试改进后的提示词")
    print("=" * 60)
    
    from novel_runner.templates import build_chapter_messages
    
    # 模拟故事上下文
    story_context = {
        "characters": {
            "林风": "林风（主角）：\n  性格：坚毅、智慧\n  能力：血触古卷传承\n  当前：掌握初步力量",
            "苏雨": "苏雨（配角）：\n  性格：聪慧、勇敢\n  关系：与林风青梅竹马"
        },
        "plot_threads": {
            "主线": "【天地大劫】（进行中）：千年劫数将至\n  关键事件：预言显现→寻找传人",
            "支线": "【血触古卷】（进行中）：神器认主\n  关键事件：古卷现世→力量觉醒"
        },
        "world_details": [
            "[法宝] 血触古卷：记载天地秘法的神器",
            "[修行] 心性为本：修行重心性，法术为辅"
        ],
        "recent_summaries": [
            "第1章：林风穿越，获血触古卷",
            "第1章：初遇追杀，展现潜力",
            "第2章：结识苏雨，立下誓言",
            "第2章：祭天台一战，发现阴谋"
        ]
    }
    
    # 当前章节概要
    prev_summary = [
        "龙王庙中发现石碑",
        "各方势力齐聚争夺",
        "林风以智破局",
        "获得重要线索"
    ]
    
    # 构建第3章消息
    messages = build_chapter_messages(
        chapter_index=3,
        summary_lines=prev_summary,
        story_context=story_context
    )
    
    print("\n系统提示词：")
    print("-" * 40)
    print(messages[0]["content"][:200] + "...")
    
    print("\n用户提示词（包含所有上下文）：")
    print("-" * 40)
    print(messages[1]["content"])
    
    return True


if __name__ == "__main__":
    print("开始测试改进后的小说生成系统\n")
    
    # 运行测试
    test_story_manager()
    test_improved_prompt()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
    print("\n改进内容总结：")
    print("1. ✅ 添加了完整的人物档案系统")
    print("2. ✅ 实现了多章节历史概要累积")
    print("3. ✅ 加入了剧情线索追踪机制")
    print("4. ✅ 增强了世界观细节管理")
    print("5. ✅ 支持故事状态的保存和恢复")
    print("\n现在每章生成时都会包含：")
    print("- 主要人物的完整档案和当前状态")
    print("- 活跃的剧情线索及其最新进展")
    print("- 最近几章的关键剧情点（滑动窗口）")
    print("- 重要的世界观设定细节")
    print("\n可以使用以下命令运行改进后的系统：")
    print("python -m novel_runner.runner --dry-run  # 测试模式")
    print("python -m novel_runner.runner  # 实际生成")