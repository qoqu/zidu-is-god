"""
场景配置检查 — 在模拟前检查每个场景的角色配置是否完整
"""
from app.characters.schema import SceneRole, DecisionWeight


def check_scene_cast(scenes: list, characters: dict) -> list:
    """
    检查场景角色配置, 返回缺失列表
    
    Args:
        scenes: [{"id","name","cast":[{"char_id","scene_role","weight"}]}]
        characters: {char_id: Character}
    
    Returns:
        [{"scene":场景名, "missing_roles":[角色类型], "suggestion":"建议"}]
    """
    warnings = []
    
    for scene in scenes:
        cast = scene.get("cast", [])
        assigned_roles = {c.get("scene_role", "") for c in cast}
        
        # 每个场景至少需要主角
        if SceneRole.PROTAGONIST not in assigned_roles:
            warnings.append({
                "scene": scene["name"],
                "missing_roles": [SceneRole.PROTAGONIST],
                "suggestion": f"场景\"{scene['name']}\"缺少主角, 请分配一个角色"
            })
        
        # 有裁判场景就需要竞争者
        if SceneRole.JUDGE in assigned_roles and SceneRole.COMPETITOR not in assigned_roles:
            warnings.append({
                "scene": scene["name"],
                "missing_roles": [SceneRole.COMPETITOR],
                "suggestion": f"场景\"{scene['name']}\"有裁判但没有竞争者"
            })
    
    return warnings


def build_scene_cast(scene_id: str, all_chars: list, scene_name: str = "") -> list:
    """
    为一个场景构建 cast 列表
    
    从所有角色中筛选出归属该场景的角色, 自动设置权重
    """
    cast = []
    for char in all_chars:
        # 检查角色是否属于这个场景
        char_scene = getattr(char, 'current_location', '') or ''
        if char_scene != scene_id:
            continue
        
        scene_role = getattr(char, 'scene_role', SceneRole.SUPPORTING)
        weight = DecisionWeight.WEIGHT_MAP.get(scene_role, DecisionWeight.LIGHT)
        
        cast.append({
            "char_id": char.id,
            "char_name": char.name,
            "scene_role": scene_role,
            "weight": weight,
        })
    
    if not cast:
        # 没有角色直接归属此场景, 使用所有角色
        for char in all_chars:
            role = getattr(char, 'scene_role', SceneRole.SUPPORTING)
            weight = DecisionWeight.WEIGHT_MAP.get(role, DecisionWeight.LIGHT)
            cast.append({
                "char_id": char.id,
                "char_name": char.name,
                "scene_role": role,
                "weight": weight,
            })
    
    return cast


def format_cast_warning(warnings: list) -> str:
    """将缺失提醒格式化为文本"""
    if not warnings:
        return ""
    lines = ["⚠️ 场景角色配置不完整:"]
    for w in warnings:
        lines.append(f"  - {w['suggestion']}")
    lines.append("请在模拟前补充配置。")
    return "\n".join(lines)
