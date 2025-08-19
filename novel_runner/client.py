import os
import time
import json
from typing import List, Dict, Any, Optional

import requests


class BaiduErnieClient:
    """
    Thin client for Baidu ERNIE chat completions.

    - Retrieves and caches access_token using API key and secret key from env vars
    - Provides a simple chat_completions wrapper with retries
    """

    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    CHAT_URL = "https://qianfan.baidubce.com/v2/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        max_retries: int = 5,
        retry_delay_seconds: float = 2.0,
        request_timeout_seconds: float = 0.0,
    ) -> None:
        self.api_key = api_key or os.getenv("BAIDU_API_KEY", "")
        self.secret_key = secret_key or os.getenv("BAIDU_SECRET_KEY", "")
        if not self.api_key:
            raise RuntimeError("需要配置 BAIDU_API_KEY")

        # 若未提供 SECRET 则走直传模式，将 API_KEY 作为访问令牌使用
        self._direct_access_token_mode = not bool(self.secret_key)
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        # Allow override via env, default to generous 300s read timeout for long generations
        if request_timeout_seconds and request_timeout_seconds > 0:
            self.request_timeout_seconds = request_timeout_seconds
        else:
            self.request_timeout_seconds = float(os.getenv("BAIDU_HTTP_TIMEOUT", "300"))

        self._access_token: Optional[str] = None
        self._access_token_expiry_epoch: float = 0.0

    def _now(self) -> float:
        return time.time()

    def _get_access_token(self) -> str:
        # Direct-token mode: 将 BAIDU_API_KEY 直接视为令牌
        if self._direct_access_token_mode:
            self._access_token = self.api_key
            # Treat as long-lived token; force no refresh
            self._access_token_expiry_epoch = self._now() + 365 * 24 * 3600
            return self._access_token

        # OAuth mode: exchange api_key/secret_key for access_token
        if (
            self._access_token
            and self._now() < (self._access_token_expiry_epoch - 60)
        ):
            return self._access_token

        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        response = requests.post(self.TOKEN_URL, params=params, timeout=self.request_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 0)
        if not token:
            raise RuntimeError(f"Failed to obtain access token: {data}")

        self._access_token = token
        self._access_token_expiry_epoch = self._now() + float(expires_in)
        return token

    def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.85,
        top_p: float = 0.9,
        max_tokens: int = 4500,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call chat completions with basic retries.
        Returns parsed JSON response.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if extra_payload:
            payload.update(extra_payload)

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                access_token = self._get_access_token()
                # 先尝试使用 Bearer 头部，其次回退到查询参数
                candidate_requests = [
                    (
                        self.CHAT_URL,
                        {
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "Authorization": f"Bearer {access_token}",
                        },
                    ),
                    (
                        f"{self.CHAT_URL}?access_token={access_token}",
                        {
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                    ),
                ]

                last_status = None
                last_text = None
                for url, headers in candidate_requests:
                    resp = requests.post(
                        url,
                        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                        headers=headers,
                        timeout=(10, self.request_timeout_seconds),
                    )
                    last_status = resp.status_code
                    last_text = resp.text
                    if resp.status_code in (401, 403):
                        # 回退到下一种鉴权方式
                        continue
                    try:
                        resp.raise_for_status()
                    except Exception:
                        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                    data = resp.json()
                    break
                else:
                    # 若两种方式都未通过，则抛出最后一次的详细响应
                    raise RuntimeError(f"HTTP {last_status}: {last_text}")
                if resp.status_code == 429:
                    # rate limit; backoff and retry
                    time.sleep(self.retry_delay_seconds * (2 ** attempt))
                    continue

                # Basic content security and error pattern handling per docs
                error_msg = str(data)
                if "Access token expired" in error_msg:
                    # force refresh
                    self._access_token = None
                    self._access_token_expiry_epoch = 0.0
                    time.sleep(self.retry_delay_seconds * (2 ** attempt))
                    continue
                if "rate limit" in error_msg.lower():
                    time.sleep(self.retry_delay_seconds * (2 ** attempt))
                    continue
                if "content security" in error_msg.lower():
                    # Let caller adjust prompt; still return so they can handle
                    return data
                return data
            except Exception as e:  # noqa: BLE001
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_seconds * (2 ** attempt))
                    continue
                raise


