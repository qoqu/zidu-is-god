"""
Scene Design 交互引导 — 基于世界类型设计第一卷场景地图
"""
from typing import Optional
from app.worldbuilding.state import SessionState, get_scene_templates


class SceneDesignAgent:
    """
    交互式场景设计
    
    用法:
      agent = SceneDesignAgent(state)
      msg = agent.start()   # 返回引导消息
      msg = agent.handle_input(text)  # 反复直到 done
    """

    def __init__(self, state: SessionState):
        self.state = state
        self._step = "size"  # size → names → details → connections → done
        self.done = False
        self._scene_count = 3
        self._current_scene_idx = 0

    def start(self) -> str:
        self.state.stage = "scene_design"
        templates = get_scene_templates(self.state.world_type)
        names = ", ".join(t["name"] for t in templates[:5])
        return (
            f"好的! 基于{self.state.world_type}世界观, 我来推荐第一卷的场景。\n\n"
            f"常用场景有:\n{names}\n\n"
            f"第一卷需要设计几个场景? (建议 3-6 个)"
        )

    def handle_input(self, text: str) -> str:
        if self._step == "size":
            return self._handle_size(text)
        elif self._step == "names":
            return self._handle_names(text)
        elif self._step == "details":
            return self._handle_details(text)
        elif self._step == "connections":
            return self._handle_connections(text)
        return "场景设计完成。"

    def _handle_size(self, text: str) -> str:
        if text.isdigit():
            n = int(text)
            if 1 <= n <= 10:
                self._scene_count = n
        self._step = "names"
        templates = get_scene_templates(self.state.world_type)
        names = "\n".join(f"{i+1}. {t['name']} ({t['vibe']})" for i, t in enumerate(templates))
        return (
            f"好的, {self._scene_count}个场景。\n\n"
            f"以下是根据世界类型推荐的标准场景:\n{names}\n\n"
            f"请输入场景名称, 每行一个:\n"
            f"(可以选用推荐的, 也可以自己起名)"
        )

    def _handle_names(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # 如果用户输入的数量不够, 用模板补齐
        templates = get_scene_templates(self.state.world_type)
        for i, t in enumerate(templates):
            if len(lines) >= self._scene_count:
                break
            if t["name"] not in "\n".join(lines):
                lines.append(t["name"])

        self.state.scenes = [{"id": f"scene_{i+1}", "name": n, "vibe": "普通",
                              "npcs": [], "events": [], "connections": []}
                             for i, n in enumerate(lines[:self._scene_count])]
        self._current_scene_idx = 0
        self._step = "details"
        return self._ask_scene_detail()

    def _ask_scene_detail(self) -> str:
        if self._current_scene_idx >= len(self.state.scenes):
            self._step = "connections"
            return self._ask_connections()
        
        s = self.state.scenes[self._current_scene_idx]
        templates = get_scene_templates(self.state.world_type)
        template = next((t for t in templates if t["name"] in s["name"]), {})
        vibe_opts = ", ".join(t["vibe"] for t in templates[:5]) + ", 自定义"
        
        return (
            f"场景 {self._current_scene_idx+1}: {s['name']}\n"
            f"  氛围: {template.get('vibe', '普通')}"
            f"  典型NPC: {', '.join(template.get('typical_npcs', ['待定']))}"
            f"  可能事件: {', '.join(template.get('events', ['待定']))}"
            f"\n\n按回车确认, 或输入修改意见。"
        )

    def _handle_details(self, text: str) -> str:
        s = self.state.scenes[self._current_scene_idx]
        if text.strip():
            # 用户修改了
            s["description"] = text.strip()
        self._current_scene_idx += 1
        return self._ask_scene_detail()

    def _ask_connections(self) -> str:
        scenes = self.state.scenes
        names = " ↔ ".join(s["name"] for s in scenes)
        return (
            f"场景之间的关系:\n{names}\n\n"
            f"哪些场景是相邻的? (输入格式: 场景1-场景2, 场景2-场景3)\n"
            f"或直接回车跳过, 默认线性连接。"
        )

    def _handle_connections(self, text: str) -> str:
        scenes = self.state.scenes
        if text.strip():
            pairs = [p.strip() for p in text.split(",")]
            for pair in pairs:
                if "-" in pair:
                    a, b = pair.split("-")
                    for s in scenes:
                        if s["name"] == a.strip():
                            s["connections"].append(b.strip())
        else:
            # 默认线性连接
            for i in range(len(scenes) - 1):
                scenes[i]["connections"].append(scenes[i+1]["name"])

        self.done = True
        self.state.stage = "scene_done"
        
        # 生成场景地图文本
        map_lines = [f"第一卷场景地图: {self.state.world_name}"]
        for s in scenes:
            conn = " ↔ ".join(s["connections"]) if s["connections"] else "无出口"
            d = s.get("description", "")
            map_lines.append(f"  {s['name']} ({d[:30] if d else ''}) → {conn}")
        
        self.state.scene_map_text = "\n".join(map_lines)
        
        return (
            f"✅ 场景设计完成!\n\n"
            f"{self.state.scene_map_text}\n\n"
            f"接下来可以进入角色设计阶段。"
        )
