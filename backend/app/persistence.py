"""
Persistence — 保存/加载故事进度
"""

import json
import os
from datetime import datetime
from typing import Optional


def save_story(
    world,
    characters: list,
    chapters: list,
    current_chapter: int,
    total_chapters: int,
    filepath: str,
) -> str:
    """保存当前故事状态到 JSON 文件"""
    data = {
        "version": "0.1.0",
        "saved_at": datetime.now().isoformat(),
        "world": {
            "name": getattr(world, 'name', ''),
            "locations": {
                k: {"name": v.name, "description": v.description}
                for k, v in getattr(world, 'locations', {}).items()
            },
            "time": getattr(world.timeline, 'current_time', '') if hasattr(world, 'timeline') else '',
        },
        "characters": [
            {
                "id": c.id,
                "name": c.name,
                "location": c.current_location,
                "hp": c.stats.hp,
                "stamina": c.stats.stamina,
                "wealth": c.stats.wealth,
                "cultivation": getattr(c.stats, 'cultivation', 0),
                "emotion": c.emotional_state.mood_label,
                "obsessions": [
                    {"content": o["content"], "type": o["type"]}
                    for o in getattr(c.memory, 'obsessions', [])
                ],
            }
            for c in characters
        ],
        "chapters": [
            {
                "number": ch.get("number", i + 1),
                "text": ch.get("text", ""),
                "word_count": ch.get("word_count", len(ch.get("text", ""))),
                "quality": ch.get("quality", 0),
                "quality_passed": ch.get("quality_passed", False),
            }
            for i, ch in enumerate(chapters)
        ],
        "current_chapter": current_chapter,
        "total_chapters": total_chapters,
    }

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_story(filepath: str) -> dict:
    """从 JSON 文件加载故事状态"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"存档文件不存在: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def list_saves(directory: str = "saves") -> list[dict]:
    """列出所有存档"""
    os.makedirs(directory, exist_ok=True)
    saves = []
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".json"):
            fp = os.path.join(directory, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                saves.append({
                    "file": fn,
                    "name": data.get("world", {}).get("name", "未命名"),
                    "chapters": len(data.get("chapters", [])),
                    "saved_at": data.get("saved_at", ""),
                    "words": sum(c.get("word_count", 0) for c in data.get("chapters", [])),
                })
            except Exception:
                pass
    return saves
