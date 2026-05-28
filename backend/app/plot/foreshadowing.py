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
伏笔/悬念池
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Foreshadowing:
    """一条伏笔或悬念"""
    id: str
    type: str = "信息"               # 信息/危机/谜题/反转/情感/道具
    description: str = ""
    setup_chapter: int = 0
    setup_detail: str = ""
    reveal_chapter: Optional[int] = None
    actual_reveal_chapter: Optional[int] = None
    status: str = "unrevealed"       # unrevealed / in_progress / revealed / abandoned
    importance: int = 3              # 1-5
    related_chars: list = field(default_factory=list)

    def is_overdue(self, current_chapter: int) -> bool:
        if self.reveal_chapter and current_chapter > self.reveal_chapter and self.status == "unrevealed":
            return True
        return False


@dataclass
class Hook:
    """章节结尾钩子"""
    id: str
    chapter: int
    type: str = "信息钩子"           # 信息钩子/危机钩子/谜题钩子/反转钩子
    content: str = ""
    resolved_in_chapter: Optional[int] = None
    related_foreshadowing: Optional[str] = None


class ForeshadowingPool:
    """伏笔/悬念/钩子管理中心"""

    def __init__(self):
        self.foreshadowings: dict[str, Foreshadowing] = {}
        self.hooks: dict[str, Hook] = {}
        self._counter = 0

    def add_foreshadowing(
        self,
        description: str,
        type: str = "信息",
        setup_chapter: int = 0,
        reveal_chapter: Optional[int] = None,
        importance: int = 3,
    ) -> Foreshadowing:
        self._counter += 1
        fs = Foreshadowing(
            id=f"FS-{self._counter:03d}",
            type=type,
            description=description,
            setup_chapter=setup_chapter,
            reveal_chapter=reveal_chapter,
            importance=importance,
        )
        self.foreshadowings[fs.id] = fs
        return fs

    def add_hook(self, chapter: int, type: str, content: str) -> Hook:
        self._counter += 1
        hook = Hook(
            id=f"HK-{self._counter:03d}",
            chapter=chapter,
            type=type,
            content=content,
        )
        self.hooks[hook.id] = hook
        return hook

    def get_unrevealed(self) -> list[Foreshadowing]:
        return [f for f in self.foreshadowings.values() if f.status == "unrevealed"]

    def get_overdue(self, current_chapter: int) -> list[Foreshadowing]:
        return [f for f in self.foreshadowings.values() if f.is_overdue(current_chapter)]

    def get_for_chapter(self, chapter: int) -> dict:
        """获取本章需要处理的伏笔（该设的+该收的+该提一嘴的）"""
        to_set = [f for f in self.foreshadowings.values() if f.setup_chapter == chapter]
        to_reveal = [f for f in self.foreshadowings.values()
                     if f.reveal_chapter == chapter and f.status == "unrevealed"]
        to_mention = [f for f in self.foreshadowings.values()
                      if f.status == "unrevealed" and f.importance >= 4]
        return {"to_set": to_set, "to_reveal": to_reveal, "to_mention": to_mention}

    def mark_revealed(self, fs_id: str, chapter: int):
        if fs_id in self.foreshadowings:
            self.foreshadowings[fs_id].status = "revealed"
            self.foreshadowings[fs_id].actual_reveal_chapter = chapter
