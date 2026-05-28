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
世界自主演化 — 天气系统
"""

import random


class WeatherSystem:
    """
    天气系统 — 每 Tick 自动演化, 影响所有角色行为
    
    天气不是装饰——它直接影响:
    - 体力消耗 (暴雨/酷暑 → 体力消耗增加)
    - 修炼效率 (灵气潮汐 → 修炼加成)
    - 行动可行性 (大雪 → 移动受限)
    - 情绪 (连日阴雨 → 情绪倾向低沉)
    """

    PATTERNS = {
        "晴天": {"temp": 25, "visibility": 1.0, "energy_cost": 1.0, "cultivation_bonus": 1.0, "mood_effect": 0},
        "多云": {"temp": 22, "visibility": 0.9, "energy_cost": 1.0, "cultivation_bonus": 1.0, "mood_effect": 0},
        "小雨": {"temp": 18, "visibility": 0.7, "energy_cost": 1.1, "cultivation_bonus": 0.9, "mood_effect": -0.1},
        "暴雨": {"temp": 15, "visibility": 0.3, "energy_cost": 1.4, "cultivation_bonus": 0.6, "mood_effect": -0.2},
        "大雪": {"temp": -5, "visibility": 0.4, "energy_cost": 1.5, "cultivation_bonus": 0.7, "mood_effect": -0.1},
        "酷暑": {"temp": 38, "visibility": 0.9, "energy_cost": 1.3, "cultivation_bonus": 0.8, "mood_effect": -0.15},
        "灵气潮汐": {"temp": 20, "visibility": 0.9, "energy_cost": 0.8, "cultivation_bonus": 2.5, "mood_effect": 0.2},
        "暴风雨": {"temp": 12, "visibility": 0.2, "energy_cost": 1.6, "cultivation_bonus": 0.5, "mood_effect": -0.25},
    }

    SEASON_WEIGHTS = {
        "春": {"晴天": 0.4, "多云": 0.3, "小雨": 0.2, "灵气潮汐": 0.1},
        "夏": {"晴天": 0.3, "酷暑": 0.3, "暴雨": 0.2, "暴风雨": 0.15, "灵气潮汐": 0.05},
        "秋": {"晴天": 0.35, "多云": 0.3, "小雨": 0.15, "灵气潮汐": 0.15, "大雪": 0.05},
        "冬": {"大雪": 0.4, "晴天": 0.25, "多云": 0.2, "暴风雨": 0.1, "灵气潮汐": 0.05},
    }

    def __init__(self):
        self.current: str = "晴天"
        self.season: str = "春"
        self.days_in_weather: int = 0
        self.history: list = []  # [(day, weather)]

    def tick(self) -> dict:
        """推进一天, 可能变化天气, 返回天气效果"""
        # 天气变化概率: 持续越久越可能变
        change_chance = min(0.1 + self.days_in_weather * 0.05, 0.6)
        if random.random() < change_chance:
            weights = self.SEASON_WEIGHTS.get(self.season, self.SEASON_WEIGHTS["春"])
            self.current = random.choices(
                list(weights.keys()),
                weights=list(weights.values()),
            )[0]
            self.days_in_weather = 0
        else:
            self.days_in_weather += 1

        self.history.append((len(self.history), self.current))
        if len(self.history) > 30:
            self.history.pop(0)

        return self.effects()

    def effects(self) -> dict:
        """当前天气的效果数值"""
        return self.PATTERNS.get(self.current, self.PATTERNS["晴天"]).copy()

    def description(self) -> str:
        return self.current

    def apply_to_character(self, stats) -> str:
        """天气对角色状态的影响 (每 Tick 调用)"""
        fx = self.effects()
        # 体力消耗
        stats.stamina = max(0, int(stats.stamina - (fx["energy_cost"] - 1.0) * 5))
        return self.current
