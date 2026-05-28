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
世界毁灭威胁系统 — 世界末日倒计时

现实的启示: 中美的核武库足以毁灭地球几十次,
修仙世界的古神封印可能松动, 灵气可能枯竭。
世界从来不安全, 只是毁灭还没来。

核心模型: 多条并行的威胁轨道, 各自独立增长。
高影响力角色的行为可能加快或延缓某条轨道。
当某条轨道达到 100%, 对应灾难触发。
"""

from dataclasses import dataclass, field
from typing import Optional
import random


@dataclass
class ThreatTrack:
    """
    一条毁灭威胁线

    像一根绷紧的弦——日常缓慢绷紧, 特定事件猛然拉动,
    高影响力角色可能剪断它, 也可能加速它的断裂。
    """

    # ── 身份 ──
    id: str                          # "nuclear_war" / "ancient_god" / "plague"
    name: str                        # 显示名
    description: str                 # 描述

    # ── 关联的影响力维度 ──
    # 哪些维度的行为会加速/减缓这条威胁
    accelerates_by: list = field(default_factory=lambda: ["military", "mystical"])
    decelerates_by: list = field(default_factory=list)

    # ── 当前状态 0~1 ──
    level: float = 0.1               # 当前值
    natural_growth: float = 0.005    # 每日自然增长

    # ── 触发条件 ──
    trigger_threshold: float = 0.95  # 达到此值触发
    triggered: bool = False
    triggered_at_day: int = 0
    trigger_cascade: bool = False     # 触发后是否加速其他威胁

    # ── 触发效果 ──
    effects: dict = field(default_factory=lambda: {
        "danger_level": "+100",
        "description": "世界陷入了危机",
    })

    def tick(self, day: int, world_state: dict):
        """每日推进"""
        if self.triggered:
            return

        # 自然增长
        self.level = min(1.0, self.level + self.natural_growth)

        # 检查触发
        if self.level >= self.trigger_threshold:
            self.triggered = True
            self.triggered_at_day = day
            if self.trigger_cascade:
                world_state["cascade_trigger"] = self.id

    def influence(self, dimension: str, weight: int, direction: int = 1) -> str:
        """
        角色行为影响威胁值

        Args:
            dimension: 影响力维度
            weight: 影响力权重
            direction: 1=加速, -1=减缓

        Returns: 描述文本
        """
        if self.triggered:
            return ""

        impact = weight / 500.0  # weight=50 → 0.1, weight=100 → 0.2
        if dimension in self.accelerates_by:
            self.level = min(1.0, max(0.0, self.level + impact * direction))
        elif dimension in self.decelerates_by:
            self.level = min(1.0, max(0.0, self.level - impact * direction))
        else:
            return ""

        return f"毁灭威胁[{self.name}] {'上升' if direction > 0 else '下降'}至 {self.level:.0%}"

    def status_text(self) -> str:
        """给 LLM 感知用的状态文本"""
        if self.triggered:
            return f"⚠️ {self.name}已爆发: {self.effects.get('description', '')}"
        if self.level > 0.8:
            return f"🔥 {self.name}迫在眉睫({self.level:.0%})"
        if self.level > 0.5:
            return f"⚡ {self.name}日益严峻({self.level:.0%})"
        if self.level > 0.2:
            return f"🌊 {self.name}暗流涌动({self.level:.0%})"
        return ""


# ─── 预设威胁模板 ─────────────────────────────────────────

THREAT_TEMPLATES = {
    # ── 修仙世界 ──
    "ancient_god": ThreatTrack(
        id="ancient_god",
        name="古神苏醒",
        description="上古封印在时间侵蚀下逐渐松动, 一旦古神归来, 生灵涂炭",
        accelerates_by=["mystical", "military"],
        decelerates_by=["knowledge"],
        natural_growth=0.003,
        trigger_threshold=0.95,
        trigger_cascade=True,
        effects={"danger_level": "+100", "description": "古神的低语回荡在天地之间"},
    ),
    "qi_depletion": ThreatTrack(
        id="qi_depletion",
        name="灵气枯竭",
        description="天地灵气逐年稀薄, 高阶修士将无以为继",
        accelerates_by=["mystical", "economic"],
        decelerates_by=["knowledge", "social"],
        natural_growth=0.002,
        trigger_threshold=1.0,
        effects={"danger_level": "+50", "description": "灵气浓度降至临界点"},
    ),
    "demonic_tide": ThreatTrack(
        id="demonic_tide",
        name="魔潮",
        description="域外魔族虎视眈眈, 空间壁垒日渐薄弱",
        accelerates_by=["mystical", "military"],
        decelerates_by=["political", "military"],
        natural_growth=0.004,
        trigger_threshold=0.9,
        trigger_cascade=True,
        effects={"danger_level": "+80", "description": "魔潮已冲破空间壁垒"},
    ),
    # ── 现实世界 ──
    "nuclear_war": ThreatTrack(
        id="nuclear_war",
        name="核战争",
        description="大国核对峙, 一旦擦枪走火, 世界将陷入核冬天",
        accelerates_by=["political", "military"],
        decelerates_by=["economic", "knowledge", "social"],
        natural_growth=0.003,
        trigger_threshold=0.95,
        trigger_cascade=True,
        effects={"danger_level": "+200", "description": "核弹升空, 世界末日降临"},
    ),
    "climate_breakdown": ThreatTrack(
        id="climate_breakdown",
        name="气候崩溃",
        description="极端天气频发, 生态系统濒临崩溃",
        accelerates_by=["economic"],
        decelerates_by=["knowledge", "political"],
        natural_growth=0.002,
        trigger_threshold=1.0,
        effects={"danger_level": "+40", "description": "气候系统全面崩溃"},
    ),
    "pandemic": ThreatTrack(
        id="pandemic",
        name="大瘟疫",
        description="新型致命病毒在全球蔓延",
        accelerates_by=["social", "economic"],
        decelerates_by=["knowledge", "political"],
        natural_growth=0.003,
        trigger_threshold=0.9,
        effects={"danger_level": "+60", "description": "瘟疫失控, 尸横遍野"},
    ),
    "ai_uprising": ThreatTrack(
        id="ai_uprising",
        name="AI觉醒",
        description="人工智能发展失控, 可能取代人类文明",
        accelerates_by=["knowledge", "economic"],
        decelerates_by=["political", "social"],
        natural_growth=0.004,
        trigger_threshold=1.0,
        effects={"danger_level": "+70", "description": "AI获得自我意识"},
    ),
}


class WorldThreatSystem:
    """
    世界毁灭威胁系统

    多条独立的威胁轨道并行推进:
    - 日常缓慢增长 (世界总是趋向混乱)
    - 高影响力角色加速/减缓 (权重越高影响越大)
    - 达到阈值触发灾难
    - 一条触发可能级联触发其他 (threat_cascade)
    """

    def __init__(self, active_threats: list[str] = None):
        """
        Args:
            active_threats: 活跃的威胁id列表, None=全部激活
        """
        self.tracks: dict[str, ThreatTrack] = {}
        ids = active_threats or list(THREAT_TEMPLATES.keys())
        for tid in ids:
            if tid in THREAT_TEMPLATES:
                t = THREAT_TEMPLATES[tid]
                self.tracks[tid] = ThreatTrack(
                    id=t.id, name=t.name, description=t.description,
                    accelerates_by=list(t.accelerates_by),
                    decelerates_by=list(t.decelerates_by),
                    natural_growth=t.natural_growth,
                    trigger_threshold=t.trigger_threshold,
                    trigger_cascade=t.trigger_cascade,
                    effects=dict(t.effects),
                )

    def tick(self, day: int, world_state: dict) -> list[str]:
        """每日推进所有威胁线, 返回新触发的事件"""
        events = []
        for track in self.tracks.values():
            track.tick(day, world_state)
            if track.triggered and track.triggered_at_day == day:
                events.append(f"🔥 毁灭威胁[{track.name}] 爆发! {track.effects.get('description', '')}")

        # 级联触发: 一条威胁爆发加速其他
        cascade = world_state.pop("cascade_trigger", None)
        if cascade:
            for track in self.tracks.values():
                if not track.triggered and track.id != cascade:
                    boost = 0.15 + random.random() * 0.1
                    track.level = min(1.0, track.level + boost)
                    events.append(f"💥 级联: {cascade}爆发导致[{track.name}]恶化(+{boost:.0%})")

        return events

    def influence(self, dimension: str, weight: int, direction: int = 1) -> list[str]:
        """角色行为影响所有相关威胁线"""
        results = []
        for track in self.tracks.values():
            text = track.influence(dimension, weight, direction)
            if text:
                results.append(text)
        return results

    def status_for_perception(self) -> str:
        """给 LLM 感知的世界威胁状态"""
        texts = [t.status_text() for t in self.tracks.values() if t.level > 0.2 or t.triggered]
        return "\n".join(texts) if texts else ""

    def get_active_threats(self) -> list[ThreatTrack]:
        """获取活跃的威胁线"""
        return [t for t in self.tracks.values() if t.level > 0.1]
