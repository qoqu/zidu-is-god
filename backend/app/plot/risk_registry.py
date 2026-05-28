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
风险备忘 — 跨章节一致性约束
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskMemo:
    id: str
    description: str
    type: str = "consistency"       # consistency / knowledge / injury / plot
    active_from_chapter: int = 0
    active_until_chapter: Optional[int] = None
    related_chars: list = field(default_factory=list)
    violated: bool = False

    def is_active(self, chapter: int) -> bool:
        if chapter < self.active_from_chapter:
            return False
        if self.active_until_chapter and chapter > self.active_until_chapter:
            return False
        return True


class RiskRegistry:
    """风险备忘注册中心"""

    def __init__(self):
        self.memos: dict[str, RiskMemo] = {}
        self._counter = 0

    def add_memo(
        self,
        description: str,
        type: str = "consistency",
        chapter: int = 0,
        duration: int = 2,
        related_chars: list = None,
    ) -> RiskMemo:
        self._counter += 1
        memo = RiskMemo(
            id=f"RM-{self._counter:03d}",
            description=description,
            type=type,
            active_from_chapter=chapter,
            active_until_chapter=chapter + duration if duration else None,
            related_chars=related_chars or [],
        )
        self.memos[memo.id] = memo
        return memo

    def get_active(self, chapter: int) -> list[RiskMemo]:
        return [m for m in self.memos.values() if m.is_active(chapter) and not m.violated]

    def get_active_descriptions(self, chapter: int) -> list[str]:
        return [m.description for m in self.get_active(chapter)]
