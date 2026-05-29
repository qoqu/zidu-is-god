"""Narrator 批量化 — 多个 Beat 合为一次 LLM 调用"""
p = r'D:\Reasonix\Reasonixworkspace\novel-world-engine\backend\app\narrator\narrator.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 在 narrate_chapter 之后添加批量化方法
old = "    def narrate_chapter_stream(self, beat_logs: list, char_name_map: dict = None):"
new = """    def narrate_chapter_batched(self, beat_logs: list, char_name_map: dict = None, batch_size: int = 3):
        \"\"\"批量化叙事 — 多个 Beat 合并为一次 LLM 调用
        
        原来的 narrate_chapter 每 Beat 调一次 LLM, 3 Beat = 3 次调用。
        这个方法将 batch_size 个 Beat 合并成一次 LLM 调用, 大幅减少调用次数。
        
        例如 9 个 Beat, batch_size=3:
          Before: 9 次 LLM 调用 (9 × 20s = 180s)
          After:  3 次 LLM 调用 (3 × 30s = 90s)
          Speedup: 2x
        \"\"\"
        if not beat_logs:
            return ""
        
        paragraphs = []
        running_context = ""
        
        # 按 batch 分组
        for i in range(0, len(beat_logs), batch_size):
            batch = beat_logs[i:i+batch_size]
            
            # 合并 batch 内所有事件
            all_events = []
            for log in batch:
                for ev in log.events:
                    all_events.append(ev)
            
            if not all_events:
                continue
            
            # 格式化事件
            event_text = self._format_events(all_events, char_name_map or {})
            
            # 构建 prompt
            if running_context:
                prompt = f"【前文】\\n{running_context[-500:]}\\n\\n【新事件】\\n{event_text}\\n\\n请根据新事件续写, 不要重复描写场景。保持角色姓名一致。"
            else:
                prompt = f"请根据以下事件写出叙事段落:\\n\\n{event_text}"
            
            try:
                prose = self.llm.chat(self.NARRATOR_SYSTEM_PROMPT, prompt, temperature=0.5)
                if prose and len(prose.strip()) > 10:
                    paragraphs.append(prose.strip())
                    running_context = (running_context + "\\n" + prose)[-1000:]
            except Exception as e:
                paragraphs.append(f"[叙事生成失败: {e}]")
        
        return "\\n\\n".join(paragraphs)

    def narrate_chapter_stream(self, beat_logs: list, char_name_map: dict = None):"""

c = c.replace(old, new)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('OK 叙事批量化已添加')
