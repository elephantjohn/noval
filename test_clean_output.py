#!/usr/bin/env python3
"""
测试章节输出清理功能
"""
from novel_runner.post_processor import clean_chapter_text, extract_clean_summary


def test_clean_chapter():
    """测试章节文本清理"""
    
    # 模拟包含杂质的章节输出
    raw_chapter = """
第一章 血触古卷

---

青铜鹤纹在古籍残页上泛起幽蓝微光时，沈砚之正用镊子夹起第三片竹简。子夜时分的博物馆库房只有顶灯一束光，照得他鼻梁上的金丝眼镜泛起冷光。

地面忽然震颤起来。

沈砚之扶住展柜的手被玻璃划出细口，血珠滴在竹简上，那些原本静止的鹤纹突然活过来般游走。

（中间省略正文内容...）

当白光散去，祭坛上只剩下九尊獬豸仍在吐息。沈砚之发现自己能看见别人看不见的东西。

===

下一章：失忆者初探仙门秘境，暗流涌动。

写作意图：引出主角进入异世界的契机。
"""

    cleaned = clean_chapter_text(raw_chapter)
    
    print("原始文本长度:", len(raw_chapter))
    print("清理后长度:", len(cleaned))
    print("\n清理后文本（前500字）:")
    print("-" * 50)
    print(cleaned[:500])
    print("-" * 50)
    
    # 验证是否去除了非小说内容
    assert "第一章" not in cleaned
    assert "---" not in cleaned
    assert "===" not in cleaned
    assert "下一章" not in cleaned
    assert "写作意图" not in cleaned
    assert "青铜鹤纹" in cleaned  # 正文应该保留
    
    print("✅ 章节清理测试通过")
    return True


def test_clean_summary():
    """测试概要提取清理"""
    
    raw_summary = """
前情提要如下：

1. 林风意外穿越异世
2. 血触古卷认主
- 初遇神秘势力追杀
* 展现惊人潜力
5、结识苏雨等同伴
• 祭天台上立下誓言

总结：第一章主要讲述了主角的穿越经历。
"""

    cleaned_lines = extract_clean_summary(raw_summary)
    
    print("\n原始概要:")
    print(raw_summary)
    print("\n清理后概要列表:")
    for i, line in enumerate(cleaned_lines, 1):
        print(f"  {i}. {line}")
    
    # 验证清理效果
    assert len(cleaned_lines) == 6
    assert all("•" not in line and "*" not in line for line in cleaned_lines)
    assert "前情提要" not in '\n'.join(cleaned_lines)
    assert "总结" not in '\n'.join(cleaned_lines)
    
    print("✅ 概要清理测试通过")
    return True


def test_edge_cases():
    """测试边缘情况"""
    
    # 测试纯小说内容（不应该被改动）
    pure_novel = """
林风站在祭坛中央，感受着体内气脉的流动。

远处传来钟声，仿佛在召唤着什么。

他深吸一口气，迈步向前。
"""
    
    cleaned = clean_chapter_text(pure_novel)
    # 空行可能会被规范化，但内容应该保持
    assert "林风站在祭坛中央" in cleaned
    assert "远处传来钟声" in cleaned
    
    # 测试空输入
    assert clean_chapter_text("") == ""
    assert extract_clean_summary("") == []
    
    # 测试只有元信息的输入
    meta_only = """
下一章：探索仙门
写作意图：推进剧情
---
===
"""
    assert clean_chapter_text(meta_only).strip() == ""
    
    print("✅ 边缘情况测试通过")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("测试章节输出清理功能")
    print("=" * 60)
    
    test_clean_chapter()
    test_clean_summary()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)
    print("\n功能说明：")
    print("1. clean_chapter_text() - 清理章节中的非小说内容")
    print("   • 移除章节标题、分隔符、下一章预告")
    print("   • 移除写作意图等元信息")
    print("   • 保留纯净的小说正文")
    print("\n2. extract_clean_summary() - 提取干净的概要")
    print("   • 移除编号和符号")
    print("   • 过滤元信息行")
    print("   • 返回纯文本概要列表")
    print("\n现在每个章节都会通过统一的处理流程：")
    print("build_chapter_messages() → API调用 → clean_chapter_text() → 保存")