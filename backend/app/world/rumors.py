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
世界自主演化 — 谣言系统
"""

import random
from typing import Optional


class RumorSystem:
    """
    谣言系统
    
    事件发生后谣言自动传播:
    1. 高影响力角色的行为 → 谣言传播更快更远
    2. 谣言影响角色对彼此的认知
    3. 过时谣言自动消散
    """

    def __init__(self):
        self.active_rumors: list = []  # [Rumor]
        self.all_rumors: list = []

    def generate(self, content: str, source_location: str,
                 source_character: Optional[str] = None,
                 influence_weight: int = 3,
                 accuracy: float = 1.0):
        """生成一条新谣言
        
        Args:
            content: 谣言内容
            source_location: 来源地点
            source_character: 来源角色 (None=世界事件)
            influence_weight: 来源权重, 越高传得越快
            accuracy: 准确度 0~1, 越低越离谱
        """
        radius = {1: "personal", 3: "local", 10: "sect", 30: "nation", 100: "world"}
        spread_speed = min(1.0, influence_weight / 10)

        rumor = {
            "id": f"rumor_{len(self.all_rumors)}",
            "content": content,
            "source_location": source_location,
            "source_character": source_character,
            "accuracy": accuracy,
            "spread_speed": spread_speed,
            "radius": "local" if influence_weight < 10 else "sect" if influence_weight < 30 else "nation",
            "locations_reached": {source_location},  # 已传播到的地点
            "age_days": 0,
            "alive": True,
        }
        self.active_rumors.append(rumor)
        self.all_rumors.append(rumor)
        return rumor

    def tick(self, locations: dict) -> list:
        """每日谣言传播, 返回新传到的地点列表"""
        new_events = []
        for rumor in self.active_rumors:
            if not rumor["alive"]:
                continue
            rumor["age_days"] += 1

            # 按传播速度扩散到相邻地点
            if random.random() < rumor["spread_speed"] * 0.3:
                current_reached = rumor["locations_reached"]
                for loc_id, loc in locations.items():
                    if loc_id not in current_reached:
                        # 概率传播
                        if random.random() < 0.2 * rumor["spread_speed"]:
                            current_reached.add(loc_id)
                            new_events.append(f"谣言\"{rumor['content'][:20]}...\"传到了{loc.name}")

            # 谣言衰减: 7天后消散, 10天后必消
            if rumor["age_days"] > 7 + random.randint(0, 5):
                rumor["alive"] = False

        # 清理过期谣言
        self.active_rumors = [r for r in self.active_rumors if r["alive"]]
        return new_events

    def rumors_at(self, location_id: str) -> list[dict]:
        """某地点当前能听到的谣言"""
        return [
            r for r in self.active_rumors
            if location_id in r["locations_reached"]
        ]

    def rumor_text_for(self, location_id: str) -> str:
        """给 LLM 感知用的谣言文本"""
        rumors = self.rumors_at(location_id)
        if not rumors:
            return ""
        texts = []
        for r in rumors[:3]:  # 最多 3 条
            source = f" ({r['source_character']})" if r['source_character'] else ""
            texts.append(f"  - {r['content']}{source}")
        return "\n".join(texts)
