import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


@dataclass
class AIResponse:
    model: str
    content: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "content": self.content,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "error": self.error,
        }


_token_stats: Dict[str, Any] = {
    "total_calls": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "calls_detail": [],
}


class BaiduErnieClient:
    """
    学习自 baidu_ernie45_usage_example.md 的一个轻量封装：
    - 使用 BAIDU_API_KEY 作为 Bearer 令牌调用千帆 Chat Completions
    - 支持 ERNIE 系列的多种模型（非特定版本），参数与示例一致
    - 支持常用参数（temperature/top_p/penalty_score/max_completion_tokens/stop 等）
    - 记录 token 使用统计
    - 返回结构化的 AIResponse

    说明：此实现不支持流式(stream=True)返回。
    """

    API_URL = "https://qianfan.baidubce.com/v2/chat/completions"

    def __init__(self, request_timeout_seconds: int = 120) -> None:
        self.request_timeout_seconds = request_timeout_seconds

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        return dict(_token_stats)

    @staticmethod
    def reset_stats() -> None:
        _token_stats["total_calls"] = 0
        _token_stats["total_input_tokens"] = 0
        _token_stats["total_output_tokens"] = 0
        _token_stats["calls_detail"] = []

    def chat(
        self,
        messages: List[Dict[str, str]],
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
    ) -> AIResponse:
        api_key = os.environ.get("BAIDU_API_KEY")
        if not api_key:
            logger.error("未设置 BAIDU_API_KEY 环境变量，无法调用百度千帆API。")
            return AIResponse(model=model_name, error="Missing BAIDU_API_KEY")

        if stream:
            return AIResponse(model=model_name, error="Streaming not supported in this client")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "penalty_score": penalty_score,
            "parallel_tool_calls": parallel_tool_calls,
            "stream": False,
        }

        # 默认不开启 web_search，允许外部传入覆盖
        if web_search is not None:
            payload["web_search"] = web_search

        # 自动插入 system prompt（若存在且 messages[0] 不是 system）
        if system_prompt:
            if not (messages and messages[0].get("role") == "system"):
                payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

        # 只添加非 None 的参数
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

        # 估算输入 token（粗略）
        try:
            input_text = ""
            if system_prompt:
                input_text += system_prompt + "\n"
            for msg in messages:
                input_text += msg.get("content", "") + "\n"
            estimated_input_tokens = len(input_text.encode("utf-8")) // 2
        except Exception:
            estimated_input_tokens = 0

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug("Baidu raw response: %s", data)

            if "error_code" in data or "error_msg" in data:
                error_code = data.get("error_code")
                error_msg = data.get("error_msg", "Unknown API error")
                logger.error("百度API错误 (Code: %s): %s", error_code, error_msg)
                return AIResponse(model=model_name, error=f"API Error {error_code}: {error_msg}")

            choices = data.get("choices", [])
            if not choices or "message" not in choices[0]:
                logger.error("百度API响应缺少 message 字段: %s", data)
                return AIResponse(model=model_name, error="Response missing message content")

            content = choices[0]["message"].get("content")
            usage = data.get("usage", {})
            finish_reason = choices[0].get("finish_reason")
            logger.info("百度千帆API调用成功，模型: %s，finish_reason: %s", model_name, finish_reason)

            actual_input_tokens = usage.get("prompt_tokens", estimated_input_tokens)
            actual_output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", actual_input_tokens + actual_output_tokens)

            _token_stats["total_calls"] += 1
            _token_stats["total_input_tokens"] += actual_input_tokens
            _token_stats["total_output_tokens"] += actual_output_tokens

            call_detail = {
                "call_id": _token_stats["total_calls"],
                "timestamp": datetime.now().isoformat(),
                "model": model_name,
                "input_tokens": actual_input_tokens,
                "output_tokens": actual_output_tokens,
                "total_tokens": total_tokens,
                "estimated_input": estimated_input_tokens,
                "system_prompt_length": len(system_prompt) if system_prompt else 0,
                "user_content_length": sum(len(msg.get("content", "")) for msg in messages),
            }
            _token_stats["calls_detail"].append(call_detail)

            logger.info(
                "LLM调用#%s: 输入%s tokens, 输出%s tokens, 总计%s tokens",
                _token_stats["total_calls"],
                actual_input_tokens,
                actual_output_tokens,
                total_tokens,
            )

            return AIResponse(
                model=model_name,
                content=content,
                usage=usage,
                finish_reason=finish_reason,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("百度千帆API调用异常: %s", e, exc_info=True)
            return AIResponse(model=model_name, error=str(e))

    def simple_chat(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.01,
        top_p: float = 0.7,
        max_completion_tokens: Optional[int] = None,
    ) -> AIResponse:
        return self.chat_with_prompts(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompts=prompt,
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=max_completion_tokens,
        )

    def chat_with_prompts(
        self,
        model_name: str,
        user_prompts: Union[str, List[str]],
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
    ) -> AIResponse:
        """
        以 system_prompt 和 user_prompts（字符串或字符串列表）作为输入，内部组织 messages 后调用 API。
        默认禁用 web_search（不传即可）。
        """
        # 规范化 user_prompts
        if isinstance(user_prompts, str):
            user_list: List[str] = [user_prompts]
        else:
            user_list = list(user_prompts)

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for up in user_list:
            messages.append({"role": "user", "content": up})

        # 已在 messages 中放入 system，不再通过参数二次注入
        return self.chat(
            messages=messages,
            model_name=model_name,
            system_prompt=None,
            temperature=temperature,
            top_p=top_p,
            penalty_score=penalty_score,
            max_completion_tokens=max_completion_tokens,
            seed=seed,
            stop=stop,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            web_search=web_search,
            response_format=response_format,
            metadata=metadata,
            user=user,
        )


