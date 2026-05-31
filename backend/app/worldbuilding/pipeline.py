"""
串联管道 — SessionState → World → Engine 一条龙运行
"""
from typing import Optional, Callable
from app.worldbuilding.state import SessionState
from app.world.schema import World, Location, Faction, Timeline
from app.characters.schema import Character, CharIdentity, CharPersonality, CharMotivation, CharacterRole
from app.llm.client import LLMClient


def build_world(state: SessionState) -> World:
    """从 SessionState 构建 World 对象"""
    world = World(
        id="world_001",
        name=state.world_name or "未命名世界",
        description=state.world_summary or state.to_world_description(),
    )
    world.raw_text = state.to_world_description()
    world.timeline = Timeline(current_time="第1天·清晨")
    world.extras = {"actions": [], "weather": [], "threats": [], "events": []}

    # 从 Scene Design 构建地点
    for i, s in enumerate(state.scenes):
        lid = s.get("id", f"loc_{i+1}")
        world.locations[lid] = Location(
            id=lid,
            name=s.get("name", f"场景{i+1}"),
            description=s.get("description", ""),
        )

    return world


def build_characters(state: SessionState) -> list[Character]:
    """从 SessionState 构建角色列表, 带场景角色和权重"""
    chars = []
    
    # 主角
    p = state.protagonist
    if p:
        char = Character(
            id="char_001",
            name=p.get("name", "未命名"),
            identity=CharIdentity(
                name=p.get("name", "未命名"),
                age=p.get("identity", "").split(",")[0].strip() if p.get("identity") else 16,
                occupation=p.get("identity", ""),
            ),
            personality=CharPersonality(
                traits=[p.get("personality", "成长型")],
            ),
            motivation=CharMotivation(
                deep_desire=p.get("desire", ""),
                fear=p.get("fatal_flaw", ""),
            ),
        )
        char.role = CharacterRole.PRIMARY
        char.scene_role = "protagonist"
        char.decision_weight = "full"
        char.current_location = p.get("scene", "")
        chars.append(char)
    
    # 配角
    for i, s in enumerate(state.supporting_chars):
        char = Character(
            id=f"char_{i+2:03d}",
            name=s.get("name", f"配角{i+1}"),
            identity=CharIdentity(name=s.get("name", f"配角{i+1}"), age=20),
            motivation=CharMotivation(deep_desire=s.get("role", "")),
        )
        char.role = CharacterRole.SECONDARY
        char.scene_role = s.get("scene_role", "supporting")
        char.decision_weight = s.get("weight", "light")
        char.current_location = s.get("scene", "")
        chars.append(char)
    
    # 反派
    a = state.antagonist
    if a and a.get("name"):
        char = Character(
            id=f"char_{len(chars)+1:03d}",
            name=a["name"],
            identity=CharIdentity(name=a["name"], age=20),
            motivation=CharMotivation(deep_desire=a.get("motive", "")),
        )
        char.role = CharacterRole.PRIMARY
        char.scene_role = "antagonist"
        char.decision_weight = "full"
        char.current_location = a.get("scene", "")
        chars.append(char)
    
    return chars


def build_plot_config(state: SessionState) -> dict:
    """从方向配置构建 PlotDirector 参数"""
    params = state.direction_params or {}
    return {
        "target_chapters": params.get("chapter_count", 6),
        "tension_profile": params.get("tension_curve", "normal"),
        "catalyst_type": params.get("catalyst_type", "general"),
        "direction_text": state.direction_text,
    }


def validate_cast(state: SessionState) -> list:
    """模拟前验证角色配置, 返回告警列表"""
    from app.worldbuilding.scene_cast import check_scene_cast
    scenes = []
    for s in state.scenes:
        cast = []
        # 检查主角
        if state.protagonist.get("scene") == s["name"]:
            cast.append({"scene_role": "protagonist"})
        # 检查配角
        for c in state.supporting_chars:
            if c.get("scene") == s["name"]:
                cast.append({"scene_role": c.get("scene_role", "supporting")})
        # 检查反派
        if state.antagonist.get("scene") == s["name"]:
            cast.append({"scene_role": "antagonist"})
        scenes.append({"name": s["name"], "cast": cast})
    return check_scene_cast(scenes, [])


def run_from_state(
    state: SessionState,
    progress_callback: Optional[Callable] = None,
    llm: Optional[LLMClient] = None,
) -> dict:
    """一条龙: SessionState → 模拟 → 结果"""
    # 1. 验证
    warnings = validate_cast(state)
    if warnings:
        return {"error": "角色配置不完整", "warnings": warnings}

    # 2. 构建
    world = build_world(state)
    chars = build_characters(state)
    plot_config = build_plot_config(state)
    
    # 3. 注入到 World
    if not hasattr(world, 'world_engine') or not world.world_engine:
        from app.world.engine import WorldEngine
        world.world_engine = WorldEngine(world)
    
    # 4. 跑模拟
    from app.core import simulate
    world_description = state.to_world_description()
    char_descriptions = [f"{c.name}, {c.identity.occupation if hasattr(c,'identity') else ''}" for c in chars]
    
    result = simulate(
        world_description=world_description,
        character_descriptions=char_descriptions,
        chapters=plot_config.get("target_chapters", 6),
        beats_per_chapter=3,
        fast_mode=True,
        progress_callback=progress_callback,
    )
    
    return result
