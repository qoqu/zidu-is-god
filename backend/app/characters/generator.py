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
CharacterGenerator — LLM 从角色设定生成完整的 Character 对象
"""

from typing import Optional
from app.characters.schema import (CharacterRole,
    Character, CharIdentity, CharPersonality, CharMotivation,
    GrowthArc, EmotionalState, Influence,
)
from app.llm.client import LLMClient


CHAR_GEN_SYSTEM_PROMPT = """你是一位小说角色设计师。根据用户给出的角色概念, 生成完整的角色档案。

返回 JSON, 严格按以下 schema:

{
  "identity": {
    "name": "姓名",
    "age": 年龄,
    "gender": "性别",
    "appearance": "外貌描述",
    "occupation": "职业"
  },
  "personality": {
    "traits": ["特质1", "特质2"],
    "speaking_style": "说话风格描述",
    "decision_bias": {"利益": 0.6, "感情": 0.3, "原则": 0.1}
  },
  "motivation": {
    "deep_desire": "深层欲望",
    "short_term_goals": ["短期目标1"],
    "long_term_goal": "长期目标",
    "fear": "恐惧"
  },
  "growth_arc": {
    "starting_state": "起始状态",
    "intended_transformation": "目标转变",
    "current_progress": 0.0
  },
  "initial_location": "初始地点id",
  "skills": {"技能名": 数值},
  "secrets": ["隐藏信息1"]
}

不要输出非 JSON 内容。"""


class CharacterGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def generate(self, character_concept: str, index: int = 0) -> Character:
        """根据角色概念生成 Character 对象"""
        if not character_concept.strip():
            return self._default_character(index)

        try:
            data = self.llm.chat_json(
                system_prompt=CHAR_GEN_SYSTEM_PROMPT,
                user_prompt=f"请根据以下角色设定生成角色档案:\n\n{character_concept}",
            )
        except Exception as e:
            print(f"[CharacterGenerator] LLM 解析失败, 使用默认角色: {e}")
            return self._default_character(index)

        identity_data = data.get("identity", {})
        personality_data = data.get("personality", {})
        motivation_data = data.get("motivation", {})
        arc_data = data.get("growth_arc", {})

        char = Character(
            id=f"char_{index+1:03d}",
            name=identity_data.get("name", f"角色{index+1}"),
            identity=CharIdentity(
                name=identity_data.get("name", f"角色{index+1}"),
                age=identity_data.get("age", 20),
                gender=identity_data.get("gender", ""),
                appearance=identity_data.get("appearance", ""),
                occupation=identity_data.get("occupation", ""),
            ),
            personality=CharPersonality(
                traits=personality_data.get("traits", []),
                speaking_style=personality_data.get("speaking_style", ""),
                decision_bias=personality_data.get("decision_bias", {"利益": 0.5, "感情": 0.3, "原则": 0.2}),
            ),
            motivation=CharMotivation(
                deep_desire=motivation_data.get("deep_desire", ""),
                short_term_goals=motivation_data.get("short_term_goals", []),
                long_term_goal=motivation_data.get("long_term_goal", ""),
                fear=motivation_data.get("fear", ""),
            ),
            growth_arc=GrowthArc(
                starting_state=arc_data.get("starting_state", ""),
                intended_transformation=arc_data.get("intended_transformation", ""),
                current_progress=arc_data.get("current_progress", 0.0),
            ),
        )

        char.emotional_state = EmotionalState(
            arousal_speed=1.0 if "冲动" in str(personality_data.get("traits", [])) else 0.7,
        )
        char.skills = data.get("skills", {})
        char.secrets = data.get("secrets", [])
        char.current_location = data.get("initial_location", "loc_main")

        # ★★★ 根据角色身份初始化影响力
        inf = Influence()
        occ = (identity_data.get("occupation", "") or "").lower()
        title = (identity_data.get("name", "") or "").lower()
        concept = character_concept.lower()

        # 经济维度: 商人/掌柜/富商
        if any(w in occ + concept for w in ["商", "贾", "富", "掌柜", "交易", "财"]):
            inf.economic = 20
            inf.radii["economic"] = "local"
        # 政治维度: 官员/贵族/皇室
        if any(w in occ + title + concept for w in ["掌门", "宗主", "长老", "皇", "王", "官", "主"]):
            inf.political = 25
            inf.radii["political"] = "sect"
        # 武力维度: 将军/战士/护卫
        if any(w in occ + concept for w in ["将", "军", "战斗", "武", "护卫", "兵"]):
            inf.military = 20
            inf.radii["military"] = "local"
        # 知识维度: 学者/导师/炼丹师
        if any(w in occ + concept for w in ["师", "学", "教", "炼丹", "研究", "书"]):
            inf.knowledge = 20
            inf.radii["knowledge"] = "local"
        # 声望维度: 名人/明星/领袖
        if any(w in occ + concept for w in ["名", "星", "领袖", "偶像", "侠"]):
            inf.social = 25
            inf.radii["social"] = "sect"
        # 超凡维度: 修仙者/大能/天才
        if any(w in occ + concept for w in ["天才", "内门", "核心", "精英", "大能"]):
            inf.mystical = 25
            inf.radii["mystical"] = "sect"
        if any(w in occ + concept for w in ["外门", "普通"]):
            inf.mystical = 5

        char.stats.influence = inf

        # ★★★ 根据动机/恐惧/秘密初始化执念
        if char.motivation.deep_desire:
            char.memory.add_obsession(
                content=char.motivation.deep_desire,
                obs_type="goal",
                intensity=0.8,
            )
        if char.motivation.fear:
            char.memory.add_obsession(
                content=char.motivation.fear,
                obs_type="trauma",
                intensity=0.7,
            )
        for secret in char.secrets:
            char.memory.add_obsession(
                content=f"隐藏的秘密: {secret}",
                obs_type="secret",
                intensity=0.6,
            )

        return char

    def _default_character(self, index: int) -> Character:
        char = Character(
            id=f"char_{index+1:03d}",
            name=f"角色{index+1}",
        )
        char.current_location = "loc_main"
        return char

    def generate_batch(self, concepts: list[str]) -> list[Character]:
        """批量生成角色, 并行调用"""
        chars = []
        for i, concept in enumerate(concepts):
            char = self.generate(concept, index=i)
            chars.append(char)
        return chars
