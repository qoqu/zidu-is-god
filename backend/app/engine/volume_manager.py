"""
多卷循环 — 前瞻伏笔 + Vol 自动过渡
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VolumeState:
    """一卷的完整状态"""
    number: int
    title: str = ""
    scenes: list = field(default_factory=list)
    characters: list = field(default_factory=list)
    chapter_count: int = 0
    generated_chapters: list = field(default_factory=list)
    direction: str = ""
    direction_params: dict = field(default_factory=dict)
    status: str = "pending"  # pending / active / completed


@dataclass
class CrossVolumeHook:
    """跨卷伏笔 — 在 Vol N 种下, 在 Vol M 回收"""
    id: str
    planted_in: int       # 伏笔种下的卷号
    payoff_in: int        # 伏笔回收的卷号
    content: str          # 伏笔内容
    status: str = "pending"  # pending / active / paid_off
    planted_chapter: int = 0
    payoff_chapter: int = 0


class VolumeManager:
    """
    卷管理器 — 管理多卷的生命周期和跨卷伏笔
    """

    def __init__(self):
        self.volumes: list[VolumeState] = []
        self.current_vol: int = 0
        self.hooks: list[CrossVolumeHook] = []
        self._hook_counter = 0

    def start_volume(self, title: str = "", chapter_count: int = 6) -> VolumeState:
        """开始一卷"""
        vol = VolumeState(
            number=len(self.volumes) + 1,
            title=title or f"第{len(self.volumes)+1}卷",
            chapter_count=chapter_count,
            status="active",
        )
        self.volumes.append(vol)
        self.current_vol = vol.number
        return vol

    def plant_hook(self, content: str, payoff_in_vol: int,
                   planted_chapter: int = 0) -> CrossVolumeHook:
        """种下跨卷伏笔"""
        self._hook_counter += 1
        hook = CrossVolumeHook(
            id=f"cvh_{self._hook_counter:04d}",
            planted_in=self.current_vol,
            payoff_in=payoff_in_vol,
            content=content,
            status="pending",
            planted_chapter=planted_chapter,
        )
        self.hooks.append(hook)
        return hook

    def check_payoff(self, vol_number: int) -> list[CrossVolumeHook]:
        """检查本卷应该回收哪些伏笔"""
        due = [h for h in self.hooks
               if h.payoff_in == vol_number and h.status == "pending"]
        for h in due:
            h.status = "active"
        return due

    def is_volume_ending(self, current_chapter: int) -> bool:
        """检查当前卷是否接近尾声 (最后20%)"""
        vol = self.get_current()
        if not vol or vol.chapter_count <= 0:
            return False
        progress = current_chapter / vol.chapter_count
        return progress >= 0.8

    def get_current(self) -> Optional[VolumeState]:
        if 0 < self.current_vol <= len(self.volumes):
            return self.volumes[self.current_vol - 1]
        return None

    def next_volume_text(self, vol: VolumeState) -> str:
        """生成卷过渡提示词 (给 Narrator)"""
        pending_hooks = [h for h in self.hooks if h.status != "paid_off"]
        hook_lines = "\n".join(f"  - {h.content} (埋于第{h.planted_in}卷)" for h in pending_hooks)
        parts = [f"第{vol.number}卷: {vol.title}"]
        if vol.generated_chapters:
            parts.append(f"共{len(vol.generated_chapters)}章, {sum(len(c.get('text','')) for c in vol.generated_chapters)}字")
        if hook_lines:
            parts.append(f"未回收伏笔:\n{hook_lines}")
        return "\n".join(parts)

    def summary(self) -> str:
        lines = [f"共 {len(self.volumes)} 卷"]
        for v in self.volumes:
            hooks = sum(1 for h in self.hooks if h.planted_in == v.number)
            payoffs = sum(1 for h in self.hooks if h.payoff_in == v.number)
            lines.append(f"  第{v.number}卷: {v.title} ({len(v.generated_chapters)}章)")
            if hooks or payoffs:
                lines.append(f"    伏笔: {hooks}个种下, {payoffs}个回收")
        return "\n".join(lines)
