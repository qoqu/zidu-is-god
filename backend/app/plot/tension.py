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
张力计算模型
"""

from app.world.schema import World
from app.characters.schema import Character


def calculate_tension(
    world: World,
    scene: dict,
    characters: list[Character],
    chapter_progress: float,
) -> float:
    """
    计算当前叙事张力 0~1
    """
    if not characters:
        return 0.3

    # 1. 冲突数量 (已升级的冲突权重更高)
    conflicts = world.get_unresolved_conflicts()
    escalated = world.count_escalated_conflicts()
    conflict_score = min((len(conflicts) * 0.12 + escalated * 0.15), 0.6)

    clash_present = 0.0
    if scene:
        char_ids = set(scene.get("present_char_ids", []))
        for c in conflicts:
            if c["a"] in char_ids and c["b"] in char_ids:
                clash_present = 0.25  # 有冲突的双方同场

    # 2. 角色危险程度
    danger = sum(c.get_danger_level() for c in characters) / max(len(characters), 1)

    # 3. 情感强度 (基于角色的 arousal)
    emotional = sum(
        abs(c.emotional_state.arousal) for c in characters
    ) / max(len(characters), 1)
    emotional = min(emotional, 0.5)

    # 4. 距上次高潮的 Beat 数
    distance = min(world.beats_since_last_peak / 4, 1.0) * 0.12

    tension = (
        conflict_score +
        clash_present +
        danger * 0.2 +
        emotional * 0.25 +
        distance
    )
    return min(tension, 1.0)


def suggest_target_tension(chapter_num: int, chapter_progress: float) -> float:
    """建议的目标张力值 0~1"""
    import math
    base = 0.2 + (chapter_num - 1) * 0.08
    peak_boost = math.sin(chapter_progress * math.pi) * 0.25
    return min(base + peak_boost, 1.0)
