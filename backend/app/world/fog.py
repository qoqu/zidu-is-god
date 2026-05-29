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
世界迷雾 — 每个角色只能看到自己认知范围内的世界

店小二的世界 = 几张桌子 + 客人的只言片语
国王的世界  = 整个王国 + 外交 + 战事
两个人都不知道龙脊山脉有龙在苏醒 — 除非消息传到他们耳中

核心机制:
  - WorldFogManager 管理全局知识库 (全部世界观)
  - 每个角色有自己的 FogMap: {location_id: "known"/"heard_of"/"unknown"}
  - 感知层只返回角色已"点亮"的区域
  - 新区域通过探索、传闻、事件触发来点亮
  - 离角色很远、从未听说过的事件 — 直接不进入 prompt
"""

from dataclasses import dataclass, field
from typing import Optional


# ─── 迷雾状态 ─────────────────────────────────────────────

class FogState:
    """角色对某事物的认知状态"""
    UNKNOWN = 0       # 完全不知道
    HEARD_OF = 1      # 听说过 (只有名字/谣言)
    VISITED = 2       # 去过 (知道详情)
    KNOWLEDGE = 3     # 深入了解 (知道内幕/秘密)


# ─── 角色的个人迷雾地图 ────────────────────────────────────

class FogMap:
    """
    每个角色独有的迷雾地图

    角色知道什么、不知道什么，全由这张地图决定。
    地图是慢慢"点亮"的——去一个新地方、听一个传闻、调查一个秘密。
    """

    def __init__(self, char_id: str = ""):
        self.char_id = char_id

        # 地点迷雾: {location_id: FogState}
        self.locations: dict = {}

        # 势力迷雾: {faction_id: FogState}
        self.factions: dict = {}

        # 角色迷雾: {character_id: FogState}
        self.chars: dict = {}

        # 世界事件迷雾: {event_id: FogState}
        self.events: dict = {}

        # 已听说过的传闻 (去重)
        self.heard_rumors: set = set()

    def discover_location(self, loc_id: str, state: int = FogState.VISITED):
        """发现一个新地点"""
        if loc_id not in self.locations or self.locations[loc_id] < state:
            self.locations[loc_id] = state

    def hear_about_location(self, loc_id: str):
        """听说某个地点 (不精确信息)"""
        self.discover_location(loc_id, FogState.HEARD_OF)

    def discover_faction(self, fac_id: str, state: int = FogState.HEARD_OF):
        """发现一个新势力"""
        if fac_id not in self.factions or self.factions[fac_id] < state:
            self.factions[fac_id] = state

    def hear_rumor(self, rumor_text: str) -> bool:
        """听到一条传闻, 返回是否是新消息"""
        if rumor_text not in self.heard_rumors:
            self.heard_rumors.add(rumor_text)
            return True
        return False

    def is_location_known(self, loc_id: str) -> bool:
        """是否知道这个地点"""
        return self.locations.get(loc_id, FogState.UNKNOWN) >= FogState.HEARD_OF

    def is_faction_known(self, fac_id: str) -> bool:
        return self.factions.get(fac_id, FogState.UNKNOWN) >= FogState.HEARD_OF

    def visible_locations_text(self, world, max_count: int = 5) -> str:
        """角色当前知道的地点列表 (限制数量避免 prompt 爆炸)"""
        known = [(lid, s) for lid, s in self.locations.items() if s >= FogState.HEARD_OF]
        known.sort(key=lambda x: -x[1])
        lines = []
        for lid, state in known[:max_count]:
            loc = world.locations.get(lid) if hasattr(world, 'locations') else None
            name = loc.name if loc else lid
            tag = "【熟悉】" if state >= FogState.VISITED else "【听闻】"
            lines.append(f"  {tag} {name}")
        return "\n".join(lines)

    def visible_factions_text(self, world, max_count: int = 3) -> str:
        known = [(fid, s) for fid, s in self.factions.items() if s >= FogState.HEARD_OF]
        known.sort(key=lambda x: -x[1])
        lines = []
        for fid, state in known[:max_count]:
            fac = world.factions.get(fid) if hasattr(world, 'factions') else None
            name = fac.name if fac else fid
            tag = "【了解】" if state >= FogState.KNOWLEDGE else "【听说】"
            lines.append(f"  {tag} {name}")
        return "\n".join(lines)

    def recent_rumors_text(self, max_lines: int = 3) -> str:
        """最近听到的传闻"""
        recent = list(self.heard_rumors)[-max_lines:]
        return "\n".join(f"  - {r[:60]}" for r in recent) if recent else ""


# ─── 世界迷雾管理器 ───────────────────────────────────────

class WorldFogManager:
    """
    世界迷雾管理器 — 管理所有角色的认知边界

    职责:
    1. 迷雾展开: 角色到新地点 → 自动点亮周边
    2. 传闻广播: 世界事件/谣言 → 传播到相关角色的迷雾中
    3. 感知过滤: 角色只能感知已点亮的区域
    4. 渐进揭示: 世界观不一次性展开, 随着故事推进慢慢揭示
    """

    def __init__(self, world):
        self.world = world
        self.fog_maps: dict[str, FogMap] = {}  # {char_id: FogMap}

    def get_fog(self, char_id: str) -> FogMap:
        """获取角色的迷雾地图 (不存在则创建)"""
        if char_id not in self.fog_maps:
            self.fog_maps[char_id] = FogMap(char_id=char_id)
        return self.fog_maps[char_id]

    def initialize_char(self, char_id: str, location_id: str):
        """角色初始出生点 — 点亮所在地及周边"""
        fog = self.get_fog(char_id)
        # 出生点: 完全熟悉
        fog.discover_location(location_id, FogState.VISITED)

        # 相邻地点: 听说过
        loc = self.world.locations.get(location_id)
        if loc and hasattr(loc, 'nearby'):
            for nearby in loc.nearby:
                fog.discover_location(nearby, FogState.HEARD_OF)

        # 本地势力: 听说
        for fid, fac in getattr(self.world, 'factions', {}).items():
            if hasattr(fac, 'home_location') and fac.home_location == location_id:
                fog.discover_faction(fid, FogState.HEARD_OF)

    def discover_on_arrival(self, char_id: str, location_id: str):
        """角色到达新地点 — 点亮该地 + 周边"""
        fog = self.get_fog(char_id)
        fog.discover_location(location_id, FogState.VISITED)

        # 相邻地点: 由 VISITED 降级为 HEARD_OF
        loc = self.world.locations.get(location_id)
        if loc and hasattr(loc, 'nearby'):
            for nearby in loc.nearby:
                if nearby != location_id:
                    fog.discover_location(nearby, FogState.HEARD_OF)

    def broadcast_rumor(self, rumor_text: str, source_location: str,
                        radius: str = "local", tier: int = 5):
        """
        广播一条消息 — 只有满足条件的角色能收到

        Args:
            rumor_text: 消息内容
            source_location: 消息来源地
            radius: 传播范围 (personal/local/sect/nation/world)
            tier: 消息层级 (1-10), 越高越机密
        """
        for char_id, fog in self.fog_maps.items():
            char = None
            for c in getattr(self.world, '_characters', []):
                if c.id == char_id:
                    char = c
                    break
            if not char:
                continue

            # 判断角色是否能收到这条消息
            char_tier = 1
            if hasattr(char, 'stats') and hasattr(char.stats, 'influence') and char.stats.influence:
                char_tier = getattr(char.stats.influence, char.stats.influence.primary(), 1) // 10

            if char_tier < tier - 2:
                continue  # 层级不够, 收不到

            # 判断距离
            if radius == "world":
                fog.hear_rumor(rumor_text)
            elif radius == "nation" and char_tier >= 5:
                fog.hear_rumor(rumor_text)
            elif radius == "sect":
                # 同势力或同地点能收到
                if char.current_location == source_location or char_tier >= 3:
                    fog.hear_rumor(rumor_text)
            elif radius == "local":
                if char.current_location == source_location:
                    fog.hear_rumor(rumor_text)

    def filter_perception(self, char_id: str, full_perception: str) -> str:
        """
        按迷雾过滤感知文本 — 去掉角色不该知道的信息

        这是核心优化点: 将 prompt 中角色不该知道的内容裁剪掉。
        """
        fog = self.get_fog(char_id)
        lines = full_perception.split("\n")
        filtered = []

        for line in lines:
            # 传闻: 只有角色听说过的才保留
            if line.startswith("传闻:") or "传闻" in line:
                # 替换为角色实际听到的传闻
                rumors = fog.recent_rumors_text()
                if rumors:
                    filtered.append("传闻:")
                    filtered.append(rumors)
                continue

            # 天下大事: 只有高层级角色才能感知
            if "天下大事" in line or "世界态势" in line:
                # 检查角色层级
                char = None
                for c in getattr(self.world, '_characters', []):
                    if c.id == char_id:
                        char = c
                        break
                if char and hasattr(char, 'stats') and char.stats.influence:
                    prim = char.stats.influence.primary()
                    val = getattr(char.stats.influence, prim, 1)
                    if val < 30:
                        continue  # 低层级角色看不到天下大事
                filtered.append(line)
                continue

            filtered.append(line)

        return "\n".join(filtered)
