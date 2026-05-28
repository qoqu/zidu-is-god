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
情绪曲线追踪
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChapterEmotionRecord:
    chapter: int
    emotion_label: str               # 甜/虐/暖/冷/燃/抑/疑/松
    intensity: int = 5               # 1-10
    curve_type: str = "上升"         # 上升/下降/持平/转折
    dominant_char_emotions: dict = field(default_factory=dict)


class EmotionCurveTracker:
    """全书情绪曲线追踪"""

    def __init__(self):
        self.records: list[ChapterEmotionRecord] = []

    def add_record(self, record: ChapterEmotionRecord):
        self.records.append(record)

    def get_latest(self) -> Optional[ChapterEmotionRecord]:
        return self.records[-1] if self.records else None

    def suggest_next_chapter_emotion(self, chapter_num: int) -> str:
        """基于已有曲线和章节位置, 建议情绪基调"""
        # 第1章默认"燃"
        if chapter_num == 1:
            return "燃"

        # 关键转折章
        if chapter_num in (3, 5):
            return "燃"

        # 基于最后两章
        if len(self.records) < 2:
            return "燃"

        last_two = [r.emotion_label for r in self.records[-2:]]

        # 回避连续相同
        if last_two[0] == last_two[1]:
            switch_map = {
                "燃": "抑", "抑": "疑", "疑": "燃",
                "甜": "虐", "虐": "暖", "暖": "冷",
                "冷": "松", "松": "燃",
            }
            return switch_map.get(last_two[0], "燃")

        return "燃"
