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
Novel World Engine — 一键调用接口
"""

from typing import Optional, Callable
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
    progress_callback: Optional[Callable] = None,
    fast_mode: bool = False,
) -> dict:
    """
    一键运行叙事模拟

    Args:
        world_description: 世界观设定文本
        character_descriptions: 角色设定列表
        chapters: 生成章节数
        beats_per_chapter: 每章 Beat 数
        model: LLM 模型名 (覆盖 .env)
        progress_callback: 进度回调 (stage, current, total, message)
            stage: 'building_world' | 'generating_chars' | 'running' | 'narrating' | 'done'

    Returns:
        包含 chapters/total_words/quality_scores 的字典
    """
    Config.DEFAULT_BEATS_PER_CHAPTER = beats_per_chapter

    errors = Config.validate()
    if errors:
        raise ValueError("LLM_API_KEY 未配置。请创建 .env 文件或设置环境变量。")
    if not world_description.strip():
        raise ValueError("世界观描述不能为空")
    if len(character_descriptions) < 2:
        raise ValueError("至少需要 2 个角色")

    def _cb(stage, cur=0, total=0, msg=""):
        if progress_callback:
            progress_callback(stage, cur, total, msg)

    llm = LLMClient()
    llm.client.timeout = 60
    if model:
        llm.model = model

    # 构建世界
    _cb("building_world", 0, 4, "正在解析世界观...")
    world = WorldBuilder(llm).build(world_description)
    _cb("building_world", 1, 4, "世界观构建完成")

    _cb("building_world", 2, 4, "正在生成 Actor...")

    # 启动世界引擎
    world.world_engine = WorldEngine(world)
    try:
        actors = WorldBuilder(llm).build_actors(world_description, world)
        _cb("building_world", 3, 4, "Actor 生成完成")
        if actors and hasattr(world.world_engine, 'actors'):
            world.world_engine.actors = actors
    except Exception:
        pass

    # 生成角色
    _cb("generating_chars", 0, len(character_descriptions), "正在生成角色...")
    chars = CharacterGenerator(llm).generate_batch(character_descriptions)
    first_loc = list(world.locations.keys())[0] if world.locations else ""
    for c in chars:
        c.current_location = first_loc
    char_name_map = {c.id: c.name for c in chars}
    _cb("generating_chars", len(character_descriptions), len(character_descriptions), "角色生成完成")

    # 初始化引擎
    engine = Engine(world, chars, llm)
    director = PlotDirector(world, chars)
    narrator = Narrator(llm)
    quality = QualityChecker()

    result = {"chapters": [], "total_words": 0, "quality_scores": []}

    # 逐章运行
    for chap in range(1, chapters + 1):
        _cb("running", chap - 1, chapters, f"第{chap}章规划中...")
        blueprint = director.plan_chapter(chap)

        _cb("running", chap - 1, chapters, f"第{chap}章模拟中...")
        beat_logs = engine.run_chapter(director, blueprint)

        _cb("narrating", chap - 1, chapters, f"第{chap}章生成文本中...")
        chapter_text = (narrator.narrate_chapter_batched if fast_mode else narrator.narrate_chapter)(beat_logs, char_name_map=char_name_map)
        # ★★★ Writer 重写: 将事件日志变为可读的小说
        if chapter_text and len(chapter_text) > 50:
            scene = {"time": world.timeline.current_time, "location_name": world.locations.get("loc_001", "") if hasattr(world, "locations") else ""}
            rewritten = narrator.rewrite_chapter(chapter_text, world, scene)
            if rewritten and len(rewritten) > len(chapter_text) // 2:
                chapter_text = rewritten

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

        _cb("running", chap, chapters, f"第{chap}章完成 ({len(chapter_text)}字)")

    # 异步: FDR 压缩 + 其他后处理 (不阻塞下一章)
    from concurrent.futures import ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        executor.submit(compressor.add_chapter_summary, chap, chapter_text, llm, qr.get("total", 0))
    except Exception:
        pass
    # 不等待 executor 完成, 下一章继续

    result["total_words"] = sum(len(c["text"]) for c in result["chapters"])
    _cb("done", chapters, chapters, f"完成! 共{result['total_words']}字")
    return result
