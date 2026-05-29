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
WorldBuilder — LLM 将用户的世界观文档解析为结构化世界数据 + 世界行动者
"""

from typing import Optional
from app.world.schema import World, Location, Faction, WorldRule, Timeline
from app.world.actors import WorldActorSystem, WorldActor
from app.llm.client import LLMClient


WORLD_BUILD_SYSTEM_PROMPT = """你是一位小说世界观架构师。将用户的自然语言世界观描述解析为结构化的地点、势力、规则数据。

你必须返回 JSON 格式, 严格按以下 schema:

{
  "name": "世界名称",
  "description": "一句话描述",
  "locations": [
    {"id": "loc_001", "name": "地点名", "description": "描述", "parent_id": null}
  ],
  "factions": [
    {"id": "fac_001", "name": "势力名", "description": "描述"}
  ],
  "rules": [
    {"name": "规则名", "description": "规则描述", "category": "magic/technology/social/general"}
  ],
  "starting_location": "主角初始地点的 id",
  "calendar": "历法描述如'架空历·三月'",
  "initial_time": "第1天·清晨"
}

不要输出任何非 JSON 内容。如果没有某个字段, 用空数组 [] 替代。"""


ACTOR_GEN_SYSTEM_PROMPT = """你是一位世界格局设计师。根据世界观设定, 生成该世界中独立于主角的顶级势力/人物。

这些"世界行动者"有自己的议程、影响力和相互关系, 他们的行为改变世界格局, 不依赖主角而独立运作。

返回 JSON 数组, 每个元素按以下 schema:
[
  {
    "name": "势力/人物名称",
    "type": "个人/组织/势力",
    "description": "描述",
    "tier": 层级(1-10, 10=世界巅峰),
    "influence": {
      "economic": 财富影响力(1-100),
      "political": 政治影响力(1-100),
      "military": 武力影响力(1-100),
      "knowledge": 知识影响力(1-100),
      "social": 声望影响力(1-100),
      "mystical": 超凡影响力(1-100)
    },
    "relationships": [
      {"target": "另一个势力名称", "relation": "敌对/友好/中立/联盟"}
    ]
  }
]

要求:
- 不同的世界观下生成完全不同的行动者 (修仙/现代/科幻/西幻/末日)
- 至少生成 4 个, 最多 8 个
- 各维度的值要符合世界观设定
- 关系网络要合理, 有敌对有联盟
"""



ACTION_GEN_PROMPT = """设计该世界观下特有的角色行为类型。返回JSON数组, 每项:{"id":"大写ID","name":"行为名","description":"描述","params":{}}。
基础行为已有: DIALOGUE, OBSERVE, INNER, WAIT, ACT。
请补充3-6个该世界特有的。例如: 修仙->CULTIVATE,EXPLORE; 都市->WORK,DRIVE; 西幻->PRAY,HUNT。只返回JSON。"""

WEATHER_GEN_PROMPT = """根据世界观设计天气系统。返回JSON数组, 每项:{"name":"天气名","energy_cost":1.0,"visibility":0.8,"cultivation_bonus":1.0,"description":"..."}。
至少3个最多8个。只返回JSON。"""

THREAT_GEN_PROMPT = """根据世界观设计毁灭威胁。返回JSON数组, 每项:{"name":"威胁名","description":"...","natural_growth":0.003,"trigger_threshold":0.9,"accelerates_by":["dimension"],"decelerates_by":["dimension"],"effects":{"danger_level":"+50"}}。至少3个最多6个。只返回JSON。"""

EVENT_GEN_PROMPT = """根据世界观设计随机事件。返回JSON数组, 每项:{"type":"disaster/opportunity/faction/celebration","title":"事件名","desc":"描述(用{location}代替地点)","severity":1-5,"duration_days":1-10,"effects":{}}。至少4个最多8个。只返回JSON。"""

class WorldBuilder:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()


    def build_actions(self, world_description: str) -> list:
        try:
            d = self.llm.chat_json(ACTION_GEN_PROMPT, world_description[:2000])
            return d if isinstance(d, list) else []
        except: return []

    def build_weather(self, world_description: str) -> list:
        try:
            d = self.llm.chat_json(WEATHER_GEN_PROMPT, world_description[:2000])
            return d if isinstance(d, list) else []
        except: return []

    def build_threats(self, world_description: str) -> list:
        try:
            d = self.llm.chat_json(THREAT_GEN_PROMPT, world_description[:2000])
            return d if isinstance(d, list) else []
        except: return []

    def build_events(self, world_description: str) -> list:
        try:
            d = self.llm.chat_json(EVENT_GEN_PROMPT, world_description[:2000])
            return d if isinstance(d, list) else []
        except: return []

    def build_extras(self, world_description: str) -> dict:
        return {
            "actions": self.build_actions(world_description),
            "weather": self.build_weather(world_description),
            "threats": self.build_threats(world_description),
            "events": self.build_events(world_description),
        }

    def build(self, world_description: str) -> World:
        """将世界观描述解析为结构化 World 对象"""
        if not world_description.strip():
            return self._default_world()

        try:
            data = self.llm.chat_json(
                system_prompt=WORLD_BUILD_SYSTEM_PROMPT,
                user_prompt=f"请解析以下世界观设定:\n\n{world_description}",
            )
        except Exception as e:
            print(f"[WorldBuilder] LLM 解析失败, 使用默认世界观: {e}")
            return self._default_world()

        world = World(
            id="world_001",
            name=data.get("name", "未命名世界"),
            description=data.get("description", ""),
        )

        for loc_data in data.get("locations", []):
            world.locations[loc_data.get("id", f"loc_{len(world.locations)}")] = Location(
                id=loc_data.get("id", f"loc_{len(world.locations)}"),
                name=loc_data.get("name", "未知地点"),
                description=loc_data.get("description", ""),
                parent_id=loc_data.get("parent_id"),
            )

        for fac_data in data.get("factions", []):
            fac_id = fac_data.get("id", f"fac_{len(world.factions)}")
            world.factions[fac_id] = Faction(
                id=fac_id,
                name=fac_data.get("name", "未知势力"),
                description=fac_data.get("description", ""),
            )

        for rule_data in data.get("rules", []):
            world.rules.append(WorldRule(
                name=rule_data.get("name", ""),
                description=rule_data.get("description", ""),
                category=rule_data.get("category", "general"),
            ))

        world.timeline = Timeline(
            current_time=data.get("initial_time", "第1天·清晨"),
            calendar=data.get("calendar", ""),
        )

        return world

    def build_actors(self, world_description: str, world: World) -> WorldActorSystem:
        """根据世界观生成世界行动者"""
        system = WorldActorSystem()

        try:
            data = self.llm.chat_json(
                system_prompt=ACTOR_GEN_SYSTEM_PROMPT,
                user_prompt=f"请为以下世界观生成世界行动者:\n\n{world_description}",
            )
        except Exception as e:
            print(f"[WorldBuilder] Actor 生成失败: {e}, 使用默认")
            system.seed_default_actors()
            return system

        # 建立名称到 id 的映射
        name_to_id = {}

        for item in data if isinstance(data, list) else data.get("actors", []):
            aid = item.get("name", "").lower().replace(" ", "_")[:20]
            name_to_id[item.get("name", "")] = aid

            inf = item.get("influence", {})
            actor = WorldActor(
                id=aid,
                name=item.get("name", "未知"),
                type=item.get("type", "势力"),
                description=item.get("description", ""),
                tier=item.get("tier", 5),
                influence={
                    "economic": inf.get("economic", 10),
                    "political": inf.get("political", 10),
                    "military": inf.get("military", 10),
                    "knowledge": inf.get("knowledge", 10),
                    "social": inf.get("social", 10),
                    "mystical": inf.get("mystical", 10),
                },
            )
            system.add_actor(actor)

        # 建立关系
        for item in data if isinstance(data, list) else data.get("actors", []):
            source_name = item.get("name", "")
            source_id = name_to_id.get(source_name)
            for rel in item.get("relationships", []):
                target_name = rel.get("target", "")
                target_id = name_to_id.get(target_name)
                if source_id and target_id and source_id in system.actors and target_id in system.actors:
                    system.actors[source_id].relationships[target_id] = rel.get("relation", "中立")
                    system.actors[target_id].relationships[source_id] = rel.get("relation", "中立")

        if not system.actors:
            system.seed_default_actors()

        return system

    def _default_world(self) -> World:
        world = World(id="world_001", name="默认世界", description="一个普通的世界")
        world.locations["loc_main"] = Location(id="loc_main", name="主城", description="故事发生的主要地点")
        world.timeline = Timeline(current_time="第1天·清晨")
        return world
