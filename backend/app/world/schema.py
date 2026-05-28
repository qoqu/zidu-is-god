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
世界模型 — 数据模型
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Location:
    id: str
    name: str
    description: str = ""
    parent_id: Optional[str] = None
    chars_present: list = field(default_factory=list)  # character ids
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "chars_present": self.chars_present,
            "properties": self.properties,
        }


@dataclass
class Faction:
    id: str
    name: str
    description: str = ""
    members: list = field(default_factory=list)
    relations: dict = field(default_factory=dict)


@dataclass
class WorldRule:
    name: str
    description: str
    category: str = "general"


@dataclass
class Timeline:
    current_time: str = ""
    calendar: str = ""
    chapter_time_map: dict = field(default_factory=dict)


@dataclass
class Item:
    id: str
    name: str
    description: str = ""
    owner: Optional[str] = None
    properties: dict = field(default_factory=dict)


@dataclass
class World:
    id: str = ""
    name: str = ""
    description: str = ""
    locations: dict = field(default_factory=dict)
    factions: dict = field(default_factory=dict)
    rules: list = field(default_factory=list)
    timeline: Timeline = field(default_factory=Timeline)
    global_state: dict = field(default_factory=dict)
    items: dict = field(default_factory=dict)
    beats_since_last_peak: int = 0

    # ★★★ 时间推进表
    TIME_MAP = {
        0: "清晨", 1: "上午", 2: "正午", 3: "下午", 4: "黄昏", 5: "入夜",
        6: "深夜", 7: "凌晨",
    }
    _time_slot: int = 0

    def advance_time(self, beats: int = 1):
        """每 Beat 推进时间: 1 Beat ≈ 半个时辰"""
        self._time_slot += beats
        slot = self._time_slot % 8
        day = self._time_slot // 8
        time_str = self.TIME_MAP.get(slot, "白天")
        self.timeline.current_time = f"第{day+1}天·{time_str}"

    def get_present_chars(self, location_id: str) -> list:
        loc = self.locations.get(location_id)
        return loc.chars_present if loc else []

    def move_char(self, char_id: str, from_loc: Optional[str], to_loc: str):
        if from_loc and from_loc in self.locations:
            loc = self.locations[from_loc]
            if char_id in loc.chars_present:
                loc.chars_present.remove(char_id)
        if to_loc in self.locations:
            self.locations[to_loc].chars_present.append(char_id)

    # ★★★ 冲突管理
    def register_conflict(self, char_a: str, char_b: str, description: str):
        conflicts = self.global_state.setdefault("unresolved_conflicts", [])
        # 去重: 同一对人只保留一条
        existing = [c for c in conflicts if {c["a"], c["b"]} == {char_a, char_b}]
        if not existing:
            conflicts.append({"a": char_a, "b": char_b, "desc": description, "escalated": False})

    def resolve_conflict(self, char_a: str, char_b: str):
        conflicts = self.global_state.get("unresolved_conflicts", [])
        self.global_state["unresolved_conflicts"] = [
            c for c in conflicts if {c["a"], c["b"]} != {char_a, char_b}
        ]

    def escalate_conflict(self):
        """将最老的未升级冲突标记为已升级（提升张力用）"""
        conflicts = self.global_state.get("unresolved_conflicts", [])
        for c in conflicts:
            if not c.get("escalated"):
                c["escalated"] = True
                break

    def get_unresolved_conflicts(self) -> list:
        return self.global_state.get("unresolved_conflicts", [])

    def count_escalated_conflicts(self) -> int:
        return sum(1 for c in self.global_state.get("unresolved_conflicts", []) if c.get("escalated"))

    def apply_event(self, event):
        delta = getattr(event, "world_delta", None) or {}
        for key, value in delta.items():
            if key.startswith("global."):
                self.global_state[key[7:]] = value
