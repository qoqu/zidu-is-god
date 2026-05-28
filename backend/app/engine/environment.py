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
环境交互系统 — 角色与世界环境之间的互动
"""

from typing import Optional
from app.engine.events import NarrativeEvent


class EnvironmentInteraction:
    """
    环境交互 — 角色与环境之间的双向影响
    
    - 角色探索/采集/建造/交易 → 改变环境
    - 环境的天气/资源/危险 → 影响角色
    """

    @staticmethod
    def handle_explore(char, target_location: Optional[str], world) -> str:
        """探索当前或指定区域"""
        loc_name = "周围"
        if target_location and target_location in world.locations:
            loc_name = world.locations[target_location].name

        # 探索可能发现资源
        discovery_chance = 0.3
        world_state = world.global_state

        import random
        if random.random() < discovery_chance:
            discoveries = [
                "发现了几株珍稀草药",
                "找到一处隐蔽的修炼宝地",
                "发现了一些前人遗留的痕迹",
                "注意到此处地势险要, 易守难攻",
            ]
            msg = f"{char.name}在{loc_name}探索了一番, {random.choice(discoveries)}"
            char.stats.needs["achievement"] = max(0, char.stats.needs["achievement"] - 5)
        else:
            msg = f"{char.name}在{loc_name}探索了一番, 没有特别发现"
            char.stats.stamina = max(0, char.stats.stamina - 5)

        return msg

    @staticmethod
    def handle_collect(char, resource: str, world) -> str:
        """采集资源"""
        resources = char.stats.items
        resources[resource] = resources.get(resource, 0) + 1
        char.stats.stamina = max(0, char.stats.stamina - 10)
        return f"{char.name}采集到了{resource}"

    @staticmethod
    def handle_observe(char, target: Optional[str], world, weather: dict) -> str:
        """观察环境, 包含天气/环境信息"""
        parts = [f"{char.name}环顾四周"]
        if weather:
            parts.append(f"天气{weather.get('current', '晴')}")
        if target:
            parts.append(f"注意观察{target}")
        return ", ".join(parts)

    @staticmethod
    def weather_effect_on_character(char, weather: dict) -> str:
        """天气对角色的影响"""
        energy_cost = weather.get("energy_cost", 1.0)
        if energy_cost > 1.3:
            char.stats.stamina = max(0, char.stats.stamina - 8)
            return f"恶劣天气让{char.name}消耗了大量体力"
        return ""
