# Copyright (C) 2026 创世日记引擎 contributors
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
"""

from typing import Optional
from openai import OpenAI

from app.config import Config


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
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
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

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> dict:
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
