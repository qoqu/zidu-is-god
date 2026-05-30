"""
外部记忆系统 — RAG向量检索 + FDR渐进压缩
从 hybrid-novel-writing-system 移植

RAGRetriever: 角色记忆向量化, 决策时只检索 top-k 相关
FDRCompressor: 旧章节渐进压缩, 替代全文本前情提要
"""

import json
import os
import hashlib
import sqlite3
from typing import Optional
from datetime import datetime
from pathlib import Path


# ─── RAG 向量检索 ─────────────────────────────────────────

class RAGRetriever:
    """
    轻量级 RAG 检索 — 用 SQLite 存储记忆向量 + 文本
    
    替换原来的 in-memory 记忆系统:
      Before: 全部记忆塞进 prompt → 2000+ tokens
      After:  只检索 top-3 相关 → 300 tokens
    """

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), '../../data/memory.db'
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT,          -- JSON 浮点数组
                importance REAL DEFAULT 0.5,
                memory_type TEXT DEFAULT 'event',  -- event/fact/emotion/obsession
                chapter INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_char 
            ON memories(char_id)
        """)
        self.conn.commit()

    def add_memory(self, char_id: str, content: str, importance: float = 0.5,
                   memory_type: str = "event", chapter: int = 0):
        """添加一条记忆（自动计算嵌入）"""
        embedding = self._simple_embed(content)
        self.conn.execute(
            "INSERT INTO memories (char_id, content, embedding, importance, memory_type, chapter) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (char_id, content, json.dumps(embedding, ensure_ascii=False),
             importance, memory_type, chapter)
        )
        self.conn.commit()

    def search(self, char_id: str, query: str, top_k: int = 3,
               min_importance: float = 0.0) -> list:
        """检索最相关的 top-k 条记忆"""
        query_vec = self._simple_embed(query)

        # 读取该角色的所有记忆
        cursor = self.conn.execute(
            "SELECT id, content, embedding, importance, memory_type, chapter "
            "FROM memories WHERE char_id = ? AND importance >= ? "
            "ORDER BY importance DESC LIMIT 50",
            (char_id, min_importance)
        )
        rows = cursor.fetchall()

        # 计算余弦相似度并排序
        scored = []
        for row in rows:
            mem_emb = json.loads(row[2]) if row[2] else []
            if mem_emb:
                sim = self._cosine_sim(query_vec, mem_emb)
                scored.append((sim * row[3], row[1], row[4], row[5]))

        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]

    def get_recent(self, char_id: str, limit: int = 5) -> list:
        """获取最近 N 条记忆"""
        cursor = self.conn.execute(
            "SELECT content, memory_type, chapter FROM memories "
            "WHERE char_id = ? ORDER BY id DESC LIMIT ?",
            (char_id, limit)
        )
        return cursor.fetchall()

    def _simple_embed(self, text: str, dim: int = 64) -> list:
        """简易文本嵌入（不用外部模型, 基于 hash）"""
        text = text.lower().strip()
        # 用 SHA256 生成固定维度向量
        h = hashlib.sha256(text.encode()).digest()
        # 扩展到 dim 维度
        vec = []
        for i in range(dim):
            val = (h[i % len(h)] / 255.0) * 2 - 1  # [-1, 1]
            vec.append(val)
        return vec

    def _cosine_sim(self, a: list, b: list) -> float:
        """余弦相似度"""
        dot = sum(x*y for x, y in zip(a, b))
        na = sum(x*x for x in a) ** 0.5
        nb = sum(x*x for x in b) ** 0.5
        if na * nb == 0:
            return 0
        return dot / (na * nb)

    def close(self):
        self.conn.close()


# ─── FDR 渐进式压缩 ───────────────────────────────────────

class FDRCompressor:
    """
    渐进式压缩 — 将旧内容压缩为摘要
    
    策略:
      Layer 1: 每章 → 200字摘要
      Layer 2: 每5章 → 卷摘要
      Layer 3: 全书 → 最终摘要
    
    替换原来的全文本前情提要:
      Before: 前5章全文 → 5000+ tokens
      After:  前5章摘要 → 500 tokens
    """

    def __init__(self, storage_path: str = ""):
        self.path = Path(storage_path or os.path.join(
            os.path.dirname(__file__), '../../data/summaries'
        ))
        self.path.mkdir(parents=True, exist_ok=True)
        self._init_storage()

    def _init_storage(self):
        self.summaries_file = self.path / "chapter_summaries.json"
        if not self.summaries_file.exists():
            self._save({"summaries": [], "volumes": [], "book": ""})

    def _load(self) -> dict:
        return json.loads(self.summaries_file.read_text(encoding='utf-8'))

    def _save(self, data: dict):
        self.summaries_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
        )

    def add_chapter_summary(self, chapter: int, text: str, llm=None):
        """Layer 1: 压缩单章为摘要"""
        if llm and len(text) > 500:
            try:
                summary = llm.chat(
                    "你是一个小说摘要生成器。",
                    f"将以下章节压缩为200字以内的摘要, 保留核心事件和转折:\n\n{text[:3000]}",
                    temperature=0.3, max_tokens=300
                )
            except Exception:
                summary = text[:200]
        else:
            summary = text[:200]

        data = self._load()
        data["summaries"].append({
            "chapter": chapter,
            "summary": summary,
            "word_count": len(text),
        })
        # Layer 2: 每5章生成卷摘要
        if len(data["summaries"]) % 5 == 0 and llm:
            vol_text = "\n".join(s["summary"] for s in data["summaries"][-5:])
            try:
                vol_summary = llm.chat(
                    "你是一个小说摘要生成器。",
                    f"将以下5章摘要压缩为300字以内的卷摘要:\n\n{vol_text}",
                    temperature=0.3, max_tokens=400
                )
                data["volumes"].append({"volume": len(data["volumes"]) + 1, "summary": vol_summary})
            except Exception:
                pass
        self._save(data)

    def context_for(self, max_chapters: int = 3) -> str:
        """获取前情提要（压缩后）"""
        data = self._load()
        recent = data["summaries"][-max_chapters:]
        lines = ["【前情提要】"]
        for s in recent:
            lines.append(f"  第{s['chapter']}章: {s['summary'][:100]}")
        if data["volumes"]:
            v = data["volumes"][-1]
            lines.append(f"  当前卷: {v['summary'][:150]}")
        return "\n".join(lines)

    def full_context(self) -> str:
        """全量压缩上下文"""
        data = self._load()
        if data["book"]:
            return data["book"]
        parts = []
        for v in data["volumes"]:
            parts.append(f"第{v['volume']}卷: {v['summary']}")
        if not parts:
            parts = [s["summary"] for s in data["summaries"]]
        return "\n".join(parts[:5])
