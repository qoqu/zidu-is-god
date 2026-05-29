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
PlotDirector — 剧情导演
宏观控制，不干预 Agent 细节决策
"""

from typing import Optional, Callable
from app.config import Config
from app.world.schema import World
from app.characters.schema import Character
from app.engine.events import ChapterBlueprint
from app.plot.tension import calculate_tension, suggest_target_tension
from app.plot.catalysts import create_catalyst, CatalystEvent
from app.plot.foreshadowing import ForeshadowingPool
from app.plot.emotion_curve import EmotionCurveTracker, ChapterEmotionRecord
from app.plot.risk_registry import RiskRegistry
from app.plot.status_card import StatusCard


class PlotDirector:
    """剧情导演 — 宏观节奏控制"""

    def __init__(
        self,
        world: World,
        characters: list[Character],
        config: Optional[Config] = None,
    ):
        self.world = world
        self.characters = {c.id: c for c in characters}
        self.config = config or Config()
        self.foreshadowing_pool = ForeshadowingPool()
        self.emotion_curve = EmotionCurveTracker()
        self.risk_registry = RiskRegistry()
        self.status_card = StatusCard()

        # 运行时状态
        self._consecutive_low_beats = 0
        self._consecutive_high_beats = 0
        self._milestones_met: set = set()

    # ─── 章前准备 ───────────────────────────────────────────

    def plan_chapter(self, chapter_num: int) -> ChapterBlueprint:
        """为本章生成蓝图"""
        # 1. 建议情绪基调
        target_emotion = self.emotion_curve.suggest_next_chapter_emotion(chapter_num)

        # 2. 获取本章的伏笔操作
        fs_for_chapter = self.foreshadowing_pool.get_for_chapter(chapter_num)

        # 3. 获取生效中的风险备忘
        risks = self.risk_registry.get_active_descriptions(chapter_num)

        # 4. 生成张力曲线
        num_beats = self.config.DEFAULT_BEATS_PER_CHAPTER
        tension_curve = [
            suggest_target_tension(chapter_num, i / num_beats)
            for i in range(num_beats)
        ]

        blueprint = ChapterBlueprint(
            chapter_number=chapter_num,
            title_hint=f"第{chapter_num}章",
            target_tension_curve=tension_curve,
            milestones=self._get_chapter_milestones(chapter_num),
            target_emotion_label=target_emotion,
            active_risk_constraints=risks,
            foreshadowing_to_set=[f.description for f in fs_for_chapter.get("to_set", [])],
            foreshadowing_to_reveal=[f.id for f in fs_for_chapter.get("to_reveal", [])],
        )

        # 更新 StatusCard
        self.status_card.current_chapter = chapter_num

        return blueprint

    # ─── Beat 级监控 ────────────────────────────────────────

    def check_tension(
        self,
        current_tension: float,
        target_tension: float,
        chapter_progress: float,
    ) -> Optional[CatalystEvent]:
        """
        检查当前张力, 必要时注入催化剂。
        返回 CatalystEvent 或 None。
        """
        deviation = current_tension - target_tension

        if deviation < -0.2:
            self._consecutive_low_beats += 1
            self._consecutive_high_beats = 0
        elif deviation > 0.3:
            self._consecutive_high_beats += 1
            self._consecutive_low_beats = 0
        else:
            self._consecutive_low_beats = 0
            self._consecutive_high_beats = 0

        # 张力偏低 → 注入威胁/反转
        if self._consecutive_low_beats >= 3:
            self._consecutive_low_beats = 0
            return create_catalyst("THREAT_ESCALATE", {
                "reason": f"张力连续 {self._consecutive_low_beats} Beat 偏低",
            })

        # 张力偏高 → 注入喘息
        if self._consecutive_high_beats >= 3:
            self._consecutive_high_beats = 0
            return create_catalyst("RESPITE", {
                "reason": f"张力连续 {self._consecutive_high_beats} Beat 偏高",
            })

        # 检查逾期伏笔
        overdue = self.foreshadowing_pool.get_overdue(self.status_card.current_chapter)
        if overdue:
            # 强制回收最早逾期的伏笔
            fs = overdue[0]
            return create_catalyst("SECRET_REVEAL", {
                "reason": f"强制回收伏笔: {fs.description}",
            })

        return None

    # ─── 章后处理 ───────────────────────────────────────────

    def finish_chapter(self, chapter_num: int, avg_tension: float):
        """本章结束后的收尾工作"""
        # ★★★ 角色升降级 (根据剧情关注度动态调整)
        self._adjust_roles(chapter_num)

        # 更新情绪曲线
        emotion_label = self.status_card.chapter_type
        self.emotion_curve.add_record(ChapterEmotionRecord(
            chapter=chapter_num,
            emotion_label=emotion_label or "燃",
            intensity=int(avg_tension * 10),
        ))

    def _adjust_roles(self, chapter_num: int):
        """根据剧情关注度动态调整角色级别"""
        from app.characters.schema import CharacterRole
        chars = self.characters.values()

        # 统计每个角色在最近事件中出现的频率
        event_counts = {}
        for blog in getattr(self, '_recent_logs', []):
            for ev in getattr(blog, 'events', []):
                cid = getattr(ev, 'agent_id', None)
                if cid:
                    event_counts[cid] = event_counts.get(cid, 0) + 1

        if not event_counts:
            return

        avg_count = sum(event_counts.values()) / max(len(event_counts), 1)

        for char in chars:
            cid = char.id
            count = event_counts.get(cid, 0)
            current_role = getattr(char, 'role', CharacterRole.PRIMARY)

            # 长期不活跃 → 降级
            if current_role == CharacterRole.PRIMARY and count < avg_count * 0.3:
                if chapter_num > 3:  # 前三章不降级
                    char.role = CharacterRole.SECONDARY

            # 活跃度提升 → 升级
            elif current_role == CharacterRole.SECONDARY and count > avg_count * 1.5:
                char.role = CharacterRole.PRIMARY

            # background → secondary (如果参与了事件)
            elif current_role == CharacterRole.BACKGROUND and count > 0:
                char.role = CharacterRole.SECONDARY

    # ★★★ 为 PlotDirector 添加事件日志引用
    @property
    def _recent_logs(self):
        return getattr(self, '_event_log', [])
    
    def set_recent_logs(self, logs):
        self._event_log = logs[-5:]  # 只保留最近 5 Beat

        # 角色情绪沉淀
        for char in self.characters.values():
            char.emotional_state.decay_to_mood()

        # 重置 Beat 计数器
        self._consecutive_low_beats = 0
        self._consecutive_high_beats = 0

    # ─── 黄金三章 ───────────────────────────────────────────

    def _get_chapter_milestones(self, chapter_num: int) -> dict:
        """获取章节的里程碑约束"""
        milestones = {
            1: {
                "core_conflict": 0.4,
                "protagonist_intro": 0.2,
                "hook_ending": 1.0,
            },
            2: {
                "show_advantage": 0.5,
                "escalate_threat": 0.8,
            },
            3: {
                "short_term_goal": 0.3,
                "first_reward": 0.6,
                "real_threat": 0.85,
            },
        }
        return milestones.get(chapter_num, {"hook_ending": 1.0})
