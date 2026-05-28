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
感知模块 — 为角色构建当前环境感知上下文
"""

from app.characters.schema import Character
from app.world.schema import World
from app.engine.events import NarrativeEvent


def build_scene(
    world: World,
    location_id: str,
    time: str,
    present_chars: list[Character],
) -> dict:
    """构建当前场景的完整描述"""
    location = world.locations.get(location_id)
    return {
        "location_id": location_id,
        "location_name": location.name if location else "未知",
        "location_desc": location.description if location else "",
        "time": time,
        "present_char_ids": [c.id for c in present_chars],
        "present_chars": [
            {
                "id": c.id,
                "name": c.name,
                "relation": "自己",
            }
            for c in present_chars
        ],
    }


def build_perception(
    char: Character,
    scene: dict,
    world: World,
    recent_events: list[NarrativeEvent] = None,
) -> str:
    """为单个角色构建感知文本（直接拼入 prompt）"""
    lines = []
    lines.append(f"你身处 {scene['location_name']}。{scene['location_desc']}")
    lines.append(f"时间是 {scene['time']}。")

    # 在场其他角色
    others = [c for c in scene["present_chars"] if c["id"] != char.id]
    if others:
        names = [o["name"] for o in others]
        lines.append(f"在场的有: {', '.join(names)}。")
        for other in others:
            rel = char.relationships.get(other["id"])
            if rel:
                lines.append(f"{other['name']}对你的态度: 好感度{rel.affinity:.0f}, 信任度{rel.trust:.0f}")

    # 上几轮刚发生的事（跨 Beat 连贯的关键！）
    if recent_events:
        lines.append("\n刚发生的事:")
        for ev in recent_events[-3:]:  # 最近 3 个事件
            if ev.agent_id != char.id:
                # 别人做的事
                actor_name = "某人"
                lines.append(f"- {ev.outcome[:80]}")
            elif ev.action_type == "INNER":
                lines.append(f"- 你刚才在想: {ev.content[:60]}")
            else:
                lines.append(f"- 你刚才: {ev.outcome[:60]}")

    # ★★★ 环境上下文 (天气/传闻)
    weather = world.global_state.get('current_weather', '') if hasattr(world, 'global_state') else ''
    if weather:
        lines.append(f"天气: {weather}")
    
    # 如果 WorldEngine 存在, 注入传闻
    world_engine = getattr(world, 'world_engine', None)
    if world_engine:
        rums = world_engine.rumors.rumor_text_for(scene.get('location_id', ''))
        if rums:
            lines.append("传闻:")
            lines.append(rums)
        # 毁灭威胁感知
        env = world_engine.environment_for(scene.get('location_id', ''))
        # 世界大事 (按角色影响力过滤)
        if hasattr(char, 'stats') and char.stats.influence:
            prim = char.stats.influence.primary()
            val = getattr(char.stats.influence, prim, 1)
            visible = world_engine.actors.visible_events_for(val)
            if visible:
                lines.append("")
                lines.append("天下大事:")
                for ev in visible[-3:]:
                    lines.append(f"  - {ev}")
        threats = env.get('threats', '')
        if threats:
            lines.append("")
            lines.append("世界态势:")
            lines.append(threats)

    # ★★★ 角色状态
    lines.append(f"\n【状态】{char.stats.status_summary()}")

    # ★★★ 需求紧迫度
    need_text = char.stats.need_urgency_text()
    if need_text:
        lines.append(f"\n【需求】\n{need_text}")

    # 情绪
    lines.append(char.emotional_state.format_for_prompt())

    # ★★★ 记忆检索 (多层记忆系统)
    scene_context = f"{scene.get('location_name', '')} {', '.join(c.name for c in scene.get('present_chars', []) if hasattr(c, 'name'))}"
    memory_text = char.memory.format_for_prompt(
        context=scene_context,
        max_lines=4,
        max_chars=400,
    )
    if memory_text:
        lines.append("")
        lines.append(memory_text)

    return "\n".join(lines)
