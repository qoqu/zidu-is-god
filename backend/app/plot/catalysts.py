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
催化剂事件目录
"""

from dataclasses import dataclass
from typing import Optional


CATALYST_CATALOG = {
    "THREAT_ESCALATE": {
        "name": "威胁升级",
        "trigger": "张力低于目标 0.2 持续 3+ Beat",
        "effects": ["环境变化", "敌人逼近", "天灾降临"],
    },
    "SECRET_REVEAL": {
        "name": "秘密揭示",
        "trigger": "已到揭示伏笔的节点",
        "effects": ["隐藏信息曝光", "发现关键证据"],
    },
    "NEW_CHARACTER": {
        "name": "新角色入场",
        "trigger": "剧情需要新变量打破僵局",
        "effects": ["神秘人出现", "信使到来", "第三方势力介入"],
    },
    "OPPORTUNITY": {
        "name": "机遇出现",
        "trigger": "章节需要爽点但 Agent 未创造",
        "effects": ["机缘降临", "宝物出世", "贵人相助"],
    },
    "TWIST": {
        "name": "剧情反转",
        "trigger": "张力不够或剧情太线性",
        "effects": ["关系反转", "信息截获", "发现被骗"],
    },
    "RESPITE": {
        "name": "喘息",
        "trigger": "张力高于目标 0.3 持续 3+ Beat",
        "effects": ["安全区域", "疗伤恢复", "情感交流"],
    },
    "DEADLINE": {
        "name": "时间压力",
        "trigger": "剧情推进太慢",
        "effects": ["倒计时", "最后期限", "危机逼近"],
    },
}


@dataclass
class CatalystEvent:
    """催化剂事件 — PlotDirector 注入到世界中的外部事件"""
    type: str
    description: str                # 注入描述
    target_location: Optional[str] = None
    target_char: Optional[str] = None

    def to_world_delta(self) -> dict:
        """将催化剂转换为世界状态变更"""
        return {
            "catalyst_type": self.type,
            "catalyst_desc": self.description,
        }


def create_catalyst(catalyst_type: str, context: dict) -> CatalystEvent:
    """根据上下文创建一个具体的催化剂事件"""
    catalog = CATALYST_CATALOG.get(catalyst_type, {})
    desc_prefix = catalog.get("effects", ["事件发生"])[0]

    return CatalystEvent(
        type=catalyst_type,
        description=f"[催化剂:{catalyst_type}] {desc_prefix} — {context.get('reason', '')}",
        target_location=context.get("location"),
        target_char=context.get("target_char"),
    )
