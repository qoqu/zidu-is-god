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
多线并行引擎 — 不同角色在不同地点同时推进各自的故事

核心机制:
  split  — 角色去不同地点 → 分裂为两条独立叙事线
  merge  — 不同线的角色相遇 → 合并为一条线
  POV    — 每轮选择一条线聚焦, 其他线后台推进

设计原则:
  - 每个角色都是自己故事的主角
  - 高张力线优先获得 POV
  - 没有线被长期忽略 (防饿死)
  - 叙事线最终会汇聚
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
import random


@dataclass
class NarrativeLine:
    """一条独立的叙事线"""
    id: str
    name: str                           # 显示名, 如 "林北辰在演武场"
    location_id: str
    char_ids: list = field(default_factory=list)
    char_names: list = field(default_factory=list)

    # 运行时
    beat_count: int = 0                  # 本条线已推进的 Beat 数
    last_pov_beat: int = 0               # 上次获得 POV 的全局 Beat 号
    current_tension: float = 0.3
    pending_events: list = field(default_factory=list)  # 待叙事的事件
    is_active: bool = True               # False = 这条线已收束可关闭

    # 分合溯源
    parent_line: Optional[str] = None    # 从哪条线分出来的
    split_reason: str = ""               # 为什么分开
    merged_into: Optional[str] = None    # 合并到了哪条线


class ParallelEngine:
    """
    多线并行调度器

    使用方式:
      pe = ParallelEngine(step_callback)
      pe.add_line("main", loc_id, [char_ids])
      pe.run_batch(beats=15)  # 推进所有线, 自动切换 POV
    """

    MAX_LINES = 5
    BEATS_PER_POV = 3          # 每条线连续获得 POV 的 Beat 数

    def __init__(self, step_callback: Callable):
        """
        Args:
            step_callback: 执行一个 Beat 的回调函数
                签名: (location_id, char_ids) → (events, post_tension)
        """
        self.lines: dict[str, NarrativeLine] = {}
        self.global_beat: int = 0
        self.current_pov: Optional[str] = None
        self._step_fn = step_callback
        self._history: list = []

    # ─── 线管理 ───────────────────────────────────────────

    def add_line(self, line_id: str, name: str, location_id: str,
                 char_ids: list[str], char_names: list[str] = None):
        """添加一条新叙事线"""
        assert len(self.lines) < self.MAX_LINES, f"叙事线已达上限({self.MAX_LINES})"
        self.lines[line_id] = NarrativeLine(
            id=line_id,
            name=name or f"线_{line_id}",
            location_id=location_id,
            char_ids=list(char_ids),
            char_names=list(char_names) if char_names else [],
        )
        if self.current_pov is None:
            self.current_pov = line_id

    def split_line(self, source_id: str, new_id: str, new_name: str,
                   new_location: str, split_char_ids: list[str],
                   reason: str = ""):
        """从一条线分裂出一条新线 (角色分头行动)"""
        if len(self.lines) >= self.MAX_LINES:
            return False

        source = self.lines.get(source_id)
        if not source:
            return False

        # 从源线移除分出角色
        for cid in split_char_ids:
            if cid in source.char_ids:
                source.char_ids.remove(cid)

        # 创建新线
        char_names = []
        self.lines[new_id] = NarrativeLine(
            id=new_id,
            name=new_name,
            location_id=new_location,
            char_ids=list(split_char_ids),
            char_names=char_names,
            parent_line=source_id,
            split_reason=reason,
            last_pov_beat=self.global_beat,
        )
        return True

    def merge_lines(self, line_a: str, line_b: str):
        """合并两条线 (角色相遇)"""
        if line_a not in self.lines or line_b not in self.lines:
            return

        la = self.lines[line_a]
        lb = self.lines[line_b]

        # 合并角色到 a
        for cid in lb.char_ids:
            if cid not in la.char_ids:
                la.char_ids.append(cid)

        # 标记 b 已合并
        lb.merged_into = line_a
        lb.is_active = False

        # 如果当前 POV 在 b 上, 切换到 a
        if self.current_pov == line_b:
            self.current_pov = line_a

    def check_convergence(self, world) -> list[str]:
        """检查不同线的角色是否处于同地点 → 自动合并"""
        merged = []
        active = [lid for lid, l in self.lines.items() if l.is_active]
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                li = self.lines[active[i]]
                lj = self.lines[active[j]]
                if li.location_id == lj.location_id:
                    # 同地点 → 合并
                    self.merge_lines(active[i], active[j])
                    merged.append(f"{li.name} + {lj.name}")
                    break  # 一次只合并一对

        # 清理非活跃线
        self.lines = {k: v for k, v in self.lines.items() if v.is_active}
        return merged

    # ─── POV 调度 ─────────────────────────────────────────

    def select_pov(self) -> Optional[str]:
        """选择当前应该聚焦的叙事线"""
        active = {lid: l for lid, l in self.lines.items() if l.is_active}
        if not active:
            return None
        if len(active) == 1:
            return list(active.keys())[0]

        now = self.global_beat

        # 1. 张力优先: 张力最高的线有更高概率获得 POV
        scored = []
        for lid, l in active.items():
            tension_score = l.current_tension * 10
            # 2. 防饿死: 越久没拿到 POV 权重越高
            starvation = min((now - l.last_pov_beat) / 5, 3.0)
            total = tension_score + starvation + random.uniform(0, 0.5)
            scored.append((total, lid))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    # ─── 推进 ─────────────────────────────────────────────

    def run_batch(self, world, beats_per_line: int = 3) -> list:
        """
        推进所有活跃叙事线

        Args:
            beats_per_line: 每条线一次推进多少 Beat

        Returns: 全部线的事件列表
        """
        all_events = []
        batches = max(1, beats_per_line // self.BEATS_PER_POV)

        for _ in range(batches):
            # 选择 POV
            pov_id = self.select_pov()
            if not pov_id:
                break
            self.current_pov = pov_id
            pivot = self.lines[pov_id]

            # POV 线推进
            for _ in range(self.BEATS_PER_POV):
                self.global_beat += 1
                events, tension = self._step_fn(
                    pivot.location_id, pivot.char_ids
                )
                pivot.beat_count += 1
                pivot.last_pov_beat = self.global_beat
                pivot.current_tension = tension
                pivot.pending_events.extend(events)
                all_events.extend(events)

            # 其他线后台推进 (每轮 1 Beat)
            for lid, line in self.lines.items():
                if lid == pov_id or not line.is_active:
                    continue
                events, tension = self._step_fn(
                    line.location_id, line.char_ids
                )
                line.beat_count += 1
                line.current_tension = tension
                line.pending_events.extend(events)
                all_events.extend(events)

            # 检查合并
            merges = self.check_convergence(world)
            if merges:
                for m in merges:
                    all_events.append(f"[叙事线合并] {m}")

        return all_events

    def get_line_summaries(self) -> list[dict]:
        """所有活跃线的摘要 (给 Narrator 用)"""
        summaries = []
        for line in self.lines.values():
            if not line.is_active:
                continue
            is_pov = (line.id == self.current_pov)
            summaries.append({
                "id": line.id,
                "name": line.name,
                "location": line.location_id,
                "char_count": len(line.char_ids),
                "beats": line.beat_count,
                "tension": f"{line.current_tension:.2f}",
                "events_count": len(line.pending_events),
                "is_pov": is_pov,
            })
        return summaries
