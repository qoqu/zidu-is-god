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
配置管理
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 从 backend/ 目录加载 .env
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
# 也尝试环境变量（部署场景）
load_dotenv()


class Config:
    # LLM 配置（OpenAI 格式）
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")
    LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
    LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))

    # 模拟配置
    DEFAULT_CHARS_PER_BEAT = 4     # 每 Beat 同时决策的角色数上限
    DEFAULT_BEATS_PER_CHAPTER = 15  # 每章默认 Beat 数
    DEFAULT_CHAPTERS = 5            # 默认总章数

    # 叙事配置
    NARRATOR_MODEL = os.environ.get("NARRATOR_MODEL", "")  # 空=用 LLM_MODEL_NAME
    NARRATOR_TEMPERATURE = float(os.environ.get("NARRATOR_TEMPERATURE", "0.5"))

    # 可配置的魔法数字 (v0.5.0+)
    QUALITY_PASS_THRESHOLD = int(os.environ.get("QUALITY_PASS", "48"))  # 质量门禁及格线
    TENSION_DANGER_WEIGHT = float(os.environ.get("TENSION_DANGER", "0.3"))  # 张力:危险权重
    TENSION_EMOTION_WEIGHT = float(os.environ.get("TENSION_EMOTION", "0.25"))  # 张力:情绪权重
    TENSION_DISTANCE_WEIGHT = float(os.environ.get("TENSION_DISTANCE", "0.12"))  # 张力:距离权重
    PARALLEL_MAX_LINES = int(os.environ.get("PARALLEL_LINES", 5))  # 最大并行线数
    BEATS_PER_POV = int(os.environ.get("BEATS_PER_POV", 3))  # POV切换频率
    BATCH_NARRATE_SIZE = int(os.environ.get("BATCH_NARRATE", 3))  # 叙事批次大小

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置 — 请在 .env 中设置")
        return errors
