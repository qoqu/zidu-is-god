"""
世界观构建状态 — 贯穿 WorldBuild → SceneDesign → CharacterDesign 的共享状态
"""
from dataclasses import dataclass, field
from typing import Optional
from app.world.world_types import WORLD_TYPE_CATALOG


@dataclass
class SessionState:
    """一次完整的世界创作会话"""
    stage: str = "world_type"  # world_type / world_detail / scene_design / character_design / done
    
    # WorldBuild 产出
    world_type: str = ""
    world_subtype: str = ""
    world_name: str = ""
    power_system: str = ""
    core_conflict: str = ""
    world_vibe: str = ""
    world_summary: str = ""  # 最终产出文本
    direction_text: str = ""  # 方向文本
    direction_params: dict = field(default_factory=dict)  # PlotDirector 配置
    target_words: int = 20000  # 每卷目标字数
    volume_manager: object = None  # VolumeManager 实例
    current_volume: int = 1
    
    # Scene Design 产出
    scenes: list = field(default_factory=list)  # [{id, name, stages:[舞台名], connections}]
    scene_map_text: str = ""
    
    # Character Design 产出
    protagonist: dict = field(default_factory=dict)
    supporting_chars: list = field(default_factory=list)
    antagonist: dict = field(default_factory=dict)
    
    def get_type_options(self) -> list:
        """返回所有世界类型选项"""
        return list(WORLD_TYPE_CATALOG.keys())
    
    def get_subtype_options(self) -> list:
        """返回当前类型的子方向"""
        info = WORLD_TYPE_CATALOG.get(self.world_type, {})
        return info.get("aliases", [])
    
    def get_power_options(self) -> list:
        info = WORLD_TYPE_CATALOG.get(self.world_type, {})
        return info.get("power_system", [])
    
    def get_location_options(self) -> list:
        info = WORLD_TYPE_CATALOG.get(self.world_type, {})
        return info.get("location_types", [])
    
    def get_faction_options(self) -> list:
        info = WORLD_TYPE_CATALOG.get(self.world_type, {})
        return info.get("faction_types", [])

    def to_world_description(self) -> str:
        """将交互结果转为世界描述文本 (Engine 可解析)"""
        lines = [
            f"世界观: {self.world_name or '未命名'}",
            f"类型: {self.world_type} - {self.world_subtype}",
            f"力量体系: {self.power_system}",
            f"核心冲突: {self.core_conflict}",
            f"基调: {self.world_vibe}",
            f"",
            self.world_summary,
        ]
        return "\n".join(lines)


# 场景模板 (按类型推荐)
SCENE_TEMPLATES = {
    "仙侠": [
        {"name": "外门食堂", "vibe": "嘈杂", "typical_npcs": ["食堂大妈(情报贩子)", "恶霸师兄"], "events": ["冲突","情报交换"]},
        {"name": "后山竹林", "vibe": "安静", "typical_npcs": ["隐居老人(导师)", "灵兽"], "events": ["修炼","秘密发现"]},
        {"name": "演武场", "vibe": "喧闹", "typical_npcs": ["教头", "同期弟子"], "events": ["比试","公开冲突"]},
        {"name": "藏经阁", "vibe": "肃穆", "typical_npcs": ["管理员(深藏不露)"], "events": ["禁书","秘密通道"]},
        {"name": "外门宿舍", "vibe": "日常", "typical_npcs": ["舍友"], "events": ["夜间事件","舍友关系"]},
    ],
    "玄幻": [
        {"name": "家族演武场", "vibe": "激烈", "typical_npcs": ["族长", "竞争者"], "events": ["测试","羞辱"]},
        {"name": "后山禁地", "vibe": "神秘", "typical_npcs": ["守山人", "妖兽"], "events": ["奇遇","封印"]},
        {"name": "城镇集市", "vibe": "热闹", "typical_npcs": ["商贩", "神秘老者"], "events": ["交易","线索"]},
    ],
    "都市": [
        {"name": "教室", "vibe": "日常", "typical_npcs": ["老师", "同学"], "events": ["冲突","表现"]},
        {"name": "天台", "vibe": "安静", "typical_npcs": ["神秘转学生"], "events": ["秘密对话","异能觉醒"]},
        {"name": "老旧小巷", "vibe": "危险", "typical_npcs": ["混混", "流浪者"], "events": ["战斗","线索"]},
    ],
    "奇幻": [
        {"name": "乡村酒馆", "vibe": "温暖", "typical_npcs": ["酒馆老板", "冒险者"], "events": ["委托","情报"]},
        {"name": "地下城入口", "vibe": "险恶", "typical_npcs": ["守卫", "冒险者公会代表"], "events": ["探索","陷阱"]},
        {"name": "精灵遗迹", "vibe": "神秘", "typical_npcs": ["精灵哨兵", "古代机关"], "events": ["发现","危机"]},
    ],
    "科幻": [
        {"name": "空间站港湾区", "vibe": "嘈杂", "typical_npcs": ["港口管理员", "走私者"], "events": ["到达","检查"]},
        {"name": "实验室", "vibe": "冰冷", "typical_npcs": ["首席科学家", "安保"], "events": ["实验事故","秘密"]},
        {"name": "地下街区", "vibe": "危险", "typical_npcs": ["黑市商人", "黑客"], "events": ["交易","追捕"]},
    ],
    "末世": [
        {"name": "避难所", "vibe": "压抑", "typical_npcs": ["管理员", "幸存者"], "events": ["物资分配","冲突"]},
        {"name": "废墟街道", "vibe": "危险", "typical_npcs": ["掠夺者", "变异生物"], "events": ["搜索","战斗"]},
        {"name": "废弃实验室", "vibe": "诡异", "typical_npcs": ["前研究员(幸存)"], "events": ["发现","触发事件"]},
    ],
    "悬疑": [
        {"name": "警局档案室", "vibe": "压抑", "typical_npcs": ["老警员", "法医"], "events": ["线索","档案"]},
        {"name": "废弃医院", "vibe": "恐怖", "typical_npcs": ["流浪汉", "不明存在"], "events": ["探索","惊吓"]},
        {"name": "死者住所", "vibe": "诡异", "typical_npcs": ["邻居", "房东"], "events": ["搜查","发现"]},
    ],
    "古代言情": [
        {"name": "闺阁", "vibe": "精致", "typical_npcs": ["丫鬟", "嬷嬷"], "events": ["秘密","谋划"]},
        {"name": "后花园", "vibe": "优美", "typical_npcs": ["姐妹", "意外访客"], "events": ["偶遇","偷听"]},
        {"name": "前厅", "vibe": "正式", "typical_npcs": ["长辈", "客人"], "events": ["相亲","冲突"]},
    ],
    "现代言情": [
        {"name": "办公室", "vibe": "紧张", "typical_npcs": ["上司", "同事"], "events": ["冲突","表现"]},
        {"name": "咖啡厅", "vibe": "轻松", "typical_npcs": ["服务员", "约会对象"], "events": ["偶遇","对话"]},
        {"name": "电梯", "vibe": "密闭", "typical_npcs": ["陌生人"], "events": ["意外","尴尬相遇"]},
    ],
    "历史": [
        {"name": "朝堂", "vibe": "威严", "typical_npcs": ["皇帝", "大臣"], "events": ["争论","弹劾"]},
        {"name": "边关军营", "vibe": "肃杀", "typical_npcs": ["将军", "士兵"], "events": ["战事","密谋"]},
        {"name": "市井街巷", "vibe": "热闹", "typical_npcs": ["商贩", "说书人"], "events": ["情报","隐藏身份"]},
    ],
    "默认": [
        {"name": "主角住所", "vibe": "日常", "typical_npcs": ["邻居", "家人"], "events": ["日常","事件触发"]},
        {"name": "集会场所", "vibe": "热闹", "typical_npcs": ["各色人物"], "events": ["信息收集","冲突"]},
        {"name": "未知区域", "vibe": "神秘", "typical_npcs": ["守护者", "原住民"], "events": ["探索","发现"]},
    ],
}

def get_scene_templates(world_type: str) -> list:
    return SCENE_TEMPLATES.get(world_type, SCENE_TEMPLATES["默认"])
