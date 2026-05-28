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
演示脚本 — 用内置示例运行一次 3 章模拟
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import Config
from app.llm.client import LLMClient
from app.world.builder import WorldBuilder
from app.characters.generator import CharacterGenerator
from app.engine.simulation import Engine
from app.plot.director import PlotDirector
from app.narrator.narrator import Narrator
from app.narrator.quality import QualityChecker
from app.world.engine import WorldEngine

Config.DEFAULT_BEATS_PER_CHAPTER = 3

DEMO_WORLD = """苍澜学院武道世界。
地点:
- 演武场: 学生日常训练和比试的广场
- 宿舍区: 学生住宿区
修炼体系: 炼体→凝气→筑基
"""

DEMO_CHARS = [
    "林北辰, 16岁, 外门弟子, 黄级灵根, 沉默寡言但意志坚定",
    "赵无极, 18岁, 内门弟子, 地级灵根, 嚣张跋扈, 喜欢欺压外门弟子",
    "苏晚晴, 17岁, 内门天才, 表面高傲内心善良, 对林北辰似有宿缘",
]


def main():
    errors = Config.validate()
    if errors:
        for e in errors:
            print(f"❌ {e}")
        sys.exit(1)

    print("=" * 50)
    print("AI 叙事模拟引擎 — 演示")
    print("=" * 50)

    llm = LLMClient()
    llm.client.timeout = 60

    world = WorldBuilder(llm).build(DEMO_WORLD)
    chars = CharacterGenerator(llm).generate_batch(DEMO_CHARS)
    first_loc = list(world.locations.keys())[0]
    for c in chars:
        c.current_location = first_loc
    char_name_map = {c.id: c.name for c in chars}

    engine = Engine(world, chars, llm)
    director = PlotDirector(world, chars)
    world_engine = WorldEngine(world)
    world.world_engine = world_engine
    narrator = Narrator(llm)
    quality = QualityChecker()

    chapters = 3
    all_text = []

    for chap in range(1, chapters + 1):
        blueprint = director.plan_chapter(chap)
        beat_logs = engine.run_chapter(director, blueprint)
        text = narrator.narrate_chapter(beat_logs, char_name_map=char_name_map)
        qr = quality.check(text, chapter_num=chap)
        all_text.append(text)

        we = world_engine
    weather_info = we.weather.description() if we else ''
    print(f"\n📝 第{chap}章 ({len(text)} 字, 质量 {qr['total']}/80) 天气: {weather_info}")
        print(text[:200] + "...\n")

        avg_tension = sum(l.post_tension for l in beat_logs) / max(len(beat_logs), 1)
        director.finish_chapter(chap, avg_tension)

    total = sum(len(t) for t in all_text)
    print(f"\n✅ 完成! 共 {chapters} 章, {total} 字")


if __name__ == "__main__":
    main()
