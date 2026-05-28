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
Zidu is God — CLI 入口

用法:
  # 从文件运行模拟
  python -m app.cli run --world world.txt --chars chars.txt --chapters 3

  # 使用内置示例运行演示 (不需要文件)
  python -m app.cli demo

  # 交互式引导 (逐步输入)
  python -m app.cli interactive

  # 查看帮助
  python -m app.cli --help
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


def _build_parser():
    import argparse
    p = argparse.ArgumentParser(
        prog="zidu-is-god",
        description="创世日记引擎 — 让角色在模拟的世界中书写自己的故事",
        epilog="文档: https://github.com/... | 许可证: AGPL-3.0",
    )
    sub = p.add_subparsers(dest="command")

    # ── run ──
    r = sub.add_parser("run", help="从文件读入世界观和角色, 运行模拟")
    r.add_argument("--world", required=True, help="世界观设定文件路径")
    r.add_argument("--chars", required=True, help="角色设定文件路径 (每行一个角色)")
    r.add_argument("--chapters", type=int, default=3, help="生成章节数 (默认 3)")
    r.add_argument("--beats", type=int, default=3, help="每章 Beat 数 (默认 3, 越大越精细)")
    r.add_argument("--output", default="", help="输出文件路径 (不指定则输出到终端)")
    r.add_argument("--model", default="", help="LLM 模型名 (覆盖 .env 配置)")

    # ── demo ──
    sub.add_parser("demo", help="使用内置示例快速演示 (无需输入文件)")

    # ── interactive ──
    i = sub.add_parser("interactive", help="交互式引导: 逐步输入世界观和角色")
    i.add_argument("--chapters", type=int, default=3, help="生成章节数 (默认 3)")
    i.add_argument("--beats", type=int, default=3, help="每章 Beat 数 (默认 3)")

    return p


# ─── 演示数据 ─────────────────────────────────────────────

DEMO_WORLD = """苍澜学院武道世界。
地点:
- 演武场: 学生日常训练和比试的广场
- 宿舍区: 学生住宿区
- 藏书阁: 珍藏功法典籍的阁楼
修炼体系: 炼体→凝气→筑基
势力:
- 赵家: 苍澜城大家族, 势力庞大
"""

DEMO_CHARS = [
    "林北辰, 16岁, 外门弟子, 黄级灵根, 沉默寡言但意志坚定, 很想进入内门证明自己",
    "赵无极, 18岁, 内门弟子, 地级灵根, 嚣张跋扈, 家族势力大, 喜欢欺压外门弟子",
    "苏晚晴, 17岁, 内门天才, 地级灵根, 表面高傲内心善良, 对林北辰似有宿缘",
]


# ─── 核心流程 ─────────────────────────────────────────────

def run_with(world_text, char_lines, chapters=3, beats=3, model="", output=""):
    """核心运行函数 (同时被 CLI 和 Python API 调用)"""
    Config.DEFAULT_BEATS_PER_CHAPTER = beats

    errors = Config.validate()
    if errors:
        msg = "❌ LLM_API_KEY 未配置。请创建 .env 文件或在环境变量中设置。"
        return {"error": msg}

    llm = LLMClient()
    llm.client.timeout = 60
    if model:
        llm.model = model

    # 构建世界
    wb = WorldBuilder(llm)
    world = wb.build(world_text)

    # 生成角色
    cg = CharacterGenerator(llm)
    chars = cg.generate_batch(char_lines)
    first_loc = list(world.locations.keys())[0] if world.locations else ""
    for c in chars:
        c.current_location = first_loc
    char_name_map = {c.id: c.name for c in chars}

    # 初始化
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


# ─── CLI 子命令 ────────────────────────────────────────────

def cmd_run(args):
    world_text = "\n".join(_load_lines(args.world))
    char_lines = _load_lines(args.chars)
    if not world_text:
        print("❌ 世界观文件为空"); sys.exit(1)
    if len(char_lines) < 2:
        print("❌ 至少需要 2 个角色"); sys.exit(1)

    print(f"📖 创世日记引擎 — 模拟运行")
    print(f"   章节: {args.chapters} × {args.beats} Beat | 角色: {len(char_lines)}")

    result = run_with(world_text, char_lines, args.chapters, args.beats, args.model)
    if "error" in result:
        print(result["error"]); sys.exit(1)

    for ch in result["chapters"]:
        mark = "✅" if ch["quality_passed"] else "❌"
        print(f"\n📝 第{ch['number']}章 ({ch['word_count']} 字, 质量 {ch['quality']}/80 {mark})")
        preview = ch["text"][:200]
        print(preview + ("..." if len(ch["text"]) > 200 else ""))

    print(f"\n✅ 完成! 总字数: {result['total_words']}")

    output_text = "\n\n---\n\n".join(ch["text"] for ch in result["chapters"])
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"   已保存到: {args.output}")


def cmd_demo(args):
    print("📖 创世日记引擎 — 演示模式")
    print("   使用内置示例: 苍澜学院 × 3角色 × 3章\n")
    result = run_with(DEMO_WORLD, DEMO_CHARS, chapters=3, beats=3)
    if "error" in result:
        print(result["error"])
        print("\n💡 演示模式需要 LLM API, 请先配置 .env 文件")
        return

    for ch in result["chapters"]:
        mark = "✅" if ch["quality_passed"] else "❌"
        print(f"📝 第{ch['number']}章 ({ch['word_count']} 字, 质量 {ch['quality']}/80 {mark})")
        print(f"   {ch['text'][:150]}...\n")

    print(f"✅ 完成! 总字数: {result['total_words']}")


def cmd_interactive(args):
    print("📖 创世日记引擎 — 交互式输入")
    print("   请逐行输入世界观 (输入空行结束):")
    lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        lines.append(line)
    world_text = "\n".join(lines)

    print("\n   请逐行输入角色设定 (每行一个, 输入空行结束, 至少2个):")
    chars = []
    while len(chars) < 2:
        line = input(f"  角色{len(chars)+1}> ")
        if not line:
            if len(chars) >= 2:
                break
            print("   至少需要 2 个角色")
            continue
        chars.append(line)

    print(f"\n📖 开始模拟: {args.chapters}章 × {args.beats} Beat\n")
    result = run_with(world_text, chars, args.chapters, args.beats)
    if "error" in result:
        print(result["error"]); return

    for ch in result["chapters"]:
        mark = "✅" if ch["quality_passed"] else "❌"
        print(f"📝 第{ch['number']}章 ({ch['word_count']} 字, 质量 {ch['quality']}/80 {mark})")
        print(f"   {ch['text'][:200]}...\n")

    print(f"✅ 完成! 总字数: {result['total_words']}")


# ─── 工具 ─────────────────────────────────────────────────

def _load_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# ─── 入口 ─────────────────────────────────────────────────

def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "interactive":
        cmd_interactive(args)
    else:
        parser.print_help()
        print("\n示例:")
        print("  # 快速演示 (需要配置 .env)")
        print("  python -m app.cli demo")
        print()
        print("  # 从文件运行")
        print("  python -m app.cli run --world world.txt --chars chars.txt --chapters 3")
        print()
        print("  # 交互式输入")
        print("  python -m app.cli interactive")


if __name__ == "__main__":
    main()
