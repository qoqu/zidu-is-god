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
角色模型 — 数据模型
"""

from dataclasses import dataclass, field
from typing import Optional


# ─── 情绪系统 ───────────────────────────────────────────────

@dataclass
class EmotionalState:
    """
    两层情绪模型
    mood (心境): 慢变量, 跨场景延续, 每章变化一次
    emotion (即时情绪): 快变量, 每 Beat 更新
    """
    # --- mood ---
    mood_label: str = "平静"       # 平静/焦虑/低沉/昂扬/警惕/绝望/希望
    mood_intensity: float = 0.5    # 0~1

    # --- emotion ---
    valence: float = 0.0           # -1.0 ~ +1.0 (消极↔积极)
    arousal: float = 0.0           # -1.0 ~ +1.0 (平静↔激动)
    dominant_emotion: str = ""     # 愤怒/喜悦/恐惧/悲伤/惊讶/厌恶/羞愧/期待

    # --- 人格调节参数 ---
    arousal_speed: float = 1.0     # >1 = 情绪起伏剧烈, <1 = 沉稳
    recovery_rate: float = 0.3     # 每轮回归基线的速度

    def update_by_event(self, event):
        """每轮事件后更新情绪"""
        event_type = getattr(event, "action_type", "")

        if event_type == "ACT" and getattr(event, "outcome", ""):
            self.valence = min(1.0, self.valence + 0.3 * self.arousal_speed)
            self.arousal = min(1.0, self.arousal + 0.2 * self.arousal_speed)
        elif event_type in ("OBSERVE",) and "威胁" in getattr(event, "content", ""):
            self.valence = max(-1.0, self.valence - 0.4 * self.arousal_speed)
            self.arousal = min(1.0, self.arousal + 0.3 * self.arousal_speed)
        elif event_type == "INNER" and any(w in getattr(event, "content", "") for w in ["悲伤", "失去", "亡"]):
            self.valence = max(-1.0, self.valence - 0.2 * self.arousal_speed)
            self.arousal = max(-1.0, self.arousal - 0.2 * self.arousal_speed)

        # 回归基线
        self.valence += (0.0 - self.valence) * self.recovery_rate
        self.arousal += (0.0 - self.arousal) * self.recovery_rate
        self.dominant_emotion = self._map_emotion(self.valence, self.arousal)

    def decay_to_mood(self):
        """每章结束时, 本章平均情绪沉淀为新的 mood"""
        if self.valence > 0.3 and self.arousal > 0:
            self.mood_label = "昂扬"
        elif self.valence < -0.3 and self.arousal > 0:
            self.mood_label = "焦虑"
        elif self.valence < -0.3 and self.arousal < 0:
            self.mood_label = "低沉"
        elif abs(self.valence) < 0.2 and abs(self.arousal) < 0.2:
            self.mood_label = "平静"
        self.mood_intensity = min(1.0, abs(self.valence) * 0.5 + abs(self.arousal) * 0.5)

    def format_for_prompt(self) -> str:
        if self.dominant_emotion:
            return f"心境: {self.mood_label}({self.mood_intensity:.1f}), 情绪: {self.dominant_emotion}"
        return f"心境: {self.mood_label}({self.mood_intensity:.1f})"

    def _map_emotion(self, v: float, a: float) -> str:
        if abs(v) < 0.15 and abs(a) < 0.15:
            return ""
        if v > 0.3 and a > 0.3:
            return "喜悦"
        if v < -0.3 and a > 0.3:
            return "愤怒" if a > 0.5 else "恐惧"
        if v < -0.3 and a < -0.3:
            return "悲伤"
        if a > 0.5 and abs(v) < 0.3:
            return "惊讶"
        if v < -0.5 and abs(a) < 0.2:
            return "厌恶"
        if v > 0 and a < -0.2:
            return "期待"
        return self.dominant_emotion or ""


# ─── 角色核心模型 ───────────────────────────────────────────

@dataclass
class CharIdentity:
    name: str = ""
    age: int = 0
    gender: str = ""
    appearance: str = ""
    occupation: str = ""


@dataclass
class CharPersonality:
    traits: list = field(default_factory=list)         # ["隐忍", "骄傲", "重情义"]
    speaking_style: str = ""                           # "短促有力"
    decision_bias: dict = field(default_factory=dict)  # {"利益": 0.6, "感情": 0.3, "原则": 0.1}


@dataclass
class CharMotivation:
    deep_desire: str = ""        # 深层欲望
    short_term_goals: list = field(default_factory=list)  # 当前短期目标
    long_term_goal: str = ""     # 长期目标
    fear: str = ""               # 恐惧


@dataclass
class GrowthArc:
    starting_state: str = ""
    intended_transformation: str = ""
    current_progress: float = 0.0   # 0~1
    key_turning_points: list = field(default_factory=list)


@dataclass
class Relationship:
    affinity: float = 0.0    # -100 ~ 100
    trust: float = 0.0       # 0 ~ 100
    history: list = field(default_factory=list)


@dataclass
class MemoryItem:
    id: str = ""
    timestamp: str = ""
    event: str = ""
    importance: float = 0.5   # 0~1
    emotion: str = ""
    embedding: list = field(default_factory=list)


@dataclass
class Goal:
    description: str = ""
    deadline_chapter: int = 0
    completed: bool = False


@dataclass
class StatusEffect:
    name: str = ""
    duration_beats: int = 0
    description: str = ""


# ─── ★★★ 新增: 数值/伤势系统 ─────────────────────────────

@dataclass
class Injury:
    """伤势"""
    part: str = ""              # 左臂/右腿/胸口/头部
    severity: int = 1           # 1轻/2中/3重
    effect: str = ""            # "攻击-20%"/"移动受限"
    remaining_days: int = 3     # 恢复所需天数

    def to_prompt(self) -> str:
        labels = {1: "轻伤", 2: "中伤", 3: "重伤"}
        return f"{self.part}{labels.get(self.severity, '伤')}({self.effect}, 还需{self.remaining_days}天)"



@dataclass
class Influence:
    """六维世界影响力系统
    
    每个维度独立, 一个角色可以是"富可敌国但毫无武力"的商人,
    也可以是"武力通天但不懂经济"的剑仙。
    
    维度:
      economic  — 财富/商业 → 影响物价/贸易/就业
      political — 政治/权力 → 影响法令/外交/权力结构
      military  — 武力/军事 → 影响安全/领土/战争
      knowledge — 知识/学术 → 影响技术/修炼突破/发现
      social    — 声望/舆论 → 影响民心/风气/谣言可信度
      mystical  — 超凡/修为 → 影响灵气/天象/秘境
    
    作用半径: personal / local / sect / regional / national / world
    """
    economic: int = 1
    political: int = 1
    military: int = 1
    knowledge: int = 1
    social: int = 1
    mystical: int = 1
    radii: dict = None

    def __post_init__(self):
        if self.radii is None:
            self.radii = {
                "economic": "personal", "political": "personal",
                "military": "personal", "knowledge": "personal",
                "social": "personal", "mystical": "personal",
            }

    def primary(self) -> str:
        dims = ["economic","political","military","knowledge","social","mystical"]
        return max(dims, key=lambda d: getattr(self, d))

    def top_three(self) -> list:
        dims = ["economic","political","military","knowledge","social","mystical"]
        scored = [(d, getattr(self, d)) for d in dims]
        scored.sort(key=lambda x: -x[1])
        return [(d, v) for d, v in scored if v > 1][:3]

    def summary(self) -> str:
        label = {"economic":"财富","political":"权谋","military":"武力",
                 "knowledge":"学识","social":"声望","mystical":"超凡"}
        top = self.top_three()
        if not top:
            return "影响力微末"
        return " | ".join(f"{label.get(d,d)}({v})" for d, v in top)


@dataclass
class ResourceItem:
    """
    资源账本 — 一个物品/装备/道具

    id: 唯一标识
    name: 名称
    type: weapon/armor/potion/scroll/material/key/treasure/quest
    description: 描述
    owner: 当前持有者 id
    chapter_obtained: 获得的章节
    durability: 耐久度 (使用类物品)
    quantity: 数量 (消耗品类)
    status: active/consumed/lost/destroyed
    properties: 自定义属性 (攻击力/防御力/效果等)
    """
    id: str = ""
    name: str = ""
    type: str = "material"
    description: str = ""
    owner: str = ""
    chapter_obtained: int = 0
    durability: int = -1       # -1 = 无限
    quantity: int = 1
    status: str = "active"
    properties: dict = field(default_factory=dict)


@dataclass
class ResourceLedger:
    """
    资源账本 — 管理角色拥有的所有物品
    
    区别于简单的 items dict, 它的核心功能:
    - 物品有生命周期 (获得/使用/消耗/丢失/销毁)
    - 物品有状态追踪 (耐久/数量/是否可用)
    - 物品可交易/转移 (同时更新双方账本)
    """
    items: dict = field(default_factory=dict)  # {item_id: ResourceItem}
    _id_counter: int = 0

    def add(self, name: str, type: str = "material",
            description: str = "", chapter: int = 0,
            quantity: int = 1, durability: int = -1,
            properties: dict = None) -> str:
        self._id_counter += 1
        item_id = f"item_{self._id_counter:04d}"
        item = ResourceItem(
            id=item_id,
            name=name,
            type=type,
            description=description,
            owner="",
            chapter_obtained=chapter,
            quantity=quantity,
            durability=durability,
            properties=properties or {},
        )
        self.items[item_id] = item
        return item_id

    def transfer_to(self, item_id: str, new_owner: str) -> bool:
        if item_id not in self.items:
            return False
        self.items[item_id].owner = new_owner
        return True

    def consume(self, item_id: str, amount: int = 1) -> bool:
        if item_id not in self.items:
            return False
        item = self.items[item_id]
        if item.quantity < amount:
            return False
        item.quantity -= amount
        if item.quantity <= 0:
            item.status = "consumed"
        return True

    def damage(self, item_id: str, amount: int = 1):
        if item_id not in self.items:
            return
        item = self.items[item_id]
        if item.durability < 0:
            return
        item.durability -= amount
        if item.durability <= 0:
            item.status = "destroyed"

    def get_active(self) -> list:
        return [i for i in self.items.values() if i.status == "active"]

    def get_by_type(self, type: str) -> list:
        return [i for i in self.items.values() if i.type == type and i.status == "active"]

    def summary(self) -> str:
        active = self.get_active()
        if not active:
            return "无"
        by_type = {}
        for item in active:
            by_type.setdefault(item.type, []).append(item.name)
        parts = []
        for t, names in by_type.items():
            parts.append(f"{t}:{','.join(set(names))}")
        return " | ".join(parts)


@dataclass
class CharacterStats:
    """
    角色数值系统 — 驱动行为的底层引擎
    """
    # ── 核心数值 (0~100) ──
    hp: int = 100
    max_hp: int = 100
    stamina: int = 100          # 体力 (行动消耗, 休息恢复)
    max_stamina: int = 100

    # ── 社会属性 ──
    wealth: int = 0             # 灵石/金币
    reputation: int = 50        # 声望 0~100
    social_status: int = 10     # 地位 (外门10, 内门30, 长老70)

    # ── 修为 (针对修仙题材可替换) ──
    cultivation: int = 10       # 修为等级
    cultivation_speed: float = 1.0

    # ── 伤势 ──
    injuries: list = field(default_factory=list)  # [Injury]

    # ── 需求 (0~100, 越高越迫切) ──
    needs: dict = field(default_factory=lambda: {
        "rest": 0,
        "safety": 0,
        "social": 10,
        "achievement": 20,
    })

    # ── 资源 (角色随身携带) ──
    ledger: ResourceLedger = field(default_factory=ResourceLedger)
    influence: Influence = field(default_factory=Influence)


    def daily_decay(self):
        """每日自然消耗"""
        self.stamina = max(0, self.stamina - 15)
        self.needs["rest"] = min(100, self.needs["rest"] + 20)
        # 伤势缓慢恢复
        for injury in self.injuries[:]:
            injury.remaining_days -= 1
            if injury.remaining_days <= 0:
                self.injuries.remove(injury)
                self.hp = min(self.max_hp, self.hp + 10)

    def apply_damage(self, amount: int, part: str = ""):
        self.hp = max(0, self.hp - amount)
        if amount >= 20:
            self.injuries.append(Injury(
                part=part or "身体",
                severity=2 if amount < 40 else 3,
                effect=f"hp-{amount}",
            ))
        self.needs["safety"] = min(100, self.needs["safety"] + amount)

    def rest(self, hours: int = 4):
        self.stamina = min(self.max_stamina, self.stamina + 20 * hours)
        self.needs["rest"] = max(0, self.needs["rest"] - 15 * hours)
        self.hp = min(self.max_hp, self.hp + 5 * hours)

    def get_dominant_need(self) -> tuple[str, int]:
        """当前最迫切的需求 (名称, 值)"""
        return max(self.needs.items(), key=lambda x: x[1])

    def need_urgency_text(self) -> str:
        """需求紧迫程度文本 (拼入决策 prompt)"""
        lines = []
        need_names = {"rest": "休息", "safety": "安全", "social": "社交", "achievement": "成就"}
        for key, name in need_names.items():
            val = self.needs.get(key, 0)
            if val >= 70:
                lines.append(f"  亟需{name}({val}/100)")
            elif val >= 40:
                lines.append(f"  需要{name}({val}/100)")
        return "\n".join(lines)

    def status_summary(self) -> str:
        """状态摘要 (拼入决策 prompt)"""
        parts = [f"体力{self.stamina}/{self.max_stamina}", f"灵石{self.wealth}"]
        if self.injuries:
            parts.append(f"伤势:{len(self.injuries)}处")
        return ", ".join(parts)


class Character:
    def __init__(
        self,
        id: str = "",
        name: str = "",
        identity: Optional[CharIdentity] = None,
        personality: Optional[CharPersonality] = None,
        motivation: Optional[CharMotivation] = None,
        growth_arc: Optional[GrowthArc] = None,
    ):
        self.id = id
        self.name = name
        self.identity = identity or CharIdentity()
        self.personality = personality or CharPersonality()
        self.motivation = motivation or CharMotivation()
        self.growth_arc = growth_arc or GrowthArc()
        self.relationships: dict = {}          # {char_id: Relationship}
        from app.characters.memory import MemorySystem
        self.memory: MemorySystem = MemorySystem(name)
        self.skills: dict = {}                 # {"剑术": 45}
        self.secrets: list = []                # 角色不知道但系统知道的信息
        self.discovered_secrets: list = []     # 已发现的秘密
        self.emotional_state: EmotionalState = EmotionalState()
        self.stats: CharacterStats = CharacterStats()   # ★★★ 新增
        self.current_location: str = ""
        self.current_goals: list = []          # [Goal]
        self.status_effects: list = []         # [StatusEffect]

    def get_current_goals(self) -> list:
        return [g for g in self.current_goals if not g.completed]

    def get_danger_level(self) -> float:
        """危险程度 0~1, 现在包含 stats"""
        danger = 0.0
        # 伤势
        for injury in self.stats.injuries:
            danger += injury.severity * 0.15
        # 低体力
        if self.stats.stamina < 30:
            danger += 0.2
        # 低 hp
        if self.stats.hp < 50:
            danger += 0.3
        # 状态效果
        for effect in self.status_effects:
            if effect.name in ("中毒", "被追捕"):
                danger += 0.3
        return min(danger, 1.0)

    def perceive(self, scene: dict, relationships: dict, memories: list) -> dict:
        """构建角色当前的感知上下文"""
        return {
            "location": scene.get("location_name", ""),
            "time": scene.get("time", ""),
            "present_chars": scene.get("present_chars", []),
            "relevant_relations": {
                cid: relationships.get(cid, Relationship()).affinity
                for cid in scene.get("present_char_ids", [])
                if cid != self.id
            },
            "recent_memories": [m.event for m in memories[-3:]] if memories else [],
            "emotional_state": self.emotional_state.format_for_prompt(),
        }
