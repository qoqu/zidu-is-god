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
章间运行时状态 (StatusCard)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StatusCard:
    """章节间的当前状态快照"""
    novel_name: str = ""
    current_chapter: int = 0
    last_updated: str = ""

    # 时间与场景锚点
    current_time: str = ""
    current_location: str = ""

    # 主角当前状态
    protagonist_status: dict = field(default_factory=dict)

    # 人物关系快照
    relationship_snapshot: dict = field(default_factory=dict)

    # 上章结尾钩子
    last_hook: Optional[str] = None
    last_hook_resolved: bool = False

    # 章节类型
    chapter_type: str = "布局章"

    # 本章任务
    chapter_task: str = ""

    # 风险备忘
    active_risks: list = field(default_factory=list)
