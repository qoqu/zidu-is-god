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
Narrator — 事件序列 → 小说文本
"""

from typing import Optional
from app.engine.events import NarrativeEvent, BeatLog
from app.llm.client import LLMClient



WRITER_PROMPT = """你是一位小说写手。你将收到一章故事的多个片段(每个片段对应一个场景)。

你的任务: 将这些片段重写为连贯的、可读性强的完整小说章节。

要求:
1. 将多个场景自然地交织在一起, 而不是分段堆砌
2. 加入环境描写、角色内心活动、对话
3. 保持角色姓名一致
4. 控制段落长度, 避免大段独白
5. 在场景切换时用空行分隔, 但不要标注"场景一"、"场景二"
6. 总字数控制在 500-1500 字
7. 让读者能感受到角色的情绪和动机, 而不仅仅是"他做了什么"

原始片段:
{raw_text}

角色信息:
{char_info}

角色信息:
{char_info}

故事背景: {world_context}
当前时间: {time}
导演计划: {plan}

请写出这一章:"""

NARRATOR_SYSTEM_PROMPT = """你是一位小说写手。根据给定的叙事事件序列, 写出流畅的小说段落。

规则:
1. 使用有限第三人称视角, 紧跟主角视角
2. 保持简洁, 不过度修饰
3. 对话用中文引号 "", 动作描写和对话交替
4. 将角色的内心独白(INNER)融入叙述
5. 每段 100-300 字
6. 如果事件中有 [冲突] 标记, 重点描写双方互动
7. 如果事件中有 [催化剂:xxx], 将其自然地融入情节
8. **续写时不要重新介绍场景和人物, 直接从上一段结尾继续推进**
9. **保持角色姓名一致, 不要给角色改名**

直接输出小说文本, 不要输出任何说明。"""


class Narrator:
    """叙事者 — 将事件序列转化为小说文本"""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def narrate_beat(
        self,
        beat_log: BeatLog,
        previous_context: str = "",
        char_name_map: dict = None,
    ) -> str:
        """将单轮 Beat 的事件转化为文本, 带前文上下文"""
        if not beat_log.events:
            return ""

        event_text = self._format_events(beat_log.events, char_name_map or {})

        # 构建角色姓名提示
        name_hint = ""
        if char_name_map:
            name_list = ", ".join(f"{k}={v}" for k, v in char_name_map.items())
            name_hint = f"\n角色id映射: {name_list}"

        if previous_context:
            user_prompt = (
                f"【前文】\n{previous_context[-500:]}\n\n"
                f"【新事件】{name_hint}\n{event_text}\n\n"
                f"请根据新事件续写, 不要重复描写场景, 直接从上一段结尾处继续推进情节。保持角色姓名一致。"
            )
        else:
            user_prompt = (
                f"请根据以下事件写出叙事段落:{name_hint}\n\n{event_text}"
            )

        try:
            prose = self.llm.chat(
                system_prompt=NARRATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.5,
            )
            return prose.strip()
        except Exception as e:
            return f"[叙事生成失败: {e}]"

    def narrate_chapter(
        self,
        beat_logs: list[BeatLog],
        char_name_map: dict = None,
    ) -> str:
        """将整章的所有 Beat 转化为文本, 每 Beat 携带前文上下文"""
        paragraphs = []
        running_context = ""

        for log in beat_logs:
            paragraph = self.narrate_beat(
                log,
                previous_context=running_context,
                char_name_map=char_name_map,
            )
            if paragraph and len(paragraph) > 10:
                paragraphs.append(paragraph)
                # 累积上下文, 只保留最近 1000 字
                running_context = (running_context + "\n" + paragraph)[-1000:]

        return "\n\n".join(paragraphs)


    def narrate_chapter_batched(self, beat_logs: list, char_name_map: dict = None, batch_size: int = 3) -> str:
        """批量化叙事: batch_size 个 Beat 合并为一次 LLM 调用"""
        if not beat_logs:
            return ""
        paragraphs, running_context = [], ""
        for i in range(0, len(beat_logs), batch_size):
            batch = beat_logs[i:i+batch_size]
            all_events = [ev for log in batch for ev in log.events]
            if not all_events:
                continue
            event_text = self._format_events(all_events, char_name_map or {})
            if running_context:
                prompt = f"【前文】\n{running_context[-500:]}\n\n【新事件】\n{event_text}\n\n请根据新事件续写, 不要重复描写场景。保持角色姓名一致。"
            else:
                prompt = f"请根据以下事件写出叙事段落:\n\n{event_text}"
            try:
                prose = self.llm.chat(NARRATOR_SYSTEM_PROMPT, prompt, temperature=0.5)
                if prose and len(prose.strip()) > 10:
                    paragraphs.append(prose.strip())
                    running_context = (running_context + "\n" + prose)[-1000:]
            except Exception as e:
                paragraphs.append(f"[叙事生成失败: {e}]")
        return "\n\n".join(paragraphs)


    def rewrite_chapter(self, beat_logs: list, world, chars: list = None, director_plan: dict = None) -> str:
        if not beat_logs:
            return ""
        all_events = [ev for log in beat_logs for ev in log.events]
        if not all_events:
            return ""
        event_text = self._format_events(all_events, {})
        char_info = ""
        if chars:
            profs = []
            for c in chars:
                d = getattr(c.motivation, 'deep_desire', '') if hasattr(c, 'motivation') else ''
                f = getattr(c.motivation, 'fear', '') if hasattr(c, 'motivation') else ''
                t = ', '.join(getattr(c.personality, 'traits', []) if hasattr(c, 'personality') else [])
                e = getattr(c.emotional_state, 'mood_label', '平静') if hasattr(c, 'emotional_state') else '平静'
                profs.append(f"{c.name}: {t} | 动机:{d} | 恐惧:{f} | 情绪:{e}")
            char_info = chr(10).join(profs)
        plan = ""
        if director_plan:
            plan = f"基调:{director_plan.get('chapter_type','')} 张力:{director_plan.get('target_tension','')} 催化剂:{director_plan.get('catalyst','')}"
        wi = f"{getattr(world,'name','')} {getattr(world,'description','')[:200]}"
        ti = getattr(world.timeline, 'current_time', '') if hasattr(world, 'timeline') else ''
        prompt = WRITER_PROMPT.format(raw_text=event_text[:2000], char_info=char_info[:1000], world_context=wi[:200], time=ti, plan=plan[:200])
        try:
            ch = self.llm.chat(NARRATOR_SYSTEM_PROMPT, prompt, temperature=0.6, max_tokens=2000)
            return ch.strip() if ch else event_text
        except Exception:
            return event_text

    def narrate_parallel(self, parallel_engine, char_name_map: dict = None) -> str:
        """将 ParallelEngine 的多条线交织成一章"""
        active = {lid: l for lid, l in parallel_engine.lines.items() if l.is_active}
        if not active:
            return ""

        paragraphs = []
        running_context = ""
        pov_id = parallel_engine.current_pov

        def _narrate_batch(events, context):
            if not events:
                return ""
            lines = []
            for ev in events[:5]:
                eid = getattr(ev, 'agent_id', '') if hasattr(ev, 'agent_id') else ''
                name = (char_name_map or {}).get(eid, eid)
                action = getattr(ev, 'action_type', '')
                content = getattr(ev, 'content', '')[:80]
                outcome = getattr(ev, 'outcome', '')[:60]
            event_text = "\n".join(lines)
            prompt = f"【前文】\n{context[-400:]}\n\n【新事件】\n{event_text}\n\n请续写，不要重复描写场景。保持角色姓名一致。" if context else f"请根据以下事件写出叙事段落:\n\n{event_text}"
            try:
                prose = self.llm.chat(NARRATOR_SYSTEM_PROMPT, prompt, temperature=0.5)
                return prose.strip()
            except:
                return ""

        # 主 POV 线
        pov_line = active.get(pov_id)
        if pov_line and pov_line.pending_events:
            text = _narrate_batch(pov_line.pending_events, running_context)
            if text:
                paragraphs.append(text)
                running_context = (running_context + "\n" + text)[-1000:]

        # 其他线
        for lid, line in active.items():
            if lid == pov_id or not line.pending_events:
                continue
            text = _narrate_batch(line.pending_events, running_context)
            if text:
                transition = f"\n\n=== 与此同时, 在{line.name} ===\n\n"
                paragraphs.append(transition + text)
                running_context = (running_context + "\n" + text)[-1000:]

        # 清空待叙事事件
        for line in active.values():
            line.pending_events = []

        return "\n\n".join(paragraphs)

    def _format_events(self, events: list[NarrativeEvent], char_name_map: dict) -> str:
        """将事件列表格式化为 LLM 可读的文本, 附带角色名"""
        lines = []
        for ev in events:
            name = char_name_map.get(ev.agent_id, ev.agent_id)
            action_verb = {
                "DIALOGUE": "对话",
                "ACT": "行动",
                "INNER": "内心",
                "OBSERVE": "观察",
                "WAIT": "等待",
            }.get(ev.action_type, ev.action_type)

            if ev.action_type == "DIALOGUE":
                target_name = char_name_map.get(ev.target_id, ev.target_id) if ev.target_id else ""
                lines.append(f"[{name}→{target_name}] {ev.content[:150]}")
            elif ev.action_type == "INNER":
                lines.append(f"[{name}内心] {ev.content[:150]}")
            else:
                lines.append(f"[{name}{action_verb}] {ev.content[:100]}")
            if ev.outcome:
                lines.append(f"   → {ev.outcome[:60]}")
        return "\n".join(lines)
