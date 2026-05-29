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
通用时间轴模型 — 时间是一条线, 我们可以在任意一点改变它

核心概念:
  时间轴 = 一系列节点 (TimelineNode), 每个节点对应原著的一章
  每个节点记录: 世界状态、关键事件、在场角色
  用户可以在任意节点插入新角色 → 后续节点产生分歧 (Diverged)

  分歧机制:
  original_branch = 原著走向 (只读)
  diverged_branch = 插入角色后 Engine 模拟的新走向
  两个分支共享分歧点之前的节点, 之后各走各路
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json


@dataclass
class TimelineNode:
    """
    时间轴上的一个节点 (通常对应原著一章)

    Attributes:
        chapter: 章节号
        title: 章节标题
        summary: 该章事件摘要 (用于 LLM 理解前情)
        world_snapshot: 该章开始时的世界状态
            {"locations": {...}, "factions": {...}, "global_state": {...}}
        key_events: 该章发生的关键事件列表
        chars_present: 该章登场的角色 id
        relationships_at_start: 该章开始时角色间的关系
            {("char_a", "char_b"): {"affinity": 30, "trust": 50}}
        inserted_chars: 在该节点插入的新角色 (分歧点)
        is_divergence_point: 是否分歧点
        diverged: 是否处于分歧分支
    """
    chapter: int
    title: str = ""
    summary: str = ""
    world_snapshot: dict = field(default_factory=dict)
    key_events: list = field(default_factory=list)
    chars_present: list = field(default_factory=list)
    relationships_at_start: dict = field(default_factory=dict)
    inserted_chars: list = field(default_factory=list)
    is_divergence_point: bool = False
    diverged: bool = False


class Timeline:
    """
    通用时间轴 — 贯穿整个引擎的核心数据模型

    用法:
      tl = Timeline.from_novel("原著.txt")  # 解析原著建时间轴
      tl.insert_character("穿越者", at_chapter=4)  # 第4章插入
      tl.diverged_branch()  # 获取分歧分支
      Engine.run_timeline(tl)  # 沿分歧分支跑模拟
    """

    def __init__(self):
        self.nodes: list[TimelineNode] = []
        self._diverged_nodes: list[TimelineNode] = []
        self._divergence_point: int = -1
        self._original_nodes: list[TimelineNode] = []

    # ─── 构建 ─────────────────────────────────────────────

    def add_node(self, node: TimelineNode):
        """添加一个时间节点"""
        self.nodes.append(node)

    def add_empty_chapter(self, chapter: int, title: str = ""):
        """添加一个空节点 (当解析器未提供详细数据时)"""
        self.nodes.append(TimelineNode(
            chapter=chapter, title=title, summary=""
        ))

    # ─── 分歧 ─────────────────────────────────────────────

    def insert_character(self, char_id: str, char_name: str,
                         at_chapter: int) -> bool:
        """
        在指定章节插入一个新角色

        该章节成为分歧点, 后续节点标记为 diverged。
        只在未分歧状态下可插入。
        """
        if self._divergence_point >= 0:
            return False  # 已经分过歧了

        # 找到插入点
        for node in self.nodes:
            if node.chapter == at_chapter:
                node.inserted_chars.append(char_id)
                node.is_divergence_point = True
                self._divergence_point = at_chapter
                # 保存原著分支
                self._original_nodes = [n for n in self.nodes]
                # 分歧点之后的节点标记为 diverged
                for n in self.nodes:
                    if n.chapter >= at_chapter:
                        n.diverged = True
                return True

        # 如果节点不存在, 创建一个
        new_node = TimelineNode(
            chapter=at_chapter,
            title=f"第{at_chapter}章 (分歧点)",
            inserted_chars=[char_id],
            is_divergence_point=True,
            diverged=True,
        )
        self.nodes.append(new_node)
        self.nodes.sort(key=lambda n: n.chapter)
        self._divergence_point = at_chapter
        self._original_nodes = [n for n in self.nodes if not n.diverged]
        return True

    def diverged_branch(self) -> list[TimelineNode]:
        """获取分歧分支 (分歧点及之后的所有节点)"""
        if self._divergence_point < 0:
            return self.nodes  # 未分歧, 返回全部
        return [n for n in self.nodes if n.chapter >= self._divergence_point and n.diverged]

    def original_branch(self) -> list[TimelineNode]:
        """获取原著分支 (分歧点之前的节点)"""
        if self._divergence_point < 0:
            return self.nodes
        return [n for n in self.nodes if n.chapter < self._divergence_point]

    # ─── 查询 ─────────────────────────────────────────────

    def get_node(self, chapter: int) -> Optional[TimelineNode]:
        for n in self.nodes:
            if n.chapter == chapter:
                return n
        return None

    def context_for(self, chapter: int, max_history: int = 3) -> str:
        """给 Engine 提供前情提要: 分歧点之前的 N 章摘要"""
        relevant = [n for n in self.nodes if n.chapter < chapter]
        relevant = relevant[-max_history:]
        lines = ["【前情提要】"]
        for n in relevant:
            tag = " [分歧点]" if n.is_divergence_point else ""
            lines.append(f"  第{n.chapter}章{tag}: {n.summary[:100]}")
            if n.inserted_chars:
                lines.append(f"    新角色入场: {', '.join(n.inserted_chars)}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "node_count": len(self.nodes),
            "divergence_point": self._divergence_point,
            "chapters": [n.chapter for n in self.nodes],
        }

    # ─── 序列化 ───────────────────────────────────────────

    def save(self, filepath: str):
        """保存时间轴到 JSON"""
        data = {
            "divergence_point": self._divergence_point,
            "nodes": [
                {
                    "chapter": n.chapter, "title": n.title, "summary": n.summary,
                    "key_events": n.key_events,
                    "chars_present": n.chars_present,
                    "inserted_chars": n.inserted_chars,
                    "is_divergence_point": n.is_divergence_point,
                    "diverged": n.diverged,
                }
                for n in self.nodes
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(filepath: str) -> "Timeline":
        """从 JSON 加载时间轴"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        tl = Timeline()
        tl._divergence_point = data.get("divergence_point", -1)
        for nd in data.get("nodes", []):
            tl.nodes.append(TimelineNode(
                chapter=nd["chapter"],
                title=nd.get("title", ""),
                summary=nd.get("summary", ""),
                key_events=nd.get("key_events", []),
                chars_present=nd.get("chars_present", []),
                inserted_chars=nd.get("inserted_chars", []),
                is_divergence_point=nd.get("is_divergence_point", False),
                diverged=nd.get("diverged", False),
            ))
        return tl
