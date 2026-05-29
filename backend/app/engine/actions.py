from typing import Optional
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
行动解析与冲突解决模块
"""

from app.characters.schema import Character
from app.world.schema import World
from app.engine.events import NarrativeEvent


def resolve_actions(
    events: list[NarrativeEvent],
    characters: dict[str, Character],
    world: World,
) -> list[NarrativeEvent]:
    """
    收集所有角色的决策并解析。
    检测冲突并注册到 World 的冲突管理, 综合裁决后返回。
    """
    resolved_events = []

    # 按目标角色分组
    target_map = {}
    for ev in events:
        if ev.target_id:
            target_map.setdefault(ev.target_id, []).append(ev)

    # 检测冲突并注册
    for target_id, target_events in target_map.items():
        if len(target_events) >= 2:
            # 多个角色针对同一目标 → 注册冲突
            for ev in target_events:
                world.register_conflict(ev.agent_id, target_id, f"{ev.action_type}冲突")
                ev.outcome = f"[冲突] {ev.outcome}"
                ev.importance = min(5, ev.importance + 1)
        else:
            # 单对单交互 (A→B 对话/行动) → 也可能产生冲突
            ev = target_events[0]
            if ev.action_type in ("DIALOGUE", "ACT"):
                world.register_conflict(ev.agent_id, target_id, f"{ev.action_type}交互")
                ev.importance = min(4, ev.importance + 1)

    # ★★★ 生存类行动: 更新角色状态
    for ev in events:
        char = characters.get(ev.agent_id)
        if not char:
            continue
        # 解析 content 中的 params (事件存储为字符串, 需要 json 解析)
        import json as _json
        params = {}
        try:
            params = _json.loads(ev.content) if ev.content.startswith("{") else {}
        except Exception:
            params = {}
        if ev.action_type == "REST":
            hours = params.get("hours", 4) if isinstance(params, dict) else 4
            if isinstance(hours, str):
                hours = 4
            char.stats.rest(hours)
            ev.outcome = f"{char.name}休息了{hours}个时辰, 体力恢复"
            ev.importance = 2
        elif ev.action_type == "HEAL":
            char.stats.hp = min(char.stats.max_hp, char.stats.hp + 30)
            char.stats.injuries.clear()
            ev.outcome = f"{char.name}处理了伤势, hp恢复"
            ev.importance = 3
        elif ev.action_type == "CULTIVATE":
            char.stats.cultivation += 1
            char.stats.needs["achievement"] = max(0, char.stats.needs["achievement"] - 10)
            ev.outcome = f"{char.name}修炼了一段时间, 修为略有精进"
            ev.importance = 2
        elif ev.action_type == "TRADE":
            char.stats.wealth += 10
            if ev.target_id:
                target_char = characters.get(ev.target_id)
                if target_char:
                    target_char.stats.wealth -= 10
                    ev.outcome = f"{char.name}与{target_char.name}完成了交易"
            else:
                ev.outcome = f"{char.name}完成了交易"
            ev.importance = 2
        elif ev.action_type == "EXPLORE":
            target_loc = params.get("target", "") if isinstance(params, dict) else ""
            weather = world.global_state.get("current_weather", {})
            if isinstance(weather, str):
                weather = {}
            msg = EnvironmentInteraction.handle_explore(char, target_loc, world)
            ev.outcome = msg
            ev.importance = 3

    # ★★★ 高影响力角色 → 注入 WorldEngine
    for ev in events:
        char = characters.get(ev.agent_id)
        if char and ev.importance >= 3:
            world_engine = getattr(world, 'world_engine', None)
            if world_engine and hasattr(char, 'stats') and char.stats.influence:
                inf = char.stats.influence
                primary_dim = inf.primary()
                primary_val = getattr(inf, primary_dim, 1)
                if primary_val >= 10:
                    world_engine.inject_character_action(
                        char_name=char.name,
                        action_desc=ev.outcome[:40],
                        dimension=primary_dim,
                        weight=primary_val,
                        radius=inf.radii.get(primary_dim, 'local'),
                        location_id=ev.location,
                    )

    # 如果角色间有 "战斗/挑战" 等对抗行动 → 升级冲突 + 伤害
    for ev in events:
        if ev.action_type == "ACT" and any(kw in str(ev.content) for kw in ["挑战", "战斗", "切磋", "打"]):
            if ev.target_id:
                world.escalate_conflict()
                ev.importance = 5
                # 对目标造成伤害
                target_char = characters.get(ev.target_id)
                if target_char:
                    target_char.stats.apply_damage(15, "战斗中")
                    ev.outcome += f" — {target_char.name}受到伤害, hp{target_char.stats.hp}"

    resolved_events = list(events)
    return resolved_events


def resolve_outcome(event: NarrativeEvent, char: Character) -> str:
    """根据事件类型和角色状态, 生成结果文本 (简化版)"""
    if event.action_type == "DIALOGUE":
        return f"{char.name}对{event.target_id}说: {event.content}"
    elif event.action_type == "ACT":
        return f"{char.name}执行了{event.content}"
    elif event.action_type == "INNER":
        return f"{char.name}心想: {event.content}"
    elif event.action_type == "OBSERVE":
        return f"{char.name}观察了{event.target_id or '周围'}"
    else:
        return f"{char.name}按兵不动"

class EnvironmentInteraction:
    """
    环境交互 — 角色与环境之间的双向影响
    
    - 角色探索/采集/建造/交易 → 改变环境
    - 环境的天气/资源/危险 → 影响角色
    """

    @staticmethod
    def handle_explore(char, target_location: Optional[str], world) -> str:
        """探索当前或指定区域"""
        loc_name = "周围"
        if target_location and target_location in world.locations:
            loc_name = world.locations[target_location].name

        # 探索可能发现资源
        discovery_chance = 0.3
        world_state = world.global_state

        import random
        if random.random() < discovery_chance:
            discoveries = [
                "发现了几株珍稀草药",
                "找到一处隐蔽的修炼宝地",
                "发现了一些前人遗留的痕迹",
                "注意到此处地势险要, 易守难攻",
            ]
            msg = f"{char.name}在{loc_name}探索了一番, {random.choice(discoveries)}"
            char.stats.needs["achievement"] = max(0, char.stats.needs["achievement"] - 5)
        else:
            msg = f"{char.name}在{loc_name}探索了一番, 没有特别发现"
            char.stats.stamina = max(0, char.stats.stamina - 5)

        return msg

    @staticmethod
    def handle_collect(char, resource: str, world) -> str:
        """采集资源"""
        resources = char.stats.items
        resources[resource] = resources.get(resource, 0) + 1
        char.stats.stamina = max(0, char.stats.stamina - 10)
        return f"{char.name}采集到了{resource}"

    @staticmethod
    def handle_observe(char, target: Optional[str], world, weather: dict) -> str:
        """观察环境, 包含天气/环境信息"""
        parts = [f"{char.name}环顾四周"]
        if weather:
            parts.append(f"天气{weather.get('current', '晴')}")
        if target:
            parts.append(f"注意观察{target}")
        return ", ".join(parts)

    @staticmethod
    def weather_effect_on_character(char, weather: dict) -> str:
        """天气对角色的影响"""
        energy_cost = weather.get("energy_cost", 1.0)
        if energy_cost > 1.3:
            char.stats.stamina = max(0, char.stats.stamina - 8)
            return f"恶劣天气让{char.name}消耗了大量体力"
        return ""
