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
质量检查 — 80 分评分体系
"""

from typing import Optional


class QualityChecker:
    """80 分质量检查清单"""

    def __init__(self):
        self.scores = {}

    def check(self, text: str, chapter_num: int = 1) -> dict:
        """
        对文本进行质量评分, 返回 {dimension: score, total: int, passed: bool}
        """
        self.scores = {
            "开头吸引力": self._rate_opening(text),
            "情节推进": self._rate_progression(text, chapter_num),
            "人物塑造": self._rate_characters(text),
            "对话质量": self._rate_dialogue(text),
            "悬念设置": self._rate_hook(text),
            "节奏控制": self._rate_pacing(text),
            "展示而非讲述": self._rate_showing(text),
            "语言质量": self._rate_language(text),
        }
        total = sum(self.scores.values())
        return {
            "scores": self.scores,
            "total": total,
            "max": 80,
            "passed": total >= 48,  # >60%
        }

    def _rate_opening(self, text: str) -> int:
        """前 200 字是否吸引人"""
        opening = text[:200]
        score = 5
        if opening and len(opening) > 50:
            score += 2
        if any(w in opening for w in ["突然", "但是", "然而", "却", "!", "？"]):
            score += 3
        return min(score, 10)

    def _rate_progression(self, text: str, chapter_num: int) -> int:
        """是否有明确的事件推进"""
        score = 5
        # 第1章起评分更高
        if chapter_num <= 1:
            score += 1
        return min(score + len(text) // 500, 10)

    def _rate_characters(self, text: str) -> int:
        """角色是否有区分度"""
        # 检查是否有对话标签或角色名
        char_count = 0
        for line in text.split("\n"):
            if "说" in line or "道" in line or "：" in line:
                char_count += 1
        score = min(3 + char_count, 10)
        return score

    def _rate_dialogue(self, text: str) -> int:
        """对话是否自然"""
        dialogue_lines = sum(1 for c in text if c in ('"', '"', '「', '」'))
        # 平均每 200 字一段对话为佳
        expected = len(text) / 200
        actual = dialogue_lines / 2  # 一对引号算一个对话
        if expected == 0:
            return 5
        ratio = min(actual / expected, 2.0)
        return min(int(5 * ratio) + 2, 10)

    def _rate_hook(self, text: str) -> int:
        """结尾是否有悬念"""
        ending = text[-200:] if len(text) > 200 else text
        hook_words = ["突然", "竟", "却", "?" "？", "!", "!", "发现", "原来"]
        score = 5
        for w in hook_words:
            if w in ending:
                score += 1
        return min(score, 10)

    def _rate_pacing(self, text: str) -> int:
        """节奏是否有变化"""
        paragraphs = text.split("\n\n")
        para_lengths = [len(p) for p in paragraphs if p.strip()]
        if len(para_lengths) < 2:
            return 5
        # 段落长度有变化 = 好节奏
        variation = max(para_lengths) - min(para_lengths)
        score = 5 + min(variation / 100, 5)
        return min(int(score), 10)

    def _rate_showing(self, text: str) -> int:
        """展示而非讲述"""
        tell_words = ["很", "非常", "十分", "特别", "非常地", "生气地", "高兴地", "悲伤地"]
        tell_count = sum(1 for w in tell_words if w in text)
        show_words = ["握紧", "颤抖", "咬", "瞪", "低", "攥紧"]
        show_count = sum(1 for w in show_words if w in text)
        score = 5 + min(show_count * 2 - tell_count, 5)
        return max(min(score, 10), 1)

    def _rate_language(self, text: str) -> int:
        """语言是否干净"""
        ai_marks = ["此外", "然而", "强调的是", "值得注意的是", "总的来说", "综上所述"]
        count = sum(1 for m in ai_marks if m in text)
        score = 10 - count * 2
        return max(score, 1)
