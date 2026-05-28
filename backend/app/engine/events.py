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
叙事引擎 — 事件数据模型
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NarrativeEvent:
    """一个结构化的叙事事件"""
    beat_number: int
    chapter_number: int
    time: str = ""
    location: str = ""
    agent_id: str = ""
    action_type: str = ""        # DIALOGUE / ACT / INNER / OBSERVE / WAIT
    target_id: Optional[str] = None
    content: str = ""
    outcome: str = ""
    importance: int = 3          # 1-5
    tension_delta: float = 0.0
    world_delta: dict = field(default_factory=dict)
    because: str = ""            # 因为什么 (前因)
    therefore: list = field(default_factory=list)  # 导致了什么 (后果)

    def is_positive(self) -> bool:
        return "成功" in self.outcome or self.action_type == "INNER" and "喜悦" in self.content

    def is_threatening(self) -> bool:
        return "受伤" in self.outcome or "威胁" in self.content

    def is_loss(self) -> bool:
        return "失去" in self.outcome or "失败" in self.outcome

    def is_surprising(self) -> bool:
        return self.importance >= 4


@dataclass
class BeatLog:
    """一轮 Beat 产生的全部事件"""
    beat_number: int
    chapter_number: int
    events: list = field(default_factory=list)    # [NarrativeEvent]
    pre_tension: float = 0.0
    post_tension: float = 0.0
    catalyst_injected: Optional[str] = None       # 本 Beat 注入的催化剂类型


@dataclass
class ChapterBlueprint:
    """PlotDirector 每章开始前生成的蓝图"""
    chapter_number: int
    title_hint: str = ""
    target_tension_curve: list = field(default_factory=list)  # [float]
    milestones: dict = field(default_factory=dict)            # {milestone_type: deadline_beat_ratio}
    required_satisfaction: list = field(default_factory=list)  # [str]
    target_emotion_label: str = "燃"
    target_emotion_intensity: int = 5
    active_risk_constraints: list = field(default_factory=list)  # [str]
    foreshadowing_to_set: list = field(default_factory=list)     # [str]
    foreshadowing_to_reveal: list = field(default_factory=list)  # [str]


@dataclass
class ChapterSnapshot:
    """
    章节快照 — 支持版本回滚
    
    每章完成后保存一份完整快照, 包含:
    - 世界状态
    - 所有角色的状态/记忆/关系
    - 事件日志
    
    当后续章节出现问题, 可以回滚到任意版本。
    """
    chapter: int
    version: int
    timestamp: str = ""
    world_state: dict = field(default_factory=dict)
    character_states: dict = field(default_factory=dict)
    event_log_summary: str = ""


class SnapshotManager:
    """
    快照管理器 — 版本控制
    
    用法:
        sm = SnapshotManager()
        sm.save(chapter=3, world=world, characters=chars)
        sm.list_versions(chapter=3)
        sm.rollback(chapter=3, version=1)  # 恢复到版本1
    """

    def __init__(self, storage_path: str = ""):
        import os
        self._snapshots: dict = {}  # {(chapter, version): ChapterSnapshot}
        self._storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), '../../data/snapshots'
        )
        os.makedirs(self._storage_path, exist_ok=True)

    def save(self, chapter: int, world, characters: list):
        """
        保存当前状态的快照
        """
        import json
        from datetime import datetime

        versions = [k for k in self._snapshots if k[0] == chapter]
        version = max([v[1] for v in versions] + [0]) + 1

        snapshot = ChapterSnapshot(
            chapter=chapter,
            version=version,
            timestamp=datetime.now().isoformat(),
            world_state={
                "locations": {k: v.name for k, v in world.locations.items()},
                "time": world.timeline.current_time,
                "global_state": dict(world.global_state),
            },
            character_states={
                c.id: {
                    "name": c.name,
                    "location": c.current_location,
                    "hp": c.stats.hp,
                    "stamina": c.stats.stamina,
                    "wealth": c.stats.wealth,
                    "cultivation": c.stats.cultivation,
                    "injuries": len(c.stats.injuries),
                    "memory_count": c.memory.count()["total"],
                    "obsessions": [o["content"][:40] for o in c.memory.obsessions],
                }
                for c in characters
            },
        )
        key = (chapter, version)
        self._snapshots[key] = snapshot
        
        # 写入文件
        import json
        import os; fp = os.path.join(self._storage_path, f"ch{chapter}_v{version}.json")
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                "chapter": chapter,
                "version": version,
                "timestamp": snapshot.timestamp,
                "world_state": snapshot.world_state,
                "character_states": snapshot.character_states,
            }, ensure_ascii=False, indent=2))

        return version

    def list_versions(self, chapter: int) -> list[dict]:
        """
        列出某章的所有版本
        """
        versions = [v for k, v in self._snapshots.items() if k[0] == chapter]
        versions.sort(key=lambda x: x.version)
        return [
            {"version": v.version, "timestamp": v.timestamp,
             "char_count": len(v.character_states)}
            for v in versions
        ]

    def rollback(self, chapter: int, version: int) -> dict:
        """
        获取指定版本的快照数据 (用于恢复)
        返回 world_state 和 character_states
        """
        key = (chapter, version)
        snap = self._snapshots.get(key)
        if not snap:
            # 尝试从文件加载
            import json, os
            import os; fp = os.path.join(self._storage_path, f"ch{chapter}_v{version}.json")
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
            return {}
        return {
            "world_state": snap.world_state,
            "character_states": snap.character_states,
        }
