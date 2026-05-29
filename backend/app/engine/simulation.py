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
叙事引擎 — 核心模拟循环
"""

from typing import Optional
from app.config import Config
from app.world.schema import World
from app.characters.schema import Character
from app.engine.events import NarrativeEvent, BeatLog, ChapterBlueprint
from app.engine.perception import build_scene
from app.engine.deliberation import make_decision
from app.engine.actions import resolve_actions
from app.plot.tension import calculate_tension
from app.plot.director import PlotDirector
from app.llm.client import LLMClient
from app.world.engine import WorldEngine
from app.engine.parallel import ParallelEngine
from app.engine.actions import EnvironmentInteraction


class Engine:
    """叙事引擎 — 主循环"""

    def __init__(
        self,
        world: World,
        characters: list[Character],
        llm: Optional[LLMClient] = None,
        config: Optional[Config] = None,
    ):
        self.world = world
        self.characters = {c.id: c for c in characters}
        self.llm = llm or LLMClient()
        self.config = config or Config()
        self.event_log: list[BeatLog] = []
        self.world_engine: Optional[WorldEngine] = None
        self.current_chapter = 0
        self.current_beat = 0
        self._init_fog()
        self._init_pool()

    @property
    def all_characters(self) -> list[Character]:
        return list(self.characters.values())

    def run_chapter(self, director: PlotDirector, blueprint: ChapterBlueprint) -> list[BeatLog]:
        """运行一章的全部 Beat, 接入 PlotDirector"""
        self.current_chapter = blueprint.chapter_number
        chapter_logs = []

        for beat_num in range(1, self.config.DEFAULT_BEATS_PER_CHAPTER + 1):
            self.current_beat = beat_num
            chapter_progress = beat_num / self.config.DEFAULT_BEATS_PER_CHAPTER

            beat_log = self._step(director, blueprint, chapter_progress)
            chapter_logs.append(beat_log)

        # ★★★ 章后: 角色状态衰减 (每日消耗)
        for char in self.all_characters:
            char.stats.daily_decay()
        # ★★★ 章后: 记忆固化
        for char in self.all_characters:
            char.memory.consolidate(self.current_chapter)
        # ★★★ 章后: 传递事件日志给 PlotDirector
        if hasattr(director, "set_recent_logs"):
            director.set_recent_logs(chapter_logs)

        # 章后: 注册新伏笔
        for fs_desc in blueprint.foreshadowing_to_set:
            director.foreshadowing_pool.add_foreshadowing(
                description=fs_desc,
                setup_chapter=self.current_chapter,
                reveal_chapter=self.current_chapter + 2,
            )

        return chapter_logs

    def run_parallel_chapter(self, director: PlotDirector, blueprint: ChapterBlueprint) -> list:
        """多线模式: 使用 ParallelEngine 推进一章"""
        self.current_chapter = blueprint.chapter_number
        
        # 创建 ParallelEngine
        def step_cb(loc_id, char_ids):
            progress = (self.current_beat or 1) / self.config.DEFAULT_BEATS_PER_CHAPTER
            return self._step_at(loc_id, char_ids, director, blueprint, progress)

        pe = ParallelEngine(step_cb)
        
        # 初始: 所有角色在主角位置
        prot = self._get_protagonist()
        loc_id = prot.current_location if prot else list(self.world.locations.keys())[0]
        all_ids = [c.id for c in self.all_characters]
        pe.add_line('main', f'{prot.name if prot else "主角"}在{loc_id}', loc_id, all_ids)
        
        # 推进
        pe.run_batch(self.world, beats_per_line=self.config.DEFAULT_BEATS_PER_CHAPTER)
        self._parallel_engine = pe
        
        # 章后: 状态衰减
        for char in self.all_characters:
            char.stats.daily_decay()
        
        return pe


    def _step_at(self, location_id: str, char_ids: list[str], 
                 director: PlotDirector, blueprint: ChapterBlueprint,
                 chapter_progress: float) -> tuple[list, float]:
        """在指定地点+指定角色上执行一 Beat, 返回 (events_list, post_tension)"""
        beat_num = self.current_beat
        chapter_num = self.current_chapter

        present_chars = [self.characters[cid] for cid in char_ids if cid in self.characters]
        if not present_chars:
            return [], 0.0

        scene = build_scene(
            world=self.world,
            location_id=location_id,
            time=self.world.timeline.current_time,
            present_chars=present_chars,
        )

        recent_events = self.get_events_since_last_checkpoint()
        
        # 按角色分级分组
        primary_chars = [c for c in present_chars if getattr(c, 'role', 'primary') == 'primary']
        secondary_chars = [c for c in present_chars if getattr(c, 'role', 'primary') == 'secondary']
        background_chars = [c for c in present_chars if getattr(c, 'role', 'primary') == 'background']
        
        events = []
        
        # primary: 完整 LLM 决策
        if primary_chars:
            from app.engine.deliberation import make_decisions_parallel
            events = make_decisions_parallel(
                chars=primary_chars, scene=scene, world=self.world, llm=self.llm,
                constraints=blueprint.active_risk_constraints,
                recent_events=recent_events,
                beat_number=beat_num, chapter_number=chapter_num,
            )
        
        # secondary: 简化 LLM 决策 (缩减 prompt)
        if secondary_chars:
            from app.engine.deliberation import make_decisions_parallel
            sec_events = make_decisions_parallel(
                chars=secondary_chars, scene=scene, world=self.world, llm=self.llm,
                constraints=blueprint.active_risk_constraints + ["(精简回复, 不超过20字)"],
                recent_events=recent_events,
                beat_number=beat_num, chapter_number=chapter_num,
            )
            events.extend(sec_events)
        
        # background: 自动生成默认行为 (不调 LLM)
        for char in background_chars:
            from app.engine.events import NarrativeEvent
            events.append(NarrativeEvent(
                beat_number=beat_num, chapter_number=chapter_num,
                time=self.world.timeline.current_time, location=location_id,
                agent_id=char.id, action_type="WAIT",
                outcome=f"{char.name}在附近活动", importance=1,
            ))

        resolved = resolve_actions(events, self.characters, self.world)

        pre_tension = calculate_tension(self.world, scene, present_chars, chapter_progress)
        for event in resolved:
            self.world.apply_event(event)
            char = self.characters.get(event.agent_id)
            if char:
                char.emotional_state.update_by_event(event)
                # 记忆存储
                import json as _json
                event_text = event.outcome or event.content
                if event.action_type == 'DIALOGUE':
                    char.memory.remember_dialogue(
                        speaker=char.name,
                        content=str(event.content)[:100],
                        chapter=event.chapter_number,
                        beat=event.beat_number,
                    )
                elif event.action_type == 'INNER' and len(str(event.content)) > 10:
                    char.memory.remember_reflection(str(event.content)[:150])
                else:
                    related = [event.target_id] if event.target_id else None
                    char.memory.remember(
                        content=str(event_text)[:200],
                        mem_type='event',
                        related_chars=related,
                        importance=event.importance / 5.0,
                        emotional_intensity=abs(char.emotional_state.arousal),
                        chapter=event.chapter_number,
                        beat=event.beat_number,
                    )
                self.world.beats_since_last_peak = 0 if event.importance >= 4 else self.world.beats_since_last_peak + 1

        post_tension = calculate_tension(self.world, scene, present_chars, chapter_progress)
        
        # 高影响力角色注入
        world_engine = getattr(self.world, 'world_engine', None)
        if world_engine:
            for event in resolved:
                char = self.characters.get(event.agent_id)
                if char and char.stats.influence:
                    inf = char.stats.influence
                    prim = inf.primary()
                    val = getattr(inf, prim, 1)
                    if val >= 10:
                        world_engine.inject_character_action(
                            char_name=char.name, action_desc=event.outcome[:40],
                            dimension=prim, weight=val,
                            radius=inf.radii.get(prim, 'local'),
                            location_id=event.location,
                        )

        return resolved, post_tension

    def _step(self, director: PlotDirector, blueprint: ChapterBlueprint, chapter_progress: float) -> BeatLog:
        """单线模式: 在主角位置执行一 Beat"""
        """一轮 Beat 六步"""
        beat_num = self.current_beat
        chapter_num = self.current_chapter

        # ── 时间推进 ──
        self.world.advance_time()
        # ── 世界自主演化 Tick (每章一次) ──
        if beat_num == 1 and self.world_engine:
            world_changes = self.world_engine.tick()
            # 天气影响角色
            weather = world_changes.get("weather", {})
            if weather:
                self.world.global_state["current_weather"] = weather["current"]

        # Step 1: 场景组装
        protagonist = self._get_protagonist()
        loc_id = protagonist.current_location if protagonist else list(self.world.locations.keys())[0]
        if loc_id not in self.world.locations:
            loc_id = list(self.world.locations.keys())[0]

        present_chars = self._get_chars_at_location(loc_id)
        scene = build_scene(
            world=self.world,
            location_id=loc_id,
            time=self.world.timeline.current_time,
            present_chars=present_chars,
        )

        # Step 2-3: 感知 + 决策
        events = []
        recent_events = self.get_events_since_last_checkpoint()
        for char in present_chars:
            event = make_decision(
                char=char,
                scene=scene,
                world=self.world,
                llm=self.llm,
                constraints=blueprint.active_risk_constraints,
                recent_events=recent_events,
            )
            event.beat_number = beat_num
            event.chapter_number = chapter_num
            events.append(event)

        # Step 4: 行动解析 + 冲突注册
        resolved = resolve_actions(events, self.characters, self.world)

        # Step 5: 张力计算 + PlotDirector 介入
        pre_tension = calculate_tension(self.world, scene, present_chars, chapter_progress)

        for event in resolved:
            self.world.apply_event(event)
            char = self.characters.get(event.agent_id)
            if char:
                char.emotional_state.update_by_event(event)
                if event.importance >= 4:
                    self.world.beats_since_last_peak = 0
                else:
                    self.world.beats_since_last_peak += 1

        post_tension = calculate_tension(self.world, scene, present_chars, chapter_progress)

        # ── PlotDirector 张力检查 → 注入催化剂 ──
        target_tension = blueprint.target_tension_curve[min(beat_num - 1, len(blueprint.target_tension_curve) - 1)]
        catalyst = director.check_tension(post_tension, target_tension, chapter_progress)

        catalyst_injected = None
        if catalyst:
            catalyst_injected = catalyst.type
            # 催化剂注入: 更新世界状态, 让后续 Beat 的 Agent 感知到变化
            self.world.global_state["catalyst"] = catalyst.description
            # 也添加一条系统事件
            resolved.append(NarrativeEvent(
                beat_number=beat_num,
                chapter_number=chapter_num,
                time=self.world.timeline.current_time,
                location=loc_id,
                agent_id="__system__",
                action_type="CATALYST",
                content=catalyst.description,
                importance=4,
            ))
            # 如果催化剂涉及威胁升级, 也自动添加冲突
            if catalyst.type == "THREAT_ESCALATE":
                for c in present_chars:
                    for other in present_chars:
                        if c.id != other.id:
                            self.world.register_conflict(c.id, other.id, f"催化剂:威胁升级")

        # Step 6: 记录
        beat_log = BeatLog(
            beat_number=beat_num,
            chapter_number=chapter_num,
            events=resolved,
            pre_tension=pre_tension,
            post_tension=post_tension,
            catalyst_injected=catalyst_injected,
        )
        self.event_log.append(beat_log)

        return beat_log

    # ─── 辅助方法 ────────────────────────────────────────────

    def _get_protagonist(self) -> Optional[Character]:
        return self.all_characters[0] if self.all_characters else None

    def _get_chars_at_location(self, location_id: str) -> list[Character]:
        loc = self.world.locations.get(location_id)
        if not loc:
            return self.all_characters
        return [c for c in self.all_characters if c.current_location == location_id]

    def _init_pool(self):
        from app.engine.character_pool import CharacterPool
        pool = CharacterPool(self.all_characters)
        pool.set_llm(self.llm)
        self.char_pool = pool

    def _init_fog(self):
        world_engine = getattr(self.world, 'world_engine', None)
        if not world_engine or not hasattr(world_engine, 'fog'):
            return
        for char in self.all_characters:
            world_engine.fog.initialize_char(char.id, char.current_location, char=char)
        if hasattr(world_engine.fog, 'world'):
            world_engine.fog.world._characters = list(self.characters.values())

    def _rotate_cast(self):
        pool = self.char_pool
        if not pool:
            return
        active = pool.get_active()
        if len(active) > 2:
            for c in reversed(active):
                if c.role != 'primary' and c.id != active[0].id:
                    pool.mark_dormant(c.id, self.current_chapter)
                    break
        if self.current_chapter % 6 == 0:
            context = f"当前第{self.current_chapter}章. 活跃: " + ", ".join(c.name for c in active)
            new_char = pool.generate_new(context, active)
            if new_char:
                we = getattr(self.world, 'world_engine', None)
                if we and hasattr(we, 'fog'):
                    we.fog.initialize_char(new_char.id, new_char.current_location, char=new_char)
                self.all_characters.append(new_char)

    def get_events_since_last_checkpoint(self) -> list[NarrativeEvent]:
        events = []
        for blog in self.event_log:
            events.extend(blog.events)
        return events
