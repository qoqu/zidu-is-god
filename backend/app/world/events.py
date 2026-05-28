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
世界自主演化 — 世界随机事件
"""

import random


EVENT_TEMPLATES = [
    # ── 天灾 ──
    {
        "type": "disaster",
        "title": "妖兽潮",
        "desc": "大批妖兽从{location}方向涌来, 警戒级别提升",
        "severity": 4,
        "locations_affected": 2,
        "duration_days": 5,
        "effects": {"danger_level": "+30", "travel_blocked": True},
    },
    {
        "type": "disaster",
        "title": "地动",
        "desc": "{location}一带发生地动, 一些建筑受损",
        "severity": 3,
        "locations_affected": 1,
        "duration_days": 2,
        "effects": {"building_damage": True, "danger_level": "+10"},
    },
    # ── 奇遇 ──
    {
        "type": "opportunity",
        "title": "秘境开启",
        "desc": "传闻{location}附近出现秘境入口, 各方势力闻风而动",
        "severity": 5,
        "locations_affected": 1,
        "duration_days": 10,
        "effects": {"opportunity": "秘境探索"},
    },
    {
        "type": "opportunity",
        "title": "拍卖会",
        "desc": "{location}将举办大型拍卖会, 多件珍品亮相",
        "severity": 3,
        "locations_affected": 1,
        "duration_days": 3,
        "effects": {"opportunity": "拍卖"},
    },
    # ── 大势变动 ──
    {
        "type": "faction",
        "title": "势力冲突",
        "desc": "{location}周边两大势力摩擦升级, 小规模冲突不断",
        "severity": 3,
        "locations_affected": 2,
        "duration_days": 7,
        "effects": {"danger_level": "+20", "faction_tension": True},
    },
    {
        "type": "faction",
        "title": "使者到访",
        "desc": "来自远方的使者抵达{location}, 似乎有要事相商",
        "severity": 2,
        "locations_affected": 1,
        "duration_days": 3,
        "effects": {"diplomatic_event": True},
    },
    # ── 日常 ──
    {
        "type": "celebration",
        "title": "节庆",
        "desc": "{location}正在举办一年一度的庆典, 热闹非凡",
        "severity": 1,
        "locations_affected": 1,
        "duration_days": 3,
        "effects": {"mood_bonus": "+0.2", "trade_boost": True},
    },
    {
        "type": "celebration",
        "title": "丰收",
        "desc": "{location}一带今年收成极好, 市面繁荣",
        "severity": 1,
        "locations_affected": 1,
        "duration_days": 5,
        "effects": {"wealth_boost": True},
    },
]


class WorldEventGenerator:
    """
    世界随机事件生成器
    
    产生独立于角色行为的"世界自己的故事":
    - 天灾: 妖兽潮/地动/天象异变
    - 奇遇: 秘境开启/遗迹现世
    - 大势: 势力冲突/外交事件
    - 日常: 节庆/丰收/瘟疫
    """

    def __init__(self, influence_weight: int = 0):
        self.active_events: list = []
        self.event_history: list = []
        self._influence_bonus = min(influence_weight / 10, 10)  # 高影响力角色提高事件概率

    def roll(self, location_ids: list[str], day: int) -> list[dict]:
        """每日随机 roll 事件"""
        events = []

        # 基础概率 10%, 每多一天无事发生 +2%
        days_since_last = day - (self.event_history[-1]["day"] if self.event_history else 0)
        base_chance = 0.08 + days_since_last * 0.02 + self._influence_bonus * 0.01

        if random.random() < base_chance:
            template = random.choice(EVENT_TEMPLATES)
            loc_id = random.choice(location_ids)
            event = {
                "type": template["type"],
                "title": template["title"],
                "description": template["desc"].replace("{location}", loc_id),
                "location_id": loc_id,
                "severity": template["severity"],
                "duration_days": template["duration_days"],
                "remaining_days": template["duration_days"],
                "effects": template["effects"].copy(),
                "day": day,
                "active": True,
            }
            events.append(event)
            self.active_events.append(event)
            self.event_history.append(event)

        # 更新已有事件的剩余天数
        for event in self.active_events[:]:
            event["remaining_days"] -= 1
            if event["remaining_days"] <= 0:
                event["active"] = False
                self.active_events.remove(event)

        return events

    def active_at(self, location_id: str) -> list[dict]:
        return [e for e in self.active_events if e["location_id"] == location_id and e["active"]]
