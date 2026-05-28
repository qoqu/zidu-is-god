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
世界行动者 — 不依赖主角的独立世界实体

现实中的启示: 中美俄的博弈不会因为一个普通人今天吃了什么而改变。
修仙世界两大至尊的对峙也不会因为一个外门弟子在练剑而暂停。

WorldActor 是"世界自己的角色"——他们有独立的议程、行动节奏、
影响力维度, 他们的行为改变世界格局, 而主角可能很久之后才感知到。

核心机制:
  - 每个 Actor 有自己的 Tick 周期 (天/周/月, 取决于层级)
  - Actor 的行为按影响力维度产生世界事件
  - Actor 之间会互动 (敌对/联盟/交易)
  - 主角的 influence 达到一定层级才能感知/介入 Actor 的行动
"""

from dataclasses import dataclass, field
from typing import Optional
import random
import math


@dataclass
class WorldActor:
    """
    世界行动者 — 一个独立于主角的势力或个人

    Attributes:
        id: 唯一标识
        name: 名称
        type: "个人" / "组织" / "势力"
        description: 描述
        influence: 六维影响力 (参考 Character.Influence)
        tier: 层级 (1~10), 决定行动频率和影响范围
              tier 1-3: 地方级, 4-6: 国家级, 7-8: 大陆级, 9-10: 世界级
        tick_interval_days: 行动间隔 (层级越高间隔越短, 因为动作更频繁)
        last_action_day: 上次行动日
        agenda: 当前议程列表
        relationships: 对其他 Actor 的态度 {actor_id: "敌对"/"友好"/"中立"/"联盟"}
        is_active: 是否活跃 (被消灭/解散后设为 False)
    """
    id: str
    name: str
    type: str = "势力"  # 个人/组织/势力
    description: str = ""
    tier: int = 5
    last_action_day: int = 0
    agenda: list = field(default_factory=list)
    relationships: dict = field(default_factory=dict)
    is_active: bool = True

    # 六维影响力 (各维度 0~100)
    influence: dict = field(default_factory=lambda: {
        "economic": 10, "political": 10, "military": 10,
        "knowledge": 10, "social": 10, "mystical": 10,
    })

    def tick_interval(self) -> int:
        """行动间隔天数: 层级越高动作越频繁"""
        return max(1, 14 - self.tier)  # tier1=13天, tier5=9天, tier10=4天

    def primary_dimension(self) -> str:
        return max(self.influence, key=lambda d: self.influence[d])

    def can_be_perceived_by(self, char_influence: int) -> bool:
        """角色的影响力层级是否能感知到这个 Actor 的行动"""
        # tier1~3: 地方级, 当地人都能感知
        # tier4~6: 国家级, 需要一定地位
        # tier7~8: 大陆级, 只有高层才知
        # tier9~10: 世界级, 近乎传说
        threshold = self.tier * 5  # tier5=25, tier10=50
        return char_influence >= threshold

    def summary(self) -> str:
        status = "活跃" if self.is_active else "已消亡"
        rels = ", ".join(f"{k}:{v}" for k, v in list(self.relationships.items())[:3])
        return f"[{self.type}] {self.name} (T{self.tier}, {status}) 关系: {rels}"


class WorldActorSystem:
    """
    世界行动者系统 — 管理所有独立于主角的势力

    每 Tick 推进所有 Actor 的独立行动。
    Actor 之间会互动: 敌对双方可能爆发冲突, 联盟可能破裂。
    主角只有达到对应的影响力层级, 才能感知到这些变化。
    """

    def __init__(self):
        self.actors: dict[str, WorldActor] = {}
        self._event_log: list = []
        self._action_templates = self._build_action_templates()

    def _build_action_templates(self) -> dict:
        """各维度可能的行为"""
        return {
            "economic": [
                ("经济扩张", "影响力", lambda a, r: {"economic": a.influence.get("military", 10) // 2}),
                ("贸易封锁", "敌对", lambda a, r: {"economic": -5} if r == "敌对" else {}),
                ("开设商路", "友好", lambda a, r: {"economic": 3} if r in ("友好","联盟") else {}),
            ],
            "political": [
                ("政治联姻", "友好", lambda a, r: {"political": 5} if r in ("友好","联盟") else {}),
                ("策反下属", "敌对", lambda a, r: {"political": -3} if r == "敌对" else {}),
                ("外交出访", "中立", lambda a, r: {"social": 3}),
            ],
            "military": [
                ("边境摩擦", "敌对", lambda a, r: {"military": -5} if r == "敌对" else {"military": -2}),
                ("军事演习", "中立", lambda a, r: {"military": 3}),
                ("调兵遣将", "中立", lambda a, r: {"military": 5}),
            ],
            "knowledge": [
                ("发现古遗迹", "中立", lambda a, r: {"knowledge": 8}),
                ("学术突破", "中立", lambda a, r: {"knowledge": 5}),
                ("技术外流", "敌对", lambda a, r: {"knowledge": -3}),
            ],
            "social": [
                ("发表演讲", "中立", lambda a, r: {"social": 4}),
                ("舆论战", "敌对", lambda a, r: {"social": -3, "political": -2} if r == "敌对" else {}),
            ],
            "mystical": [
                ("天象异变", "中立", lambda a, r: {"mystical": 6}),
                ("秘境探索", "中立", lambda a, r: {"mystical": 5, "knowledge": 3}),
                ("大能渡劫", "中立", lambda a, r: {"mystical": 10}),
            ],
        }

    def add_actor(self, actor: WorldActor):
        self.actors[actor.id] = actor

    def seed_default_actors(self):
        """生成默认的顶层世界行动者 (对标现实中的大国级实体)"""
        default_actors = [
            WorldActor(id="celestial_empire", name="天朝上国", type="势力",
                       tier=9, description="大陆中央的古老帝国, 底蕴深不可测",
                       influence={"economic": 85, "political": 90, "military": 80,
                                  "knowledge": 70, "social": 85, "mystical": 60}),
            WorldActor(id="northern_legion", name="北境军团", type="势力",
                       tier=8, description="极北之地的军事强国, 铁血善战",
                       influence={"economic": 40, "political": 60, "military": 95,
                                  "knowledge": 30, "social": 50, "mystical": 20}),
            WorldActor(id="southern_alliance", name="南境商盟", type="组织",
                       tier=7, description="南方诸国组成的商业联盟, 富甲天下",
                       influence={"economic": 90, "political": 50, "military": 30,
                                  "knowledge": 60, "social": 70, "mystical": 25}),
            WorldActor(id="ancient_sect", name="天道宗", type="组织",
                       tier=9, description="传承万年的修仙宗门, 超然世外",
                       influence={"economic": 40, "political": 30, "military": 70,
                                  "knowledge": 85, "social": 50, "mystical": 95}),
            WorldActor(id="dark_cult", name="暗影教", type="组织",
                       tier=7, description="行踪诡秘的邪教组织, 图谋不轨",
                       influence={"economic": 30, "political": 40, "military": 50,
                                  "knowledge": 40, "social": 60, "mystical": 75}),
        ]

        # 设置初始关系
        relationships = {
            ("celestial_empire", "northern_legion"): "敌对",
            ("celestial_empire", "southern_alliance"): "联盟",
            ("celestial_empire", "ancient_sect"): "友好",
            ("celestial_empire", "dark_cult"): "敌对",
            ("northern_legion", "southern_alliance"): "敌对",
            ("northern_legion", "ancient_sect"): "中立",
            ("northern_legion", "dark_cult"): "友好",
            ("southern_alliance", "ancient_sect"): "友好",
            ("southern_alliance", "dark_cult"): "中立",
            ("ancient_sect", "dark_cult"): "敌对",
        }

        for actor in default_actors:
            self.add_actor(actor)

        for (a, b), rel in relationships.items():
            if a in self.actors and b in self.actors:
                self.actors[a].relationships[b] = rel
                self.actors[b].relationships[a] = rel

        return default_actors

    def tick(self, day: int) -> list[dict]:
        """每日推进所有 Actor 的行动"""
        events = []
        for actor in list(self.actors.values()):
            if not actor.is_active:
                continue

            # 检查行动间隔
            interval = actor.tick_interval()
            if day - actor.last_action_day < interval:
                continue
            actor.last_action_day = day

            # 选择一个目标
            target_id = self._select_target(actor)
            rel = actor.relationships.get(target_id, "中立") if target_id else "中立"

            # 根据 Actor 的核心维度选择行为
            dim = actor.primary_dimension()
            templates = self._action_templates.get(dim, [])
            if not templates:
                continue

            chosen = random.choice(templates)
            action_name, target_rel_filter, effect_fn = chosen

            # 检查关系过滤条件
            if target_rel_filter != "中立" and rel != target_rel_filter and target_rel_filter != "任何":
                continue

            # 计算效果
            effects = effect_fn(actor, rel)
            if not effects:
                continue

            # 应用效果到 Actor 自身
            for k, v in effects.items():
                if k in actor.influence:
                    actor.influence[k] = max(1, min(100, actor.influence[k] + v))

            # 如果有目标, 影响目标 Actor
            target_actor = self.actors.get(target_id) if target_id else None
            if target_actor:
                for k, v in effects.items():
                    if k in target_actor.influence:
                        target_actor.influence[k] = max(1, min(100, target_actor.influence[k] - v))

            # 记录事件
            event = {
                "day": day,
                "actor": actor.name,
                "action": action_name,
                "dimension": dim,
                "target": target_actor.name if target_actor else "无",
                "effects": effects,
                "tier": actor.tier,
                "description": f"{actor.name} {action_name}" + (f" (针对{target_actor.name})" if target_actor else ""),
            }
            events.append(event)
            self._event_log.append(event)

            # 随机关系变化
            if random.random() < 0.05:  # 5%概率关系变化
                if target_actor:
                    old_rel = rel
                    new_rel = random.choice(["敌对", "中立", "友好", "联盟"])
                    actor.relationships[target_id] = new_rel
                    target_actor.relationships[actor.id] = new_rel
                    event["relationship_change"] = f"{old_rel}→{new_rel}"

        return events

    def _select_target(self, actor: WorldActor) -> Optional[str]:
        """选择一个互动目标"""
        candidates = [aid for aid in self.actors if aid != actor.id and self.actors[aid].is_active]
        if not candidates:
            return None

        # 优先选择关系极端的 (敌对或联盟)
        weighted = []
        for aid in candidates:
            rel = actor.relationships.get(aid, "中立")
            if rel == "敌对":
                weight = 3
            elif rel == "联盟":
                weight = 2
            elif rel == "友好":
                weight = 1.5
            else:
                weight = 0.5
            weighted.append((weight, aid))

        total_w = sum(w for w, _ in weighted)
        r = random.uniform(0, total_w)
        cumulative = 0
        for w, aid in weighted:
            cumulative += w
            if r <= cumulative:
                return aid
        return random.choice(candidates)

    def visible_events_for(self, char_influence: int) -> list[str]:
        """
        返回角色当前影响力层级能感知到的世界大事
        
        低层级角色: 只能感知到 tier ≤ 3 的事情
        高层级角色: 能感知到 tier ≤ 7 的事情
        顶层角色: 能感知到全部
        """
        threshold = char_influence // 10  # influence=30 → threshold=3
        visible = []
        for ev in self._event_log[-20:]:  # 最近 20 条
            if ev.get("tier", 5) <= threshold:
                visible.append(ev["description"])
        return visible

    def from_user_config(self, configs: list[dict]) -> None:
        """从用户自定义配置加载 Actor
        支持同时含有 LLM 生成的 actor 和用户自定义的 actor。同名则覆盖。
        """
        for item in configs:
            name = item.get("name", "")
            if not name:
                continue
            aid = item.get("id", name.lower().replace(" ", "_")[:20])
            inf = item.get("influence", {})
            actor = WorldActor(
                id=aid,
                name=name,
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
            for target_name, rel in item.get("relationships", {}).items():
                target_id = target_name.lower().replace(" ", "_")[:20]
                actor.relationships[target_id] = rel
            # 覆盖同名
            existing = [k for k, v in self.actors.items() if v.name == name]
            for k in existing:
                del self.actors[k]
            self.add_actor(actor)

    def get_actor_status_text(self) -> str:
        """世界格局简报 (给 LLM 和高层级角色感知用)"""
        active = [a for a in self.actors.values() if a.is_active and a.tier >= 5]
        if not active:
            return ""
        lines = ["世界格局:"]
        for a in active:
            dim = a.primary_dimension()
            lines.append(f"  {a.name} (T{a.tier}) — 核心:{dim}={a.influence.get(dim, 0)}")
            rels = [f"{k}:{v}" for k, v in list(a.relationships.items())[:3]]
            if rels:
                lines.append(f"    关系: {', '.join(rels)}")
        return "\n".join(lines)
