#!/usr/bin/env python3
"""
测试完整的审核系统
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from novel_runner.censor_manager import CensorManager, generate_chapter_title
from novel_runner.client import BaiduErnieClient


def test_censor_flow():
    """测试审核流程"""
    print("=" * 60)
    print("测试审核流程（模拟）")
    print("=" * 60)
    
    # 模拟一个可能有问题的章节内容
    test_chapter = """
林风站在祭坛中央，感受着体内气脉的流动。远处传来钟声，仿佛在召唤着什么。

突然，一道血光冲天而起，整个祭坛都被染成了猩红色。那些围观的弟子纷纷后退，脸上露出恐惧的神情。

"这是上古血祭之术！"有人惊呼道，"传说中需要以生灵之血为引，方能开启禁忌之门。"

林风紧握手中的古卷，感受到其中传来的灼热力量。他知道，这一刻的选择将决定所有人的命运。
"""
    
    print("测试章节内容（节选）：")
    print("-" * 40)
    print(test_chapter[:200] + "...")
    print("-" * 40)
    
    # 测试标题生成（模拟）
    print("\n1. 测试章节标题生成")
    print("-" * 40)
    
    # 模拟标题生成
    mock_title = "血祭禁地"
    print(f"生成的标题: {mock_title}")
    print(f"完整文件名: 第3章-{mock_title}.md")
    
    # 测试审核结果处理
    print("\n2. 测试审核结果处理")
    print("-" * 40)
    
    # 模拟审核结果
    mock_violations = [
        {
            "type": "暴力血腥",
            "msg": "内容包含血腥暴力描述",
            "hits": ["血光", "猩红", "血祭"]
        }
    ]
    
    print("模拟审核发现的问题：")
    for v in mock_violations:
        print(f"  - {v['type']}: {v['msg']}")
        if v.get('hits'):
            print(f"    涉及词汇: {', '.join(v['hits'])}")
    
    # 模拟修正后的内容
    fixed_chapter = """
林风站在祭坛中央，感受着体内气脉的流动。远处传来钟声，仿佛在召唤着什么。

突然，一道红光冲天而起，整个祭坛都被笼罩在神秘的光芒中。那些围观的弟子纷纷后退，脸上露出敬畏的神情。

"这是上古秘术！"有人惊呼道，"传说中需要以精神之力为引，方能开启神秘之门。"

林风紧握手中的古卷，感受到其中传来的温暖力量。他知道，这一刻的选择将决定所有人的命运。
"""
    
    print("\n修正后的内容（节选）：")
    print("-" * 40)
    print(fixed_chapter[:200] + "...")
    print("-" * 40)
    
    # 文件命名逻辑
    print("\n3. 文件命名逻辑")
    print("-" * 40)
    print("审核通过: 第3章-血祭禁地.md")
    print("审核失败: 第3章_审核失败.md")
    
    return True


def test_integration():
    """测试集成效果"""
    print("\n" + "=" * 60)
    print("测试完整工作流程")
    print("=" * 60)
    
    print("\n工作流程：")
    print("1. ernie-x1-turbo-32k 生成章节内容")
    print("   ↓")
    print("2. 清理输出（去除元信息）")
    print("   ↓")
    print("3. 百度文本审核API检测")
    print("   ↓")
    print("4. [如果不通过] ernie-4.5-turbo-128k 修正")
    print("   ↓")
    print("5. 重新审核（最多3次）")
    print("   ↓")
    print("6. [审核通过] ernie-4.5-turbo-128k 生成标题")
    print("   ↓")
    print("7. 保存为: 第X章-标题.md")
    print("   或")
    print("   [审核失败] 保存为: 第X章_审核失败.md")
    
    print("\n配置要求：")
    print("- BAIDU_API_KEY: 百度API密钥（用于ERNIE模型）")
    print("- BAIDU_SECRET_KEY: 百度Secret密钥")
    print("- TEXT_API_KEY: 文本审核API密钥")
    print("- TEXT_SECRET_KEY: 文本审核Secret密钥")
    
    print("\n文件结构：")
    print("outputs/")
    print("├── chapters/")
    print("│   ├── 第1章-血触古卷.md")
    print("│   ├── 第2章-祭天台结义.md")
    print("│   └── 第3章_审核失败.md  # 如果审核未通过")
    print("├── summaries/")
    print("├── logs/")
    print("│   ├── censor_01.json      # 审核日志")
    print("│   ├── fix_01.json         # 修正日志")
    print("│   └── chapter_01.raw.txt  # 原始输出")
    print("└── story_state/            # 故事状态")
    
    return True


if __name__ == "__main__":
    print("测试审核和命名系统\n")
    
    test_censor_flow()
    test_integration()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    print("\n使用说明：")
    print("1. 配置.env文件：")
    print("   TEXT_API_KEY=你的文本审核API密钥")
    print("   TEXT_SECRET_KEY=你的文本审核SECRET密钥")
    print("")
    print("2. 运行生成器：")
    print("   python -m novel_runner.runner")
    print("")
    print("3. 系统将自动：")
    print("   - 使用ernie-x1生成内容")
    print("   - 审核每章内容")
    print("   - 必要时用ernie-4.5修正")
    print("   - 用ernie-4.5生成标题")
    print("   - 保存带标题的章节文件")