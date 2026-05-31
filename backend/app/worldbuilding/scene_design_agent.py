"""Scene Design v3 — 只设计大场景名, 舞台由模拟自动生成"""
from app.worldbuilding.state import SessionState


class SceneDesignAgent:
    def __init__(self, state: SessionState):
        self.state = state
        self._step = "count"
        self.done = False
        self._count = 2
        self._idx = 0

    def start(self) -> str:
        self.state.stage = "scene_design"
        return (
            "第一卷的故事发生在几个大区域?\n\n"
            "只告诉我区域名就行, 每个区域内的具体舞台\n"
            "会在角色行动时自动生成。\n\n"
            f"基于{self.state.world_type}世界观, 建议 1-3 个。\n"
            "例如: 青云城 / 龙脊山脉 / 玄天宗"
        )

    def handle_input(self, text: str) -> str:
        if self._step == "count":
            if text.isdigit():
                n = int(text)
                if 1 <= n <= 5: self._count = n
            self._idx = 0
            self.state.scenes = []
            self._step = "name"
            return f"大区域 1/{self._count}: 叫什么?"

        if self._step == "name":
            name = text.strip() or f"区域{self._idx+1}"
            self.state.scenes.append({"id": f"s{self._idx+1}", "name": name, "stages": [], "connections": []})
            self._idx += 1
            if self._idx < self._count:
                return f"大区域 {self._idx+1}/{self._count}: 叫什么?"
            self._step = "done"
            return self._finish()

    def _finish(self) -> str:
        self.done = True
        self.state.stage = "scene_done"
        names = ", ".join(s["name"] for s in self.state.scenes)
        self.state.scene_map_text = f"第一卷: {names}"
        return (
            f"场景设计完成: {self.state.scene_map_text}\n\n"
            f"进入角色设计阶段。"
        )
