# 百度ERNIE API文档

## API配置

### 环境变量
```bash
BAIDU_API_KEY=你的API_KEY
```

### 端点配置
- **基础URL**: https://aip.baidubce.com
- **Token端点**: /oauth/2.0/token
- **Chat端点**: https://qianfan.baidubce.com/v2/chat/completions

## 模型选择策略

### 模型映射
```python
MODEL_MAPPING = {
    "story_telling": "ernie-x1-turbo-32k",     # 故事创作
    "life_thinking": "ernie-4.0-turbo-8k",     # 人生思考
    "tech_exploration": "ernie-x1-8k",         # 科技探索
    "food_culture": "ernie-x1-turbo-32k",      # 美食文化
    "travel_notes": "ernie-x1-turbo-32k"       # 旅行游记
}
```

### 模型特点
- **ernie-x1-turbo-32k**: 长文本，创意写作
- **ernie-4.0-turbo-8k**: 深度思考，哲理分析
- **ernie-x1-8k**: 技术内容，专业分析

## 提示词模板

### 童话故事模板
```python
prompt = f"""
你是一位优秀的童话故事作家，请创作一个关于"{topic}"的温馨童话故事。

要求：
1. 故事要有起承转合，情节生动有趣
2. 包含正面的价值观和教育意义
3. 语言温馨优美，适合所有年龄段阅读
4. 字数要求：2500-3000字
5. 分成6-8个段落，每段300-400字

输出JSON格式...
"""
```

### 人生思考模板
```python
prompt = f"""
你是一位富有哲思的作家，请就"{topic}"这个主题进行深入思考和探讨。

要求：
1. 有独特的观点和深刻的见解
2. 结合生活实例，引发读者共鸣
3. 文字优美流畅，富有哲理
4. 字数要求：2500-3000字
5. 包含引言、3-4个核心观点、结语

输出JSON格式...
"""
```

## 参数配置

### 基础参数
```python
{
    "model": "模型名称",
    "messages": [
        {"role": "user", "content": "提示词"}
    ],
    "temperature": 0.8,  # 创意度
    "top_p": 0.9,        # 多样性
    "max_tokens": 4000,  # 最大生成长度
    "stream": False      # 非流式输出
}
```

### 参数调优建议

#### 故事创作
- temperature: 0.8-0.9（更有创意）
- top_p: 0.9-0.95
- max_tokens: 4000

#### 技术文章
- temperature: 0.5-0.7（更准确）
- top_p: 0.8-0.9
- max_tokens: 3000

#### 哲理思考
- temperature: 0.7-0.8（平衡）
- top_p: 0.85-0.9
- max_tokens: 3500

## JSON输出格式

### 童话故事
```json
{
    "title": "故事标题",
    "subtitle": "副标题",
    "introduction": "引言",
    "paragraphs": ["段落1", "段落2", ...],
    "highlights": ["精彩片段1", "精彩片段2"],
    "moral": "故事寓意",
    "conclusion": "结语"
}
```

### 人生思考
```json
{
    "title": "文章标题",
    "subtitle": "副标题",
    "quote": "名言引用",
    "introduction": "导语",
    "paragraphs": ["段落1", "段落2", ...],
    "insights": ["观点1", "观点2", ...],
    "conclusion": "结语"
}
```

## 错误处理

### 常见错误
```python
# Token过期
if "Access token expired" in error_message:
    refresh_token()

# 请求频率限制
if "rate limit" in error_message:
    time.sleep(1)
    retry_request()

# 内容安全
if "content security" in error_message:
    modify_prompt()
```

### 重试机制
```python
MAX_RETRIES = 3
RETRY_DELAY = 2

for attempt in range(MAX_RETRIES):
    try:
        response = call_api()
        break
    except Exception as e:
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
        else:
            use_fallback_content()
```

## 内容优化策略

### 提示词优化
1. **明确指令**: 清晰说明任务要求
2. **格式规范**: 指定输出格式
3. **字数控制**: 明确字数范围
4. **风格指导**: 说明写作风格

### 质量控制
1. **结构检查**: 验证JSON结构完整性
2. **字数验证**: 确保满足字数要求
3. **内容审核**: 过滤敏感内容
4. **格式美化**: 优化段落分布

## 平台价值观集成

### 核心价值观
```python
PLATFORM_VALUES = """
【微信平台核心价值观】
=== 我们鼓励倡导的内容 ===
1. 以传递知识、分享经验和展示个人观点为主要目的
2. 有价值、有深度的原创内容
3. 提供良好的阅读体验
4. 具有启发性、教育性或娱乐性质

=== 我们坚决避免的内容 ===
1. 违反法律法规的内容
2. 不实或误导性信息
3. 违背公序良俗的内容
4. 纯营销性质的内容
"""
```

### 集成方式
在每个提示词模板中都包含平台价值观，确保生成内容符合要求。

## 最佳实践

### 提高生成质量
1. 使用具体详细的提示词
2. 提供示例和参考
3. 分步骤要求
4. 多次迭代优化

### 性能优化
1. 缓存access_token
2. 批量处理请求
3. 异步调用API
4. 使用连接池

### 成本控制
1. 选择合适的模型
2. 控制生成长度
3. 避免重复请求
4. 实施请求限流

## 备用方案

### 模板内容生成
当API不可用时，使用预定义模板生成内容：

```python
def generate_fallback_content(category, topic):
    """生成备用内容"""
    templates = load_templates(category)
    content = fill_template(templates, topic)
    return format_as_json(content)
```

### 内容库系统
维护高质量内容库，在API失败时提供备选内容。