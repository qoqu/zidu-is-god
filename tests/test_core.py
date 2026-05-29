"""
Novel World Engine — 核心模块单元测试
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

# ─── Character 模型 ───────────────────────────────────────

def test_character_creation():
    from app.characters.schema import Character, EmotionalState, CharacterStats
    c = Character(id="test_1", name="测试角色")
    assert c.id == "test_1"
    assert c.name == "测试角色"
    assert isinstance(c.emotional_state, EmotionalState)
    assert isinstance(c.stats, CharacterStats)
    print("  ✅ Character 创建")

def test_emotional_state():
    from app.characters.schema import EmotionalState
    e = EmotionalState()
    assert e.mood_label == "平静"
    assert e.valence == 0.0
    e.valence = 0.5
    e.arousal = 0.4
    assert e._map_emotion(0.5, 0.4) == "喜悦"
    print("  ✅ 情绪系统")

def test_character_stats():
    from app.characters.schema import CharacterStats, Injury
    s = CharacterStats()
    assert s.hp == 100
    s.apply_damage(30, "左臂")
    assert s.hp == 70
    assert len(s.injuries) == 1
    s.rest(4)
    assert s.stamina == 100
    print("  ✅ 数值/伤势系统")

def test_influence():
    from app.characters.schema import Influence
    inf = Influence(economic=50, political=10, mystical=30)
    assert inf.primary() == "economic"
    top = inf.top_three()
    assert top[0] == ("economic", 50)
    assert "财富(50)" in inf.summary()
    print("  ✅ 影响力系统")

def test_resource_ledger():
    from app.characters.schema import ResourceLedger
    l = ResourceLedger()
    l.add("青云剑", type="weapon", durability=100)
    l.add("培元丹", type="potion", quantity=5)
    assert len(l.get_active()) == 2
    l.consume("item_0002", 2)
    assert l.items["item_0002"].quantity == 3
    assert "青云剑" in l.summary()
    print("  ✅ 资源账本")


# ─── Memory 系统 ──────────────────────────────────────────

def test_memory_basic():
    from app.characters.memory import MemorySystem
    ms = MemorySystem("测试")
    ms.remember("重要事件", importance=0.8, emotional_intensity=0.7)
    assert ms.count()["total"] == 1
    mems = ms.recall("重要", top_k=3)
    assert len(mems) >= 1
    print("  ✅ 记忆存储/检索")

def test_memory_obsession():
    from app.characters.memory import MemorySystem
    ms = MemorySystem("测试")
    ms.add_obsession("杀父之仇", obs_type="grudge", intensity=0.9)
    assert len(ms.obsessions) == 1
    text = ms.obsessions_text()
    assert "杀父之仇" in text
    # 执念永远在 prompt 第一条
    prompt = ms.format_for_prompt(context="无关内容")
    assert "杀父之仇" in prompt
    print("  ✅ 执念机制")

def test_memory_consolidation():
    from app.characters.memory import MemorySystem
    ms = MemorySystem("测试")
    for i in range(20):
        ms.remember(f"日常事件{i}", importance=0.2)
    ms.remember("刻骨铭心", importance=0.95)
    ms.consolidate(chapter=1)
    stats = ms.count()
    assert stats["long_term"] > 0 or stats["core"] > 0
    print("  ✅ 记忆固化")


# ─── 事件与因果链 ─────────────────────────────────────────

def test_narrative_event():
    from app.engine.events import NarrativeEvent
    ev = NarrativeEvent(1, 1, agent_id="c1", action_type="ACT",
                         content="拔剑", because="受到挑衅")
    assert ev.because == "受到挑衅"
    ev.therefore.append("双方对峙")
    assert len(ev.therefore) == 1
    print("  ✅ 因果链")


# ─── 质量检查 ─────────────────────────────────────────────

def test_quality_checker():
    from app.narrator.quality import QualityChecker
    qc = QualityChecker()
    text = "突然, 他发现了一个秘密。\"你在这里做什么?\"他问道。"
    result = qc.check(text, chapter_num=1)
    assert "scores" in result
    assert "total" in result
    assert result["max"] == 80
    print("  ✅ 质量检查")


# ─── 世界模型 ─────────────────────────────────────────────

def test_world_schema():
    from app.world.schema import World, Location
    w = World(id="test", name="测试世界")
    w.locations["loc_1"] = Location(id="loc_1", name="演武场")
    assert len(w.locations) == 1
    w.advance_time()
    assert "第1天" in w.timeline.current_time
    print("  ✅ 世界模型")

def test_weather():
    from app.world.weather import WeatherSystem
    ws = WeatherSystem()
    for _ in range(10):
        fx = ws.tick()
    assert "temp" in fx
    assert ws.current in ws.PATTERNS
    print("  ✅ 天气系统")

def test_rumor():
    from app.world.rumors import RumorSystem
    from app.world.schema import World, Location
    w = World(id="test")
    w.locations["l1"] = Location(id="l1", name="地点")
    rs = RumorSystem()
    rs.generate("主角被人打了", "l1", influence_weight=30)
    assert len(rs.active_rumors) == 1
    text = rs.rumor_text_for("l1")
    assert "主角" in text
    print("  ✅ 谣言系统")


# ─── 张力计算 ─────────────────────────────────────────────

def test_tension():
    from app.plot.tension import calculate_tension, suggest_target_tension
    from app.world.schema import World
    w = World(id="test")
    t = suggest_target_tension(1, 0.5)
    assert 0 < t <= 1.0
    print("  ✅ 张力计算")


# ─── 持久化 ───────────────────────────────────────────────

def test_persistence():
    from app.persistence import save_story, load_story, list_saves
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), "nwe_test_save.json")
    # 测试保存
    from app.world.schema import World, Location
    from app.characters.schema import Character
    w = World(id="test", name="测试世界")
    w.locations["l1"] = Location(id="l1", name="地点")
    c = Character(id="c1", name="角色1")
    chapters = [{"number": 1, "text": "第一章内容", "word_count": 100, "quality": 60, "quality_passed": True}]
    save_story(w, [c], chapters, current_chapter=1, total_chapters=3, filepath=tmp)
    assert os.path.exists(tmp)
    # 测试加载
    data = load_story(tmp)
    assert data["world"]["name"] == "测试世界"
    assert len(data["chapters"]) == 1
    # 测试列表
    saves = list_saves(os.path.dirname(tmp))
    assert len(saves) >= 1
    os.remove(tmp)
    print("  ✅ 持久化")


# ─── 运行 ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Novel World Engine — 单元测试")
    print("=" * 50)

    tests = [
        test_character_creation,
        test_emotional_state,
        test_character_stats,
        test_influence,
        test_resource_ledger,
        test_memory_basic,
        test_memory_obsession,
        test_memory_consolidation,
        test_narrative_event,
        test_quality_checker,
        test_world_schema,
        test_weather,
        test_rumor,
        test_tension,
        test_persistence,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败, {len(tests)} 总计")
