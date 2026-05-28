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
决策模块 — 角色行为决策 (LLM 调用)
"""

from typing import Optional
from app.characters.schema import Character
from app.engine.perception import build_perception
from app.engine.events import NarrativeEvent
from app.llm.client import LLMClient


ACTION_SPACE_DESC = """你可选择的行为类型:

社交类:
- DIALOGUE: 对某人说话, params: {target, content?}
- TRADE: 交易/买卖, params: {target?, item?, price?}

探索类:
- EXPLORE: 探索当前区域, params: {direction?, purpose?}
- COLLECT: 采集资源, params: {resource: "草药/矿石/木材"/...}

信息类:
- OBSERVE: 观察环境/侦查/偷听, params: {target?}

生存类:
- REST: 休息恢复体力, params: {hours?}
- HEAL: 疗伤/治疗, params: {method?}

成长类:
- CULTIVATE: 修炼/练功, params: {skill?, duration?}

信息类:
- OBSERVE: 观察环境/侦查/偷听, params: {target?}
- INNER: 内心独白/反思/回忆, params: {content?}

行动类:
- ACT: 采取行动, params: {action_type: "战斗/探索/寻找/...", detail?}
- WAIT: 按兵不动/等待时机, params: {reason?}"""

DECISION_SYSTEM_PROMPT = f"""你是一位小说角色。根据你的角色设定、当前处境和相关记忆，决定你下一步做什么。

密切关注你的【状态】和【需求】——当需求值高时, 优先选择能满足该需求的行为。
也要关注【天气】和【传闻】——恶劣天气影响行动, 传闻可能暗示重要信息。
例如:
- 亟需休息(REST) → 体力低时
- 亟需安全 → 受伤/被追捕时

{ACTION_SPACE_DESC}

你必须返回 JSON 格式:
{{"action": "DIALOGUE/TRADE/EXPLORE/REST/HEAL/CULTIVATE/OBSERVE/INNER/ACT/WAIT", "target": "目标角色id或空", "params": {{}}, "reasoning": "一句话理由"}}

不要输出非 JSON 内容。"""


def make_decision(
    char: Character,
    scene: dict,
    world,
    llm: LLMClient,
    constraints: list[str] = None,
    recent_events: list[NarrativeEvent] = None,
) -> NarrativeEvent:
    """让一个角色做决策, 返回 NarrativeEvent"""

    perception_text = build_perception(char, scene, world, recent_events=recent_events)

    # 构建角色 prompt
    char_prompt_parts = [
        f"【角色档案】",
        f"姓名: {char.name}",
        f"人格: {', '.join(char.personality.traits)}",
        f"深层动机: {char.motivation.deep_desire}",
        f"当前目标: {', '.join(char.motivation.short_term_goals)}",
        f"",
        f"【当前处境】",
        perception_text,
    ]

    if constraints:
        char_prompt_parts.append(f"\n【约束】\n" + "\n".join(f"- {c}" for c in constraints))

    full_prompt = "\n".join(char_prompt_parts)

    try:
        decision = llm.chat_json(
            system_prompt=DECISION_SYSTEM_PROMPT,
            user_prompt=full_prompt,
        )
    except Exception as e:
        # LLM 调用失败时的 fallback
        decision = {"action": "WAIT", "target": "", "params": {"reason": "无法决定"}, "reasoning": str(e)}

    event = NarrativeEvent(
        beat_number=0,       # 由外层赋值
        chapter_number=0,
        time=scene.get("time", ""),
        location=scene.get("location_id", ""),
        agent_id=char.id,
        action_type=decision.get("action", "WAIT"),
        target_id=decision.get("target", None),
        content=str(decision.get("params", {})),
        outcome=decision.get("reasoning", ""),
        importance=3,
    )
    return event
