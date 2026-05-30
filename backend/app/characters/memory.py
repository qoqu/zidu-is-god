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
记忆系统 — 角色的多层长期记忆

人的记忆不是简单的"最近 N 条"。它是分层的、会衰减的、
情绪会增强的、相关事件会互相链接的。

层级:
  工作记忆 (Working):  最近 3~5 Beat, 完整细节
  短期记忆 (ShortTerm): 本章内, 较完整, 有情绪标记
  长期记忆 (LongTerm):  跨章, 压缩摘要, 按重要性排序
  核心记忆 (Core):      永不遗忘的关键事件 (成长转折/重大创伤)
"""

import uuid
import math
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


# ─── 记忆类型 ─────────────────────────────────────────────

@dataclass
class Memory:
    """一条记忆"""
    id: str = ""
    type: str = "event"          # event / dialogue / knowledge / relationship / reflection
    content: str = ""            # 记忆内容
    summary: str = ""            # 压缩摘要 (长期记忆用)

    # 时间
    created_at: float = 0.0       # 创建时间戳 (unix)
    chapter: int = 0
    beat: int = 0

    # 关联
    related_chars: list = field(default_factory=list)  # 关联角色 id
    related_memories: list = field(default_factory=list)  # 关联记忆 id

    # 权重
    importance: float = 0.5       # 0~1, 事件本身的重要性
    emotional_intensity: float = 0.0  # 0~1, 当时的情绪强度
    recall_count: int = 0          # 被回忆次数 (每次 recall +1)

    # 层级
    layer: str = "working"        # working / short_term / long_term / core

    # 衰减
    decay_rate: float = 0.01      # 每天衰减比例
    last_accessed: float = 0.0

    def score(self, now: float) -> float:
        """当前综合权重: 决定这条记忆在检索中的排名"""
        age_days = (now - self.created_at) / 86400
        days_since_access = (now - self.last_accessed) / 86400

        # 基础 = 重要性
        score = self.importance

        # 情绪增强: 高情绪的记忆更突出
        score += self.emotional_intensity * 0.3

        # 近期增强: 最近 N 天权重更高
        recency_boost = math.exp(-age_days * self.decay_rate)
        score += recency_boost * 0.2

        # 新鲜度惩罚: 刚被 recall 过的短期内权重降低 (避免重复)
        if days_since_access < 0.1:
            score -= 0.3

        # 访问次数增益: 常被 recall 的记忆更重要
        visit_boost = min(self.recall_count * 0.05, 0.3)
        score += visit_boost

        return max(0.0, score)

    def to_prompt_line(self, max_len: int = 80) -> str:
        """格式化为 LLM prompt 中的一行"""
        content = self.summary or self.content
        if max_len and len(content) > max_len:
            content = content[:max_len] + "..."
        tags = []
        if self.type == "dialogue":
            tags.append("对话")
        if self.emotional_intensity > 0.6:
            tags.append("印象深刻")
        if self.layer == "core":
            tags.append("刻骨铭心")
        if self.recall_count > 3:
            tags.append("反复回想")
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        return f"- {content}{tag_str}"


# ─── 记忆系统 ─────────────────────────────────────────────

class MemorySystem:
    """
    多层记忆系统

    核心机制:
    - 新记忆进入 working layer
    - 每章结束时: working→short_term, 旧的 short_term→long_term
    - 重要性 < 阈值且长期未访问 → 自然遗忘
    - 情绪强度高 或 被多次 recall → 提升层级
    - relevance 检索: 综合关键词 + 关联角色 + 时间近因 + 情绪
    """

    WORKING_MAX = 10       # 工作记忆上限
    SHORT_MAX = 50         # 短期记忆上限
    LONG_MAX = 200         # 长期记忆上限

    def __init__(self, char_name: str = ""):
        self._rag = None
        self.char_name = char_name
        # 执念: 角色永远忘不掉的东西, 不受衰减
        self.obsessions: list[dict] = []
        self.working: list[Memory] = []
        self.short_term: list[Memory] = []
        self.long_term: list[Memory] = []
        self.core: list[Memory] = []

    # ─── 存储 ─────────────────────────────────────────────

    def remember(self, content: str, mem_type: str = "event",
                 related_chars: list = None, importance: float = 0.5,
                 emotional_intensity: float = 0.0,
                 chapter: int = 0, beat: int = 0,
                 related_memories: list = None) -> Memory:
        """存入一条新记忆 (进入工作记忆层)"""
        now = datetime.now().timestamp()
        mem = Memory(
            id=uuid.uuid4().hex[:12],
            type=mem_type,
            content=content,
            summary=content[:120],
            created_at=now,
            last_accessed=now,
            chapter=chapter,
            beat=beat,
            related_chars=related_chars or [],
            related_memories=related_memories or [],
            importance=importance,
            emotional_intensity=emotional_intensity,
            layer="working",
        )
        self.working.append(mem)
        # 裁剪工作记忆
        self.working.sort(key=lambda m: m.score(now), reverse=True)
        self.working = self.working[:self.WORKING_MAX]
        return mem

    def remember_dialogue(self, speaker: str, content: str,
                          listener: str = "", chapter: int = 0, beat: int = 0):
        """记住一段对话"""
        related = [s for s in [speaker, listener] if s]
        self.remember(
            content=f"{speaker}对{listener}说: {content}" if listener else f"{speaker}说: {content}",
            mem_type="dialogue",
            related_chars=related,
            importance=0.4,
            emotional_intensity=0.3 if "!" in content or "?" in content else 0.1,
            chapter=chapter, beat=beat,
        )

    def remember_relationship_change(self, char_name: str, change: str,
                                     chapter: int = 0):
        """记住关系变化"""
        self.remember(
            content=f"和{char_name}的关系: {change}",
            mem_type="relationship",
            related_chars=[char_name],
            importance=0.7,
            emotional_intensity=0.5,
            chapter=chapter,
        )

    def remember_reflection(self, content: str, importance: float = 0.6):
        """角色内心的反思/感悟 (高重要性)"""
        self.remember(
            content=content,
            mem_type="reflection",
            importance=importance,
            emotional_intensity=0.4,
        )

    # ─── 层级管理与衰减 ─────────────────────────────────

    def consolidate(self, chapter: int):
        """
        每章结束时的记忆固化:
        - working → short_term
        - 旧的 short_term → long_term (或遗忘)
        - 高重要性+多次recall → core
        """
        now = datetime.now().timestamp()

        # working → short_term
        for mem in self.working:
            mem.layer = "short_term"
            self.short_term.append(mem)
        self.working = []

        self.short_term.sort(key=lambda m: m.score(now), reverse=True)
        self.short_term = self.short_term[:self.SHORT_MAX]

        # 长期记忆衰减
        surviving = []
        for mem in self.long_term:
            mem.layer = "long_term"
            score = mem.score(now)
            if score > 0.15:  # 低于此阈值遗忘
                surviving.append(mem)
            else:
                pass  # 遗忘
        self.long_term = surviving[:self.LONG_MAX]

        # 检查是否有 short_term 记忆可以升级到 long_term
        for mem in self.short_term:
            if mem.importance > 0.7 or mem.recall_count > 2:
                mem.layer = "long_term"
                self.long_term.append(mem)
        self.short_term = [m for m in self.short_term if m.layer == "short_term"]

        # 核心记忆: 重要性 > 0.9 或 recall > 5
        for mem in self.short_term + self.long_term:
            if mem.importance >= 0.9 or mem.recall_count >= 5:
                mem.layer = "core"
                if mem not in self.core:
                    self.core.append(mem)

    # ─── 执念

    def add_obsession(self, content: str, obs_type: str = "grudge",
                      intensity: float = 0.8, related_char: str = ""):
        """增加一条执念 —— 角色永远无法释怀的事
        obs_type: grudge(怨恨) / goal(目标) / trauma(创伤) / love(情感) / secret(秘密)
        """
        self.obsessions = [o for o in self.obsessions if o["content"] != content]
        self.obsessions.append({
            "content": content, "type": obs_type,
            "intensity": min(1.0, max(0.1, intensity)),
            "related_char": related_char,
        })
        # 同时作为 core memory
        self.remember(content=content, mem_type="obsession",
                       related_chars=[related_char] if related_char else None,
                       importance=0.95, emotional_intensity=intensity)

    def obsessions_text(self) -> str:
        """执念永远出现在决策 prompt 中"""
        if not self.obsessions:
            return ""
        labels = {"grudge": "怨恨", "goal": "目标", "trauma": "创伤",
                  "love": "情感", "secret": "秘密"}
        lines = ["【执念】"]
        for obs in self.obsessions:
            label = labels.get(obs["type"], obs["type"])
            bar = "■" * int(obs["intensity"] * 10) + "░" * (10 - int(obs["intensity"] * 10))
            lines.append(f"  {bar} {label}: {obs['content']}")
        return "\n".join(lines)

    # ---- 检索 ─────────────────────────────────────────────

    def recall(self, context: str = "", top_k: int = 5,
               char_in_focus: str = "") -> list[Memory]:
        """
        检索最相关的记忆

        Args:
            context: 当前场景上下文 (关键词匹配)
            top_k: 返回上限
            char_in_focus: 如果指定, 优先返回与该角色相关的记忆

        Returns: [Memory, ...]
        """
        now = datetime.now().timestamp()
        candidates = self.working + self.short_term + self.long_term + self.core

        # 去重
        seen = set()
        unique = []
        for m in candidates:
            if m.id not in seen:
                seen.add(m.id)
                unique.append(m)

        # 评分
        keywords = set(context.lower().split()) if context else set()
        for mem in unique:
            base = mem.score(now)

            # 关键词匹配加成
            if keywords:
                match = sum(1 for kw in keywords if kw in mem.content.lower())
                base += match * 0.15

            # 关联角色加成
            if char_in_focus and char_in_focus in mem.related_chars:
                base += 0.3

            mem._retrieval_score = base

        unique.sort(key=lambda m: getattr(m, '_retrieval_score', 0), reverse=True)

        # 返回时更新 recall_count
        results = unique[:top_k]
        for mem in results:
            mem.recall_count += 1
            mem.last_accessed = now

        return results

    def recall_by_type(self, mem_type: str, top_k: int = 3) -> list[Memory]:
        """按类型检索"""
        candidates = self.short_term + self.long_term + self.core
        filtered = [m for m in candidates if m.type == mem_type]
        filtered.sort(key=lambda m: m.importance, reverse=True)
        return filtered[:top_k]

    # ─── Prompt 集成 ──────────────────────────────────────

    def format_for_prompt(self, context: str = "", char_in_focus: str = "",
                          max_lines: int = 6, max_chars: int = 500) -> str:
        """格式化为 LLM prompt 中的记忆段落"""
        memories = self.recall(context=context, char_in_focus=char_in_focus,
                                top_k=max_lines)

        # 执念永远优先显示
        obs_text = self.obsessions_text()
        mem_text = self._format_memories(context, char_in_focus, max_lines, max_chars)
        if obs_text and mem_text:
            return obs_text + "\n\n" + mem_text
        return obs_text or mem_text or ""

    def _format_memories(self, context, char_in_focus, max_lines, max_chars):
        memories = self.recall(context=context, char_in_focus=char_in_focus, top_k=max_lines)
        if not memories:
            return ""
        lines = ["【记忆】"]
        char_count = 0
        for mem in memories:
            line = mem.to_prompt_line()
            char_count += len(line)
            if char_count > max_chars:
                break
            lines.append(line)

        return "\n".join(lines)

    def format_comprehensive(self) -> str:
        """
        完整记忆摘要 (用于章节切换时的上下文传递)
        - 核心记忆: 全部列出
        - 长期记忆: 最近 5 条
        - 重要关系变化: 最近 3 条
        """
        parts = []

        if self.core:
            parts.append("刻骨铭心的记忆:")
            for m in self.core[-5:]:
                parts.append(f"  - {m.summary}")

        long_recent = sorted(self.long_term, key=lambda m: m.created_at, reverse=True)[:5]
        if long_recent:
            parts.append("近期重要经历:")
            for m in long_recent:
                parts.append(f"  - {m.summary}")

        rel_memories = [m for m in self.short_term + self.long_term if m.type == "relationship"]
        if rel_memories:
            parts.append("关系变化:")
            for m in rel_memories[-3:]:
                parts.append(f"  - {m.summary}")

        return "\n".join(parts)

    def count(self) -> dict:
        return {
            "working": len(self.working),
            "short_term": len(self.short_term),
            "long_term": len(self.long_term),
            "core": len(self.core),
            "total": len(self.working) + len(self.short_term) + len(self.long_term) + len(self.core),
        }
