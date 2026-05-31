"""
Character Design 交互引导 — 基于角色模板 + 场景归属
参考: zidu-novel-studio 的 character-template.md + character-building.md
"""
from typing import Optional
from app.worldbuilding.state import SessionState


class CharacterDesignAgent:
    """
    交互式角色设计
    
    用法:
      agent = CharacterDesignAgent(state)
      msg = agent.start()
      msg = agent.handle_input(text)
    """

    PERSONALITY_TYPES = [
        {"name": "英雄型", "desc": "勇敢、正义、利他 — 战胜外在威胁"},
        {"name": "成长型", "desc": "从弱小到强大 — 克服内在缺陷"},
        {"name": "反英雄型", "desc": "道德灰色、复杂 — 挑战传统道德"},
        {"name": "平凡型", "desc": "普通人卷入非凡事 — 读者代入感强"},
    ]

    FATAL_FLAWS = ["傲慢", "信任问题", "完美主义", "复仇心", "自卑", "冲动", "怯懦"]

    VILLAIN_MOTIVES = [
        "理想主义扭曲 — 为了大局必须牺牲",
        "过去创伤 — 世界伤害了我, 我要报复",
        "权力渴望 — 我配得上更多",
        "与主角相同目标, 不同方法",
    ]

    SUPPORTING_ROLES = [
        "导师型 — 指引主角, 传递信息",
        "盟友型 — 协助主角, 提供情感支持",
        "搞笑型 — 缓解紧张, 提供喜剧元素",
        "爱情型 — 制造浪漫线索",
        "叛徒型 — 制造背叛和转折",
    ]

    def __init__(self, state: SessionState):
        self.state = state
        self._step = "protagonist_intro"
        self.done = False

    def start(self) -> str:
        self.state.stage = "character_design"
        scenes = [s["name"] for s in self.state.scenes]
        scene_list = "\n".join(f"  {s}" for s in scenes)
        return (
            f"现在开始设计角色。已设计的场景:\n{scene_list}\n\n"
            f"第一步: 主角。\n"
            f"主角叫什么名字?"
        )

    def handle_input(self, text: str) -> str:
        if self._step == "protagonist_intro":
            return self._handle_protagonist_name(text)
        elif self._step == "protagonist_age":
            return self._handle_protagonist_age(text)
        elif self._step == "protagonist_personality":
            return self._handle_protagonist_personality(text)
        elif self._step == "protagonist_flaw":
            return self._handle_protagonist_flaw(text)
        elif self._step == "protagonist_desire":
            return self._handle_protagonist_desire(text)
        elif self._step == "protagonist_scene":
            return self._handle_protagonist_scene(text)
        elif self._step == "supporting_count":
            return self._handle_supporting_count(text)
        elif self._step == "supporting_input":
            return self._handle_supporting_input(text)
        elif self._step == "antagonist":
            return self._handle_antagonist(text)
        elif self._step == "antagonist_motive":
            return self._handle_antagonist_motive(text)
        elif self._step == "antagonist_scene":
            return self._handle_antagonist_scene(text)
        return "角色设计完成。"

    def _handle_protagonist_name(self, text: str) -> str:
        self.state.protagonist["name"] = text.strip() or "未命名"
        self._step = "protagonist_age"
        return (
            f"好的, 主角叫{self.state.protagonist['name']}。\n\n"
            f"年龄和职业/身份是什么?\n"
            f"(例: 16岁, 外门弟子 / 28岁, 京城捕头)"
        )

    def _handle_protagonist_age(self, text: str) -> str:
        self.state.protagonist["identity"] = text.strip() or "未知"
        self._step = "protagonist_personality"
        options = "\n".join(f"{i+1}. {t['name']} — {t['desc']}" for i, t in enumerate(self.PERSONALITY_TYPES))
        return (
            f"主角的性格类型?\n\n{options}\n\n"
            f"选择一项或自己描述。"
        )

    def _handle_protagonist_personality(self, text: str) -> str:
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(self.PERSONALITY_TYPES):
                self.state.protagonist["personality"] = self.PERSONALITY_TYPES[idx]["name"]
        else:
            self.state.protagonist["personality"] = text.strip() or "成长型"
        
        self._step = "protagonist_flaw"
        flaws = ", ".join(self.FATAL_FLAWS)
        return (
            f"主角的致命缺陷是什么?\n{flaws}\n(或自定义)"
        )

    def _handle_protagonist_flaw(self, text: str) -> str:
        self.state.protagonist["fatal_flaw"] = text.strip() or "无"
        self._step = "protagonist_desire"
        return (
            f"主角的核心欲望和深层动机?\n"
            f"(例: 为家人复仇 / 证明自己的价值 / 寻找失踪的父母)"
        )

    def _handle_protagonist_desire(self, text: str) -> str:
        self.state.protagonist["desire"] = text.strip() or "待定"
        self._step = "protagonist_scene"
        scenes = "\n".join(f"{i+1}. {s['name']}" for i, s in enumerate(self.state.scenes))
        return (
            f"主角的初始场景是哪个?\n{scenes}"
        )

    def _handle_protagonist_scene(self, text: str) -> str:
        scenes = self.state.scenes
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(scenes):
                self.state.protagonist["scene"] = scenes[idx]["name"]
        else:
            self.state.protagonist["scene"] = text.strip() or scenes[0]["name"]
        
        self._step = "supporting_count"
        return (
            f"好的, 主角初始在{self.state.protagonist['scene']}。\n\n"
            f"第一卷需要几个配角? (建议 2-4 个)"
        )

    def _handle_supporting_count(self, text: str) -> str:
        n = int(text) if text.isdigit() else 2
        self._supporting_count = min(max(n, 1), 6)
        self._supporting_idx = 0
        self.state.supporting_chars = []
        self._step = "supporting_input"
        return self._ask_supporting()

    def _ask_supporting(self) -> str:
        if self._supporting_idx >= self._supporting_count:
            self._step = "antagonist"
            return self._ask_antagonist()
        
        roles = "\n".join(f"{i+1}. {r}" for i, r in enumerate(self.SUPPORTING_ROLES))
        return (
            f"配角 {self._supporting_idx+1}/{self._supporting_count}:\n"
            f"名字和角色类型?\n{roles}\n\n"
            f"格式: 名字, 类型 (例: 老陈, 导师型)"
        )

    def _handle_supporting_input(self, text: str) -> str:
        parts = text.split(",")
        name = parts[0].strip() if parts else f"配角{self._supporting_idx+1}"
        role_type = parts[1].strip() if len(parts) > 1 else "盟友型"
        
        self.state.supporting_chars.append({
            "name": name,
            "role": role_type,
            "scene_role": "supporting",
            "weight": "light",
            "scene": self.state.scenes[self._supporting_idx % len(self.state.scenes)]["name"]
        })
        self._supporting_idx += 1
        return self._ask_supporting()

    def _ask_antagonist(self) -> str:
        self._step = "antagonist"
        return (
            f"本卷的反派是谁?\n"
            f"(可以是具体的敌人, 也可以是对立势力, 或直接回车跳过)"
        )

    def _handle_antagonist(self, text: str) -> str:
        if not text.strip():
            self.done = True
            return self._finalize()
        
        self.state.antagonist["name"] = text.strip()
        self.state.antagonist["scene_role"] = "antagonist"
        self.state.antagonist["weight"] = "full"
        self._step = "antagonist_motive"
        motives = "\n".join(f"{i+1}. {m}" for i, m in enumerate(self.VILLAIN_MOTIVES))
        return (
            f"{self.state.antagonist['name']}的动机?\n{motives}\n\n"
            f"选择一项或自定义。"
        )

    def _handle_antagonist_motive(self, text: str) -> str:
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(self.VILLAIN_MOTIVES):
                self.state.antagonist["motive"] = self.VILLAIN_MOTIVES[idx]
        else:
            self.state.antagonist["motive"] = text.strip() or "待定"
        self._step = "antagonist_scene"
        scenes = "\n".join(f"{i+1}. {s['name']}" for i, s in enumerate(self.state.scenes))
        return (
            f"反派在哪个场景活动?\n{scenes}"
        )

    def _handle_antagonist_scene(self, text: str) -> str:
        scenes = self.state.scenes
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(scenes):
                self.state.antagonist["scene"] = scenes[idx]["name"]
        else:
            self.state.antagonist["scene"] = text.strip() or scenes[0]["name"]
        
        self.done = True
        return self._finalize()

    def _finalize(self) -> str:
        self.state.stage = "done"
        lines = [f"✅ 角色设计完成!\n"]
        p = self.state.protagonist
        lines.append(f"主角: {p.get('name','?')} | {p.get('identity','')} | {p.get('personality','')}型")
        lines.append(f"  缺陷: {p.get('fatal_flaw','')} | 欲望: {p.get('desire','')}")
        lines.append(f"  初始场景: {p.get('scene','')}")
        lines.append("")
        if self.state.supporting_chars:
            lines.append("配角:")
            for c in self.state.supporting_chars:
                lines.append(f"  {c['name']} ({c['role']}) — {c['scene']}")
        if self.state.antagonist.get("name"):
            a = self.state.antagonist
            lines.append(f"\n反派: {a['name']} | 动机: {a.get('motive','')} | 场景: {a.get('scene','')}")
        lines.append("")
        lines.append("所有设计完成, 可以开始故事规划了!")
        return "\n".join(lines)
