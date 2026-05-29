# Copyright (C) 2026 Novel World Engine contributors
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
角色生命周期 — 故事长了, 角色会下线, 新角色会出现

像真实长篇小说一样:
  - 主角从头到尾都在
  - 配角有自己的故事弧, 结束后可能离开
  - 新角色随着剧情推进自然出现
  - 旧角色偶尔回归客串
"""

from enum import Enum
from typing import Optional
from app.characters.schema import Character, CharIdentity, CharPersonality, CharMotivation
from app.llm.client import LLMClient


class CharLifecycle(Enum):
    ACTIVE = "active"       # 活跃 — 在故事中
    DORMANT = "dormant"     # 休眠 — 暂时离开, 可能回归
    RETIRED = "retired"     # 退役 — 故事弧已完成, 不再回归
    DECEASED = "deceased"  # 死亡 — 剧情死亡, 一般不回归


CHAR_GEN_PROMPT = """你是一位小说角色设计师。根据当前故事的发展, 设计一个新角色。

故事当前概况: {story_context}
已有角色: {existing_chars}
需要新的角色来: {purpose}

返回 JSON:
{{
  "name": "角色名",
  "age": 年龄,
  "occupation": "身份/职业",
  "personality_traits": ["特质1", "特质2", "特质3"],
  "speaking_style": "说话风格",
  "deep_desire": "深层欲望/动机",
  "fear": "恐惧/弱点",
  "skills": {{"技能": 等级(1-100)}},
  "initial_location": "初始所在地"
}}
只返回 JSON。"""


class CharacterPool:
    """
    角色池 — 管理整个故事生命周期中的所有角色

    active_chars: 当前活跃的角色 (参与决策和叙事)
    dormant_chars: 暂时离开的角色 (保留状态, 可回归)
    retired_chars: 故事弧完成的角色 (不再参与)
    
    lifecycle 记录: {char_id: CharLifecycle}
    entry_chapter: {char_id: 首次出场章节}
    exit_chapter: {char_id: 离场章节 (如果有)}
    """

    def __init__(self, initial_chars: list[Character]):
        self.active_chars: list[Character] = list(initial_chars)
        self.dormant_chars: list[Character] = []
        self.retired_chars: list[Character] = []

        self.lifecycle: dict[str, CharLifecycle] = {}
        self.entry_chapter: dict[str, int] = {}
        self.exit_chapter: dict[str, int] = {}

        for char in initial_chars:
            self.lifecycle[char.id] = CharLifecycle.ACTIVE
            self.entry_chapter[char.id] = 1  # 初始角色从第1章开始

        self._chapter = 1
        self._llm: Optional[LLMClient] = None

    def set_llm(self, llm: LLMClient):
        self._llm = llm

    def step(self, chapter: int):
        """每章结束后, 检查是否需要角色轮换"""
        self._chapter = chapter

    # ─── 角色进出 ────────────────────────────────────────

    def mark_dormant(self, char_id: str, at_chapter: int):
        """角色暂时离开故事"""
        for pool in [self.active_chars]:
            for c in pool:
                if c.id == char_id:
                    pool.remove(c)
                    self.dormant_chars.append(c)
                    self.lifecycle[char_id] = CharLifecycle.DORMANT
                    self.exit_chapter[char_id] = at_chapter
                    return

    def mark_deceased(self, char_id: str, at_chapter: int, cause: str = ""):
        for pool in [self.active_chars, self.dormant_chars]:
            for ch in pool[:]:
                if ch.id == char_id:
                    pool.remove(ch)
                    self.retired_chars.append(ch)
                    self.lifecycle[char_id] = CharLifecycle.DECEASED
                    self.exit_chapter[char_id] = at_chapter
                    ch._death_cause = cause
                    return

    def mark_retired(self, char_id: str, at_chapter: int):
        """角色故事弧完成, 永久离开"""
        for pool in [self.active_chars, self.dormant_chars]:
            for c in pool[:]:
                if c.id == char_id:
                    pool.remove(c)
                    self.retired_chars.append(c)
                    self.lifecycle[char_id] = CharLifecycle.RETIRED
                    self.exit_chapter[char_id] = at_chapter
                    return

    def revive(self, char_id: str, force: bool = False) -> bool:
        if self.lifecycle.get(char_id) == CharLifecycle.DECEASED and not force:
            return False
        pools = [self.dormant_chars]
        if force:
            pools.append(self.retired_chars)
        for pool in pools:
            for c in pool[:]:
                if c.id == char_id:
                    pool.remove(c)
                    self.active_chars.append(c)
                    self.lifecycle[char_id] = CharLifecycle.ACTIVE
                    return True
        return False

    def generate_new(self, story_context: str, existing_chars: list,
                     purpose: str = "给故事带来新的冲突") -> Optional[Character]:
        """生成一个新角色并加入活跃池"""
        if not self._llm:
            return None

        existing_names = ", ".join(c.name for c in existing_chars if hasattr(c, 'name'))
        prompt = CHAR_GEN_PROMPT.format(
            story_context=story_context[:1000],
            existing_chars=existing_names[:200],
            purpose=purpose,
        )

        try:
            data = self._llm.chat_json("设计一个新角色", prompt)
            if not data:
                return None

            i = len(self.entry_chapter) + 1
            char = Character(
                id=f"ngen_{i:04d}",
                name=data.get("name", f"新角色{i}"),
                identity=CharIdentity(
                    name=data.get("name", f"新角色{i}"),
                    age=data.get("age", 20),
                    occupation=data.get("occupation", ""),
                ),
                personality=CharPersonality(
                    traits=data.get("personality_traits", []),
                    speaking_style=data.get("speaking_style", ""),
                ),
                motivation=CharMotivation(
                    deep_desire=data.get("deep_desire", ""),
                    fear=data.get("fear", ""),
                ),
            )
            char.skills = data.get("skills", {})
            char.current_location = data.get("initial_location", "")

            self.active_chars.append(char)
            self.lifecycle[char.id] = CharLifecycle.ACTIVE
            self.entry_chapter[char.id] = self._chapter

            return char
        except Exception as e:
            return None

    # ─── 查询 ─────────────────────────────────────────────

    def get_active(self) -> list[Character]:
        return self.active_chars

    def all_chars(self) -> list[Character]:
        return self.active_chars + self.dormant_chars + self.retired_chars

    def summary(self) -> str:
        lines = [f"活跃: {len(self.active_chars)} 人"]
        for c in self.active_chars:
            ec = self.entry_chapter.get(c.id, 1)
            lines.append(f"  {c.name} (第{ec}章出场)")
        if self.dormant_chars:
            lines.append(f"休眠: {len(self.dormant_chars)} 人")
            for c in self.dormant_chars:
                ec = self.entry_chapter.get(c.id, 1)
                lines.append(f"  {c.name} (第{ec}章出场, 第{self.exit_chapter.get(c.id,'?')}章离开)")
        if self.retired_chars:
            lines.append(f"退役: {len(self.retired_chars)} 人")
        return "\n".join(lines)
