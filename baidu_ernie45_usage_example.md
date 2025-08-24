def call_baidu_chat_api(
    messages: List[Dict],
    model_name: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.01,
    top_p: float = 0.7,
    penalty_score: float = 1.0,
    max_completion_tokens: Optional[int] = None,
    seed: Optional[int] = None,
    stop: Optional[List[str]] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    tools: Optional[list] = None,
    tool_choice: Optional[dict] = None,
    parallel_tool_calls: bool = True,
    web_search: Optional[dict] = None,
    response_format: Optional[dict] = None,
    metadata: Optional[dict] = None,
    user: Optional[str] = None,
    stream: bool = False,
    stream_options: Optional[dict] = None,
) -> Optional[AIResponse]:
    """
    通用百度千帆ERNIE 4.0/4.5 Turbo API调用，支持所有文本生成参数。
    参数说明见官方文档：https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Blfmc9do2
    """
    global _token_stats
    
    API_KEY = os.environ.get("BAIDU_API_KEY")
    if not API_KEY:
        logger.error("❌ 未设置 BAIDU_API_KEY 环境变量，无法调用百度千帆API。")
        return None
    url = "https://qianfan.baidubce.com/v2/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "penalty_score": penalty_score,
        "parallel_tool_calls": parallel_tool_calls,
        "stream": stream,
        "web_search": {
            "enable": config.WEB_SEARCH_ENABLED,
            "enable_citation": config.WEB_SEARCH_ENABLED,
            "enable_trace": config.WEB_SEARCH_ENABLED,
            "enable_status": config.WEB_SEARCH_ENABLED
        }
    }
    # 如果用户传了web_search，则覆盖
    if web_search is not None:
        payload["web_search"] = web_search
    # 只添加非None参数
    if system_prompt:
        # 如果messages没有system，自动插入
        if not (messages and messages[0].get("role") == "system"):
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages
    if max_completion_tokens is not None:
        payload["max_completion_tokens"] = max_completion_tokens
    if seed is not None:
        payload["seed"] = seed
    if stop is not None:
        payload["stop"] = stop
    if frequency_penalty is not None:
        payload["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        payload["presence_penalty"] = presence_penalty
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if response_format is not None:
        payload["response_format"] = response_format
    if metadata is not None:
        payload["metadata"] = metadata
    if user is not None:
        payload["user"] = user
    if stream_options is not None:
        payload["stream_options"] = stream_options
    try:
        # 计算输入Token数量（估算）
        input_text = ""
        if system_prompt:
            input_text += system_prompt + "\n"
        for msg in messages:
            input_text += msg.get("content", "") + "\n"
        
        # 简单的Token估算（中文约1.5字符=1token，英文约4字符=1token）
        estimated_input_tokens = len(input_text.encode('utf-8')) // 2  # 粗略估算
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"🤖 百度千帆API原始响应: {data}")
        if "error_code" in data or "error_msg" in data:
            error_code = data.get("error_code")
            error_msg = data.get("error_msg", "Unknown API error")
            logger.error(f"❌ 百度API错误 (Code: {error_code}): {error_msg}")
            return AIResponse(model=model_name, error=f"API Error {error_code}: {error_msg}")
        
        choices = data.get("choices", [])
        if not choices or "message" not in choices[0]:
            logger.error(f"❌ 百度API响应缺少 message 字段: {data}")
            return AIResponse(model=model_name, error="Response missing message content")
        
        content = choices[0]["message"].get("content")
        usage = data.get("usage", {})
        finish_reason = choices[0].get("finish_reason")
        logger.info(f"✅ 百度千帆API调用成功，模型: {model_name}，finish_reason: {finish_reason}")
        
        # 提取实际Token使用量
        actual_input_tokens = usage.get("prompt_tokens", estimated_input_tokens)
        actual_output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", actual_input_tokens + actual_output_tokens)
        
        # 更新全局统计
        _token_stats["total_calls"] += 1
        _token_stats["total_input_tokens"] += actual_input_tokens
        _token_stats["total_output_tokens"] += actual_output_tokens
        
        # 记录详细信息
        call_detail = {
            "call_id": _token_stats["total_calls"],
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "input_tokens": actual_input_tokens,
            "output_tokens": actual_output_tokens,
            "total_tokens": total_tokens,
            "estimated_input": estimated_input_tokens,
            "system_prompt_length": len(system_prompt) if system_prompt else 0,
            "user_content_length": sum(len(msg.get("content", "")) for msg in messages)
        }
        _token_stats["calls_detail"].append(call_detail)
        
        # 记录Token使用日志
        logger.info(f"🔢 LLM调用#{_token_stats['total_calls']}: 输入{actual_input_tokens}tokens, 输出{actual_output_tokens}tokens, 总计{total_tokens}tokens")
        
        return AIResponse(
            model=model_name,
            content=content,
            usage=usage,
            finish_reason=finish_reason
        )
    except Exception as e:
        logger.error(f"❌ 百度千帆API调用异常: {e}", exc_info=True)
        return AIResponse(model=model_name, error=str(e))
