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
世界自主演化引擎 — 每 Tick 驱动世界运转

世界自己活着——天气变化、谣言传播、随机事件发生。
角色感知世界的变化, 而不是世界等待角色行动。
"""

from typing import Optional
from app.world.schema import World
from app.world.weather import WeatherSystem
from app.world.rumors import RumorSystem
from app.world.events import WorldEventGenerator
from app.world.threats import WorldThreatSystem
from app.world.actors import WorldActorSystem


class WorldEngine:
    """
    世界自主演化引擎
    
    每 Tick (=1 天) 运行一次, 完全独立于角色行为。
    但高影响力角色的行动会提高事件触发概率和传播速度。
    """

    def __init__(self, world: World):
        self.world = world
        self.weather = WeatherSystem()
        self.rumors = RumorSystem()
        self.events = WorldEventGenerator()
        self.threats = WorldThreatSystem()
        self.actors = WorldActorSystem()
        # actors will be seeded by WorldBuilder  # ★★★ 毁灭威胁
        self.day: int = 0
        self.tick_log: list = []

    def tick(self) -> dict:
        """推进一天, 返回本日的世界状态变化"""
        self.day += 1
        changes = {"weather": None, "rumors": [], "events": [], "daily_events": []}

        # 1. 天气
        weather_fx = self.weather.tick()
        changes["weather"] = {
            "current": self.weather.current,
            "effects": weather_fx,
        }

        # 2. 谣言传播
        rumor_events = self.rumors.tick(self.world.locations)
        changes["rumors"] = rumor_events

        # 3. 世界随机事件
        location_ids = list(self.world.locations.keys())
        new_events = self.events.roll(location_ids, self.day)
        for ev in new_events:
            changes["events"].append(ev["title"])
            # 高风险事件 → 影响地点状态
            if ev["effects"].get("danger_level"):
                self.world.global_state["danger_level"] = \
                    (self.world.global_state.get("danger_level", 0) + 30)
            changes["daily_events"].append(ev["description"])

        # 4. 世界行动者推进
        actor_events = self.actors.tick(self.day)
        for ae in actor_events:
            desc = ae.get("description", "")
            rel_change = ae.get("relationship_change", "")
            changes["actor_events"] = changes.get("actor_events", []) + [desc + (f" [{rel_change}]" if rel_change else "")]
            changes["daily_events"].append(f"【{ae["actor"]}】{desc}")

        # 5. 毁灭威胁推进
        threat_events = self.threats.tick(self.day, self.world.global_state)
        changes["threats"] = threat_events
        for te in threat_events:
            changes["daily_events"].append(te)

        self.tick_log.append({
            "day": self.day,
            "weather": self.weather.current,
            "events": changes["events"],
            "threats": threat_events,
        })

        return changes

    def inject_character_action(self, char_name: str, action_desc: str,
                                 dimension: str, weight: int, radius: str,
                                 location_id: str):
        """高影响力角色的行为 → 按维度影响世界
        
        不同维度影响世界的方式完全不同:
          economic  → 物价波动/贸易机会
          political → 势力关系变化/政策变动
          military  → 安全局势/战争风险
          knowledge → 技术突破/新发现传播
          social    → 舆论风向/谣言可信度
          mystical  → 灵气波动/天象异变/秘境反应
        
        weight 决定影响强度, radius 决定影响范围。
        """
        # 根据维度生成不同风格的谣言
        rumor_templates = {
            "economic": f"听说{char_name}{action_desc}, 看来{radius}市场要起波澜",
            "political": f"{char_name}{action_desc}, {radius}权力格局或将生变",
            "military": f"{char_name}{action_desc}, {radius}安全局势引人关注",
            "knowledge": f"{char_name}{action_desc}, 这一发现可能改变{radius}的认知",
            "social": f"{char_name}{action_desc}, {radius}议论纷纷",
            "mystical": f"{char_name}{action_desc}, 灵气随之波动",
        }

        if weight >= 10:
            rumor = rumor_templates.get(dimension, f"听说{char_name}{action_desc}")
            self.rumors.generate(
                content=rumor,
                source_location=location_id,
                source_character=char_name,
                influence_weight=min(weight, 100),
                accuracy=0.9 if weight < 30 else 0.7,  # 权重越高谣言越夸张
            )

        # ★★★ 高影响力行为影响毁灭威胁线
        threat_effects = self.threats.influence(dimension, weight, direction=1)
        for effect in threat_effects:
            self.rumors.generate(
                content=effect,
                source_location=location_id,
                source_character=char_name,
                influence_weight=min(weight, 100),
                accuracy=0.7,
            )

        # 高权重角色在对应维度触发世界事件
        if weight >= 30:
            self.events._influence_bonus = min(weight / 10, 10)
            # 特定维度的事件
            dimension_events = {
                "economic": {"title": "商道变动", "severity": 3},
                "political": {"title": "权力暗流", "severity": 4},
                "military": {"title": "风云渐起", "severity": 4},
                "knowledge": {"title": "学问传播", "severity": 2},
                "social": {"title": "民心所向", "severity": 3},
                "mystical": {"title": "天地异动", "severity": 4},
            }
            ev_info = dimension_events.get(dimension, {})
            if ev_info and self.day % 5 == 0:
                self.world.global_state[f"trend_{dimension}"] = f"{char_name}的{action_desc[:20]}引发{ev_info['title']}"

    def environment_for(self, location_id: str) -> dict:
        """给角色的感知层提供环境上下文"""
        weather = self.weather.effects()
        rumor_text = self.rumors.rumor_text_for(location_id)
        active_events = self.events.active_at(location_id)

        env = {
            "weather": self.weather.current,
            "weather_effects": weather,
            "temperature": weather.get("temp", 25),
            "day": self.day,
        }
        if rumor_text:
            env["rumors"] = rumor_text
        if active_events:
            env["events"] = [e["title"] + ": " + e["description"] for e in active_events[:2]]

        # ★★★ 世界行动者 (按角色影响力层级过滤)
        # actor 感知由 perception.py 直接调用 actors.visible_events_for
            if visible:
                env["world_affairs"] = visible[-3:]

        # ★★★ 毁灭威胁
        threat_text = self.threats.status_for_perception()
        if threat_text:
            env["threats"] = threat_text

        return env
