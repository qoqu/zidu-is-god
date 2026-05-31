"""
Direction Setting — 30 秒对话定本卷方向
不写卷纲章纲, 只设定引导参数, 让 Engine 自己跑
"""
from typing import Optional
from app.worldbuilding.state import SessionState
from app.plot.director import PlotDirector


class DirectionAgent:
    """
    方向设定 — 用户说一句方向, AI 配置 PlotDirector 参数
    """

    def __init__(self, state: SessionState):
        self.state = state
        self.done = False

    def start(self) -> str:
        scenes = [s["name"] for s in self.state.scenes]
        scene_list = "\n".join(f"  • {s}" for s in scenes)
        p_name = self.state.protagonist.get("name", "主角")

        return (
            f"好的。已有世界、场景和角色:\n{scene_list}\n\n"
            f"{p_name}在这个卷里想做什么?\n\n"
            f"一句话告诉我就行, 例如:\n"
            f"  • \"主角要加入宗门\"\n"
            f"  • \"主角查案, 发现背后有更大阴谋\"\n"
            f"  • \"主角和反派在比武场上一决胜负\"\n"
            f"  • \"主角在食堂被人羞辱, 开始反击\"\n\n"
            f"也可以更具体:\n"
            f"  • \"入门试炼, 有竞争者使绊子, 最后靠实力过关\""
        )

    def handle_input(self, text: str) -> str:
        if not text.strip():
            self.done = True
            return self._finalize("未指定方向")

        # 解析用户输入的方向, 配置 PlotDirector 参数
        direction = text.strip()
        params = self._parse_direction(direction)

        self.done = True
        self.state.stage = "direction_done"
        return self._finalize(direction, params)

    def _parse_direction(self, text: str) -> dict:
        """从自然语言解析方向参数"""
        text_lower = text.lower()
        params = {}

        # 张力曲线类型
        if any(w in text_lower for w in ["试炼", "比武", "考试", "选拔"]):
            params["tension_curve"] = "climax"  # 逐步升高到高潮
            params["catalyst_type"] = "competition"  # 竞争催化剂
            params["chapter_count"] = 6
        elif any(w in text_lower for w in ["查案", "调查", "秘密", "阴谋"]):
            params["tension_curve"] = "mystery"  # 波折起伏
            params["catalyst_type"] = "revelation"  # 秘密揭示
            params["chapter_count"] = 8
        elif any(w in text_lower for w in ["战斗", "复仇", "对决"]):
            params["tension_curve"] = "action"  # 持续高位
            params["catalyst_type"] = "conflict"  # 冲突升级
            params["chapter_count"] = 5
        elif any(w in text_lower for w in ["成长", "修炼", "变强"]):
            params["tension_curve"] = "growth"  # 波浪式上升
            params["catalyst_type"] = "training"  # 成长契机
            params["chapter_count"] = 8
        elif any(w in text_lower for w in ["日常", "学院", "校园"]):
            params["tension_curve"] = "slice_of_life"  # 低平偶有波澜
            params["catalyst_type"] = "daily"  # 日常事件
            params["chapter_count"] = 6
        else:
            # 默认: 正常推进
            params["tension_curve"] = "normal"
            params["catalyst_type"] = "general"
            params["chapter_count"] = 6

        # 检查是否需要 competitor
        if any(w in text_lower for w in ["竞争者", "对手", "陷害", "使绊子"]):
            params["need_competitor"] = True

        # 提取章节数
        import re
        nums = re.findall(r'\d+', text)
        for n in nums:
            if 3 <= int(n) <= 20:
                params["chapter_count"] = int(n)
                break

        return params

    def _finalize(self, direction: str, params: dict = None) -> str:
        self.state.direction_text = direction
        if params:
            self.state.direction_params = params
        if not params:
            return f"好的, 方向「{direction}」。开始模拟。"

        curve_names = {
            "climax": "逐步升温→高潮爆发",
            "mystery": "波折起伏→真相揭露",
            "action": "持续高位, 快节奏",
            "growth": "波浪式上升, 稳中有进",
            "slice_of_life": "低平偶有波澜, 轻松向",
            "normal": "正常推进",
        }

        lines = [f"好的, 方向「{direction}」配置完成:\n"]
        lines.append(f"  • 节奏: {curve_names.get(params.get('tension_curve', ''), '正常')}")
        lines.append(f"  • 催化剂: {params.get('catalyst_type', '通用')}")
        lines.append(f"  • 预计章节: {params.get('chapter_count', 6)} 章")
        if params.get("need_competitor"):
            lines.append(f"  • 需要竞争者角色 (请在角色中确认)")

        lines.append(f"\n可以开始模拟了!")
        return "\n".join(lines)

    def get_director_config(self) -> dict:
        """获取 PlotDirector 配置参数"""
        return {
            "target_chapters": 6,
            "tension_profile": "normal",
            "catalyst_frequency": 2,
        }
