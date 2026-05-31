"""
WorldBuild 交互引导 — 从一句话到结构化世界观
"""
from typing import Optional
from app.worldbuilding.state import SessionState, WORLD_TYPE_CATALOG
from app.llm.client import LLMClient, LLMError


class WorldBuildAgent:
    """
    交互式世界观构建
    
    用法:
      agent = WorldBuildAgent(llm)
      msg = agent.start()  # 返回第一条引导消息
      # 用户回复后:
      msg = agent.handle_input(user_text)
      # 反复直到 agent.done == True
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.state = SessionState()
        self.done = False

    def start(self) -> str:
        """开始交互, 返回第一条引导消息"""
        self.state.stage = "world_type"
        options = "\n".join(f"{i+1}. {t}" for i, t in enumerate(self.state.get_type_options()))
        return (
            "好的, 让我们来构建这个世界。\n\n"
            f"请选择一个世界观类型:\n\n{options}\n\n"
            "直接输入数字或类型名称即可。"
        )

    def handle_input(self, text: str) -> str:
        """处理用户输入, 返回下一步引导"""
        stage = self.state.stage
        
        if stage == "world_type":
            return self._handle_world_type(text)
        elif stage == "world_subtype":
            return self._handle_subtype(text)
        elif stage == "world_power":
            return self._handle_power(text)
        elif stage == "world_conflict":
            return self._handle_conflict(text)
        elif stage == "world_name":
            return self._handle_name(text)
        elif stage == "world_summary":
            return self._handle_summary(text)
        else:
            return "会话完成, 可以继续下一步。"

    # ─── 各阶段处理 ─────────────────────────────────────

    def _handle_world_type(self, text: str) -> str:
        types = self.state.get_type_options()
        chosen = self._match_option(text, types)
        if not chosen:
            return f"请从以下类型中选择:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(types))
        
        self.state.world_type = chosen
        self.state.stage = "world_subtype"
        
        subtypes = self.state.get_subtype_options()
        if subtypes:
            return (
                f"好的, {chosen}。具体是哪个方向?\n\n"
                + "\n".join(f"{i+1}. {s}" for i, s in enumerate(subtypes))
                + "\n\n也可以自己输入其他方向或直接回车跳过。"
            )
        else:
            return self._next_stage()

    def _handle_subtype(self, text: str) -> str:
        subtypes = self.state.get_subtype_options()
        chosen = self._match_option(text, subtypes)
        self.state.world_subtype = chosen or subtypes[0] if subtypes else ""
        return self._next_stage()

    def _handle_power(self, text: str) -> str:
        if text and len(text) > 2:
            self.state.power_system = text
        else:
            options = self.state.get_power_options()
            default = options[0] if options else ""
            self.state.power_system = self._match_option(text, options) or default
        return self._next_stage()

    def _handle_conflict(self, text: str) -> str:
        if text and len(text) > 2:
            self.state.core_conflict = text
        else:
            self.state.core_conflict = "待定"
        return self._next_stage()

    def _handle_name(self, text: str) -> str:
        self.state.world_name = text.strip() if text.strip() else f"未命名{self.state.world_type}世界"
        self.state.stage = "world_summary"
        return (
            f"好的, 世界名为「{self.state.world_name}」。\n\n"
            f"现在请写一段对这个世界的整体描述,\n"
            f"可以补充世界观文本中没有提到的信息,\n"
            f"或者直接回车使用自动生成的摘要。"
        )

    def _handle_summary(self, text: str) -> str:
        if text and len(text) > 10:
            self.state.world_summary = text
        else:
            self.state.world_summary = self._auto_summary()
        
        self.done = True
        self.state.stage = "done"
        return (
            f"✅ 世界观构建完成!\n\n"
            f"世界名称: {self.state.world_name}\n"
            f"类型: {self.state.world_type} - {self.state.world_subtype}\n"
            f"力量体系: {self.state.power_system}\n"
            f"核心冲突: {self.state.core_conflict}\n\n"
            f"{self.state.world_summary[:200]}...\n\n"
            f"接下来可以进入场景设计阶段。"
        )

    def _next_stage(self) -> str:
        """进入下一阶段"""
        if self.state.stage == "world_subtype":
            self.state.stage = "world_power"
            options = self.state.get_power_options()
            opts = "\n".join(f"{i+1}. {o}" for i, o in enumerate(options)) if options else ""
            return (
                f"好的。这个世界的力量体系是什么样的?\n\n{opts}\n\n"
                f"选择一项或自己描述。"
            )
        elif self.state.stage == "world_power":
            self.state.stage = "world_conflict"
            return (
                f"核心冲突是什么?\n"
                f"(例如: 正邪对立 / 资源争夺 / 阶级压迫 / 上古秘密 / 你自己定的)"
            )
        elif self.state.stage == "world_conflict":
            self.state.stage = "world_name"
            return f"这个世界叫什么名字?"
        return ""

    def _match_option(self, text: str, options: list) -> str:
        """匹配用户输入到选项列表"""
        text = text.strip()
        if not text or not options:
            return ""
        # 数字匹配
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(options):
                return options[idx]
        # 文本匹配
        for opt in options:
            if text.lower() in opt.lower() or opt.lower() in text.lower():
                return opt
        return ""

    def _auto_summary(self) -> str:
        """自动生成世界摘要"""
        parts = [
            f"这是一个{self.state.world_type}世界",
        ]
        if self.state.world_subtype:
            parts.append(f"属于{self.state.world_subtype}类型")
        if self.state.power_system:
            parts.append(f"力量体系采用{self.state.power_system}")
        if self.state.core_conflict:
            parts.append(f"核心冲突围绕{self.state.core_conflict}展开")
        return "；".join(parts)
