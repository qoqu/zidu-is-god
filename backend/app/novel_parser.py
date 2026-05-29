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

"""小说解析器"""

import re
import os
from typing import Optional
from app.llm.client import LLMClient, LLMError
from app.world.schema import World, Location, Faction, WorldRule
from app.characters.schema import Character, CharIdentity, CharPersonality, CharMotivation, Influence
from app.timeline import Timeline, TimelineNode

class NovelParser:
    """
    小说解析器 — 从 txt 文件提取结构化世界

    用法:
      np = NovelParser(llm)
      result = np.parse("novel.txt")
      # result.world  → World 对象
      # result.characters → [Character, ...]
      # result.timeline → Timeline 对象
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def parse(self, filepath: str, max_chapters: int = 50) -> dict:
        """
        解析一本小说

        Args:
            filepath: txt 文件路径
            max_chapters: 最多解析章节数

        Returns:
            {"world": World, "characters": [Character], "timeline": Timeline}
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            full_text = f.read()

        # 按章节分割
        chapters = self._split_chapters(full_text)
        chapters = chapters[:max_chapters]
        sample = full_text[:8000]  # 用于提取世界观和角色的样本

        print(f"📖 解析小说: {len(chapters)} 章, {len(full_text)} 字")

        # 1. 提取世界观
        print("  🌍 提取世界观...")
        world = self._extract_world(sample, chapters)

        # 2. 提取角色
        print("  👤 提取角色...")
        characters = self._extract_characters(sample)

        # 3. 提取时间轴
        print("  📅 提取时间轴...")
        timeline = self._extract_timeline(chapters, characters)

        # 构建角色名→id 映射
        char_name_to_id = {c.name: c.id for c in characters}

        # 给时间轴节点补充角色 id
        for node in timeline.nodes:
            node.chars_present = [
                char_name_to_id.get(name, name)
                for name in node.chars_present
                if name in char_name_to_id
            ]

        print(f"  ✅ 完成: {len(characters)} 角色, {len(timeline.nodes)} 章时间轴")

        return {
            "world": world,
            "characters": characters,
            "timeline": timeline,
        }

    def _split_chapters(self, text: str) -> list[dict]:
        """按"第X章"分割文本"""
        pattern = r'(第\s*\d+\s*[章回部])'
        splits = re.split(pattern, text)
        chapters = []
        current_title = "前言"
        current_text = ""

        for part in splits:
            part = part.strip()
            if re.match(pattern, part):
                if current_text:
                    chapters.append({"title": current_title, "text": current_text[:3000]})
                current_title = part
                current_text = ""
            else:
                current_text += part

        if current_text:
            chapters.append({"title": current_title, "text": current_text[:3000]})

        # 去除过短的片段 (可能不是章节)
        chapters = [c for c in chapters if len(c["text"]) > 100]
        return chapters

    def _extract_world(self, sample: str, chapters: list) -> World:
        """从小说文本中提取世界观"""
        world = World(id="novel_world", name="未命名")

        try:
            data = self.llm.chat_json(
                system_prompt=EXTRACT_WORLD_PROMPT,
                user_prompt=f"从以下小说文本中提取世界观设定:\n\n{sample[:6000]}",
            )
        except Exception as e:
            print(f"   世界观提取失败: {e}, 使用默认")
            return world

        world.name = data.get("name", "未命名世界")
        world.description = data.get("description", "")

        for loc in data.get("locations", []):
            loc_id = loc.get("id", f"loc_{len(world.locations)}")
            world.locations[loc_id] = Location(
                id=loc_id,
                name=loc.get("name", "未知"),
                description=loc.get("description", ""),
            )

        for fac in data.get("factions", []):
            fac_id = fac.get("id", f"fac_{len(world.factions)}")
            world.factions[fac_id] = Faction(
                id=fac_id,
                name=fac.get("name", "未知"),
                description=fac.get("description", ""),
            )

        for rule in data.get("rules", []):
            world.rules.append(WorldRule(
                name=rule.get("name", ""),
                description=rule.get("description", ""),
                category=rule.get("category", "general"),
            ))

        return world

    def _extract_characters(self, sample: str) -> list[Character]:
        """从小说文本中提取角色"""
        chars = []

        try:
            data = self.llm.chat_json(
                system_prompt=EXTRACT_CHARACTERS_PROMPT,
                user_prompt=f"从以下小说文本中提取主要角色:\n\n{sample[:6000]}",
            )
        except Exception as e:
            print(f"   角色提取失败: {e}, 使用默认")
            return chars

        items = data if isinstance(data, list) else data.get("characters", [])

        for i, item in enumerate(items):
            name = item.get("name", f"角色{i+1}")
            char = Character(
                id=f"char_{i+1:03d}",
                name=name,
                identity=CharIdentity(
                    name=name,
                    age=item.get("age", 20),
                    occupation=item.get("occupation", ""),
                ),
                personality=CharPersonality(
                    traits=item.get("personality_traits", []),
                    speaking_style=item.get("speaking_style", ""),
                ),
                motivation=CharMotivation(
                    deep_desire=item.get("deep_desire", ""),
                    fear=item.get("fear", ""),
                ),
            )
            char.secrets = item.get("secrets", [])
            char.skills = item.get("skills", {})
            # 影响力
            inf_data = item.get("influence", {})
            char.stats.influence = Influence(
                economic=inf_data.get("economic", 1),
                political=inf_data.get("political", 1),
                military=inf_data.get("military", 1),
                knowledge=inf_data.get("knowledge", 1),
                social=inf_data.get("social", 1),
                mystical=inf_data.get("mystical", 1),
            )
            # 执念
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
            chars.append(char)

        return chars

    def _extract_timeline(self, chapters: list[dict],
                          characters: list[Character]) -> Timeline:
        """从章节列表中提取时间轴"""
        tl = Timeline()

        # 简单模式: 直接用章节标题和摘要
        for i, ch in enumerate(chapters):
            chapter_num = i + 1
            text = ch["text"][:1000]  # 前 1000 字分析

            node = TimelineNode(
                chapter=chapter_num,
                title=ch["title"],
                summary=text[:200],
            )
            tl.add_node(node)

        # LLM 增强: 提取关键事件和角色 (分批处理以免超长)
        batch_size = 5
        for i in range(0, len(chapters), batch_size):
            batch = chapters[i:i+batch_size]
            batch_text = "\n\n".join(
                f"=== 第{i+j+1}章 ===\n{c['text']}"
                for j, c in enumerate(batch)
            )

            try:
                data = self.llm.chat_json(
                    system_prompt=EXTRACT_TIMELINE_PROMPT,
                    user_prompt=f"从以下章节提取时间轴信息:\n\n{batch_text[:5000]}",
                )
                items = data if isinstance(data, list) else data.get("chapters", [])
                for j, item in enumerate(items):
                    ch_num = i + j + 1
                    node = tl.get_node(ch_num)
                    if node:
                        node.title = item.get("title", node.title)
                        node.summary = item.get("summary", node.summary)
                        node.key_events = item.get("key_events", [])
                        node.chars_present = item.get("chars_present", [])
            except Exception as e:
                print(f"   第{i+1}章时间轴提取跳过: {e}")

        return tl
