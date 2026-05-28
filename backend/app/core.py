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
创世日记引擎 — 一键调用接口

对外暴露的最简 API, 用户只需三行代码即可运行:
    from app.core import simulate
    result = simulate(world_description, character_descriptions, chapters=3)
"""

from typing import Optional
from app.config import Config
from app.llm.client import LLMClient
from app.world.builder import WorldBuilder
from app.world.engine import WorldEngine
from app.characters.generator import CharacterGenerator
from app.engine.simulation import Engine
from app.plot.director import PlotDirector
from app.narrator.narrator import Narrator
from app.narrator.quality import QualityChecker


def simulate(
    world_description: str,
    character_descriptions: list[str],
    chapters: int = 3,
    beats_per_chapter: int = 3,
    model: str = "",
) -> dict:
    """
    一键运行叙事模拟

    Args:
        world_description: 世界观设定文本
        character_descriptions: 角色设定列表, 每行一个角色
        chapters: 生成章节数 (默认 3)
        beats_per_chapter: 每章 Beat 数 (默认 3)
        model: LLM 模型名 (覆盖 .env 配置)

    Returns:
        {
            "chapters": [
                {"number": 1, "text": "...", "word_count": 1000, "quality": 65, "quality_passed": True},
                ...
            ],
            "total_words": 3000,
            "quality_scores": [65, 58, 62],
        }

    Raises:
        ValueError: 配置错误或输入无效
    """
    Config.DEFAULT_BEATS_PER_CHAPTER = beats_per_chapter

    errors = Config.validate()
    if errors:
        raise ValueError("LLM_API_KEY 未配置。请创建 .env 文件或设置环境变量。")

    if not world_description.strip():
        raise ValueError("世界观描述不能为空")
    if len(character_descriptions) < 2:
        raise ValueError("至少需要 2 个角色")

    llm = LLMClient()
    llm.client.timeout = 60
    if model:
        llm.model = model

    # 构建世界
    world = WorldBuilder(llm).build(world_description)

    # 启动世界引擎
    world.world_engine = WorldEngine(world)
    
    # 生成世界行动者 (如果 WorldBuilder 支持)
    try:
        actors = WorldBuilder(llm).build_actors(world_description, world)
        if actors and hasattr(world.world_engine, 'actors'):
            world.world_engine.actors = actors
    except Exception:
        pass  # 非关键, 跳过

    # 生成角色
    chars = CharacterGenerator(llm).generate_batch(character_descriptions)
    first_loc = list(world.locations.keys())[0] if world.locations else ""
    for c in chars:
        c.current_location = first_loc
    char_name_map = {c.id: c.name for c in chars}

    # 初始化引擎
    engine = Engine(world, chars, llm)
    director = PlotDirector(world, chars)
    narrator = Narrator(llm)
    quality = QualityChecker()

    result = {"chapters": [], "total_words": 0, "quality_scores": []}

    for chap in range(1, chapters + 1):
        blueprint = director.plan_chapter(chap)
        beat_logs = engine.run_chapter(director, blueprint)
        chapter_text = narrator.narrate_chapter(beat_logs, char_name_map=char_name_map)
        qr = quality.check(chapter_text, chapter_num=chap)

        result["chapters"].append({
            "number": chap,
            "text": chapter_text,
            "word_count": len(chapter_text),
            "quality": qr["total"],
            "quality_passed": qr["passed"],
        })
        result["quality_scores"].append(qr["total"])

        avg_tension = sum(l.post_tension for l in beat_logs) / max(len(beat_logs), 1)
        director.finish_chapter(chap, avg_tension)

    result["total_words"] = sum(len(c["text"]) for c in result["chapters"])
    return result
