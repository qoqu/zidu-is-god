# Copyright (C) 2026 Novel World Engine contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
LLM 客户端 — OpenAI SDK 格式，多供应商兼容
包含友好的错误处理
"""

from typing import Optional
from openai import OpenAI
from openai import (
    AuthenticationError, NotFoundError, RateLimitError,
    APITimeoutError, APIConnectionError, APIStatusError,
)

from app.config import Config


class LLMError(Exception):
    """LLM 调用错误的友好包装"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original = original_error
        super().__init__(message)


class LLMClient:
    def __init__(self, config: Config = None):
        cfg = config or Config
        self.api_key = cfg.LLM_API_KEY
        self.base_url = cfg.LLM_BASE_URL
        self.model = cfg.LLM_MODEL_NAME
        self.temperature = cfg.LLM_TEMPERATURE
        self.max_tokens = cfg.LLM_MAX_TOKENS
        self.timeout = cfg.LLM_TIMEOUT

        if not self.api_key:
            raise LLMError(
                "LLM_API_KEY 未配置。\n"
                "请创建 .env 文件并填入你的 API Key:\n"
                "  LLM_API_KEY=sk-your-key-here\n"
                "  LLM_BASE_URL=https://api.openai.com/v1\n"
                "  LLM_MODEL_NAME=gpt-4o-mini"
            )

        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as e:
            raise LLMError(f"无法初始化 LLM 客户端: {e}")

    def _is_retryable(self, e: Exception) -> bool:
        """是否可以重试的错误类型"""
        return isinstance(e, (RateLimitError, APITimeoutError, APIConnectionError,
                              APIStatusError))

    def _call_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """带指数退避重试的 LLM 调用"""
        import time
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if not self._is_retryable(e):
                    raise self._handle_error(e)
                if attempt < max_retries:
                    delay = (2 ** attempt) + (0.1 * __import__('random').random())
                    print(f"  ⏳ LLM 调用失败 ({e.__class__.__name__}), {delay:.0f}s 后重试 ({attempt+1}/{max_retries})...")
                    time.sleep(delay)
        raise self._handle_error(last_error)

    def _handle_error(self, e: Exception) -> LLMError:
        """将 OpenAI SDK 的异常转为友好消息"""
        if isinstance(e, AuthenticationError):
            return LLMError(
                "API Key 认证失败，请检查 LLM_API_KEY 是否正确。\n"
                "  - 是否复制完整？\n"
                "  - 是否有该模型的访问权限？"
            )
        if isinstance(e, NotFoundError):
            return LLMError(
                f"模型 \"{self.model}\" 不存在或当前 API 不支持。\n"
                "请检查 LLM_MODEL_NAME 是否正确。"
            )
        if isinstance(e, RateLimitError):
            return LLMError("API 调用频率过高或已超出配额，请稍后重试。")
        if isinstance(e, APITimeoutError):
            return LLMError(
                f"请求超时 (>{self.timeout}秒)。\n"
                "可以尝试:\n"
                "  - 检查网络连接\n"
                "  - 在 .env 中增大 LLM_TIMEOUT\n"
                "  - 切换为响应更快的模型"
            )
        if isinstance(e, APIConnectionError):
            return LLMError(
                f"无法连接到 {self.base_url}\n"
                "请检查:\n"
                "  - 网络连接是否正常\n"
                "  - LLM_BASE_URL 是否正确"
            )
        if isinstance(e, APIStatusError):
            return LLMError(f"API 返回错误 (HTTP {e.status_code}): {e.response.text[:200]}")
        if isinstance(e, LLMError):
            return e
        return LLMError(f"LLM 调用失败: {e}")

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        def _call():
            kwargs = {
                "model": model or self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            return content or ""
        return self._call_with_retry(_call)

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> dict:
        def _call():
            kwargs = {
                "model": model or self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
            }
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            import json
            return json.loads(content or "{}")
        return self._call_with_retry(_call)
