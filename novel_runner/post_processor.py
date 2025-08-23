"""
章节后处理器 - 清理大模型输出中的非小说内容
"""
import re
from typing import List


def clean_chapter_text(raw_text: str) -> str:
    """
    清理章节文本，移除所有非小说内容
    
    Args:
        raw_text: 大模型原始输出
        
    Returns:
        纯净的小说正文
    """
    if not raw_text:
        return ""
    
    lines = raw_text.strip().split('\n')
    cleaned_lines = []
    
    # 要移除的模式
    remove_patterns = [
        r'^下一章[:：]',  # 下一章预告
        r'^第[一二三四五六七八九十\d]+章',  # 章节标题（数字或中文数字）
        r'^---+$',  # 分隔符
        r'^===+$',  # 分隔符
        r'^\*\*\*+$',  # 分隔符
        r'^【.*】$',  # 带方括号的标题
        r'^写作意图[:：]',  # 写作意图
        r'^\s*$',  # 空行（后续会重新整理）
    ]
    
    # 检测是否为元信息行
    meta_keywords = [
        '下一章', '写作意图', '章节目标', '提示词', '大纲',
        '总结', '概要', 'Chapter', 'CHAPTER', '分隔符'
    ]
    
    for line in lines:
        # 跳过匹配移除模式的行
        should_skip = False
        for pattern in remove_patterns:
            if re.match(pattern, line.strip()):
                should_skip = True
                break
        
        if should_skip:
            continue
        
        # 跳过包含元信息关键词的行（通常在末尾）
        if any(keyword in line for keyword in meta_keywords):
            # 如果这行很短（小于50字符），很可能是元信息
            if len(line.strip()) < 50:
                continue
        
        # 保留正常的小说内容
        cleaned_lines.append(line)
    
    # 重新组合文本，确保段落间有适当空行
    result_lines = []
    prev_empty = False
    
    for line in cleaned_lines:
        if line.strip():
            result_lines.append(line)
            prev_empty = False
        elif not prev_empty:
            # 保留一个空行作为段落分隔
            result_lines.append('')
            prev_empty = True
    
    # 去除末尾的空行
    while result_lines and not result_lines[-1].strip():
        result_lines.pop()
    
    # 特殊处理：如果最后一行看起来像是元信息（很短且包含特定词汇）
    if result_lines:
        last_line = result_lines[-1].strip()
        if len(last_line) < 50:
            # 检查是否包含常见的元信息词汇
            meta_endings = ['。', '写作', '意图', '下章', '下一章', '预告']
            if any(word in last_line for word in meta_endings[1:]):
                # 如果最后一行看起来像元信息，移除它
                result_lines.pop()
    
    return '\n'.join(result_lines)


def extract_clean_summary(raw_summary: str) -> List[str]:
    """
    提取清洁的章节概要列表
    
    Args:
        raw_summary: 大模型生成的原始概要
        
    Returns:
        概要条目列表
    """
    if not raw_summary:
        return []
    
    lines = raw_summary.strip().split('\n')
    summary_items = []
    
    for line in lines:
        # 清理每一行
        cleaned = line.strip()
        
        # 移除编号和符号
        cleaned = re.sub(r'^[\d\-\*\•\.]+\s*', '', cleaned)
        
        # 跳过空行和过短的行
        if len(cleaned) < 5:
            continue
        
        # 跳过元信息
        if any(keyword in cleaned for keyword in ['概要', '提要', '总结', '如下']):
            if len(cleaned) < 20:  # 短的元信息行
                continue
        
        summary_items.append(cleaned)
    
    return summary_items