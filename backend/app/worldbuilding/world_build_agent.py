"""WorldBuild 交互引导 v2 — 按子类型定制选项, 自动结束"""
from typing import Optional
from app.worldbuilding.state import SessionState, WORLD_TYPE_CATALOG
from app.llm.client import LLMClient


# 按子类型定制的力量体系选项
POWER_OPTIONS = {
    # 仙侠分支
    "古典仙侠": ["炼精化气->炼气化神->炼神还虚->大乘", "练气->筑基->金丹->元婴->化神", "剑修/体修/符修/阵修"],
    "修真文明": ["练气->筑基->金丹->元婴->化神", "剑修/体修/符修/阵修", "炼精化气->炼气化神->炼神还虚"],
    "现代修真": ["异能觉醒->等级晋升", "传统修炼体系融入现代", "古武+科技结合"],
    "神话修真": ["血脉觉醒->返祖->成神", "信仰成神/功德成神/以力证道", "先天神灵->后天修炼"],
    # 武侠分支
    "国术无双": ["气血->明劲->暗劲->化劲->抱丹", "外家横练(铁布衫/金刚腿)", "内家拳法(太极/形意/八卦)"],
    "传统武侠": ["内力->先天->宗师->大宗师", "外功招式(剑法/刀法/拳法)", "内功心法+外功招式并行"],
    "武侠同人": ["原著的武功体系", "自创武学", "跨作品融合"],
    # 玄幻分支
    "东方玄幻": ["武魂/神格觉醒", "血脉进化", "法则领悟"],
    "异世大陆": ["魔法+斗气", "职业体系(战士/法师/弓箭手)", "神格+信仰"],
    "王朝争霸": ["权谋+兵法", "个人武力+军队指挥", "气运争夺"],
    # 奇幻分支
    "西方奇幻": ["元素魔法+斗气", "神术+信仰", "奥术+炼金"],
    "剑与魔法": ["战士+法师经典组合", "魔武双修", "法术+附魔武器"],
    "领主种田": ["内政+外交", "领地建设+科技攀爬", "招募英雄+组建军队"],
    "史诗奇幻": ["多种族(精灵/矮人/龙)", "古神+凡人的力量体系", "命运/预言驱动"],
    # 都市分支
    "都市异能": ["超能力觉醒(念力/时间/空间)", "古武传承隐居都市", "科技造物赋予能力"],
    "豪门世家": ["商业手腕", "家族产业经营", "人际关系+权谋"],
    "娱乐明星": ["唱跳演全能", "综艺/影视/音乐三栖", "资本运作+流量"],
    "商战职场": ["商业谈判+并购", "职场晋升+办公室政治", "创业+融资"],
    "都市生活": ["无特殊能力", "职业技能+人脉积累", "投资理财"],
    # 科幻分支
    "星际文明": ["曲速引擎+星际航行", "机甲+太空战", "外星科技+文明等级"],
    "时空穿梭": ["时间操控+因果律", "平行宇宙穿越", "时间循环"],
    "超级科技": ["纳米技术", "基因改造+强化", "AI+脑机接口"],
    "赛博朋克": ["义体改造", "黑客+网络空间", "巨型企业+地下社会"],
    "古武机甲": ["内力+机甲驾驶", "武者+科技装备", "精神链接机甲"],
    # 末世分支
    "丧尸爆发": ["异能觉醒", "生存技能+丧尸进化", "基地建设"],
    "废土生存": ["辐射变异", "科技残骸+复原", "部落+拾荒者"],
    "天灾降临": ["元素异能(冰/火/雷)", "灾害预警+应对", "幸存者联盟"],
    # 历史/军事分支
    "历史穿越": ["现代知识降维打击", "科技攀爬+工业革命", "权谋+改革"],
    "架空历史": ["自创朝代+世界线", "古代官职+军制改革", "文化+科技并行"],
    "军事战争": ["现代武器+战术", "特种作战+情报战", "海陆空协同"],
    "军事谍战": ["情报获取+反侦察", "潜伏+双面间谍", "密码破译"],
    # 悬疑分支
    "侦探推理": ["逻辑推理+证据链", "法医+犯罪现场", "心理侧写+审讯"],
    "灵异鬼怪": ["阴阳眼+通灵", "道术+符咒", "驱魔+封印"],
    "规则怪谈": ["特定规则+生存条件", "异常物品+收容", "认知污染+模因"],
    # 游戏分支
    "游戏异界": ["等级+技能+装备", "副本+BOSS+掉落", "职业+天赋树"],
    "电子竞技": ["操作+反应速度", "团队配合+BP策略", "战术+心理战"],
    "虚拟网游": ["全息沉浸", "自由职业+生活技能", "公会战+国战"],
    # 言情分支
    "古代言情": ["女红+才艺+心计", "家族联姻+宫斗", "医术/商业/从军"],
    "现代言情": ["职场技能+社交", "才艺+个人魅力", "商业+家族事业"],
    "玄幻言情": ["魔法/修炼天赋", "血脉+特殊能力", "智慧+谋略"],
    # 轻小说
    "异界召唤": ["异世界技能面板", "召唤兽+契约", "异界知识+现代思维"],
    "日常冒险": ["普通人的特长", "小团队配合", "日常+突发事件"],
}

# 按类型定制的核心冲突选项
CONFLICT_OPTIONS = {
    "武侠": ["江湖仇杀", "门派之争", "正邪对立", "国术vs洋枪"],
    "仙侠": ["正邪对立", "资源争夺", "阶级压迫", "上古秘密"],
    "玄幻": ["家族复仇", "万族争霸", "天道崩塌", "穿越者效应"],
    "都市": ["商战博弈", "异能冲突", "家族继承", "阶层跨越"],
    "科幻": ["星际vs地球", "AI vs 人类", "基因伦理", "末世生存"],
    "历史": ["王朝更替", "变法vs守旧", "外敌入侵", "权力之争"],
    "悬疑": ["连环案件", "超自然调查", "跨时空谜题", "规则怪谈"],
    "末世": ["丧尸围城", "资源匮乏", "人性选择", "重建vs弱肉强食"],
    "古代言情": ["宫闱权斗", "联姻vs自由恋爱", "嫡庶之争", "穿越女自保"],
    "现代言情": ["阶级差异的爱情", "事业vs感情", "家族反对", "误会错过"],
}


class WorldBuildAgent:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.state = SessionState()
        self.done = False

    def start(self) -> str:
        self.state.stage = "world_type"
        types = self.state.get_type_options()
        return "请选择世界观类型:\n\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(types)) + "\n\n(输入数字或名称)"

    def handle_input(self, text: str) -> str:
        h = getattr(self, f"_handle_{self.state.stage}", None)
        return h(text) if h else ""

    def _handle_world_type(self, text: str) -> str:
        types = self.state.get_type_options()
        chosen = self._match(text, types)
        if not chosen: return "请选择:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(types))
        self.state.world_type = chosen
        self.state.stage = "world_subtype"
        subs = self.state.get_subtype_options()
        if subs: return f"{chosen}。具体方向?\n\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(subs))
        return self._ask_power()

    def _handle_world_subtype(self, text: str) -> str:
        subs = self.state.get_subtype_options()
        chosen = self._match(text, subs)
        self.state.world_subtype = chosen or (subs[0] if subs else "")
        return self._ask_power()

    def _ask_power(self) -> str:
        self.state.stage = "world_power"
        sub = self.state.world_subtype
        opts = POWER_OPTIONS.get(sub, self.state.get_power_options())
        if not opts: opts = ["自定义"]
        return "力量体系?\n\n" + "\n".join(f"{i+1}. {o}" for i, o in enumerate(opts)) + "\n\n(选数字或自己描述)"

    def _handle_world_power(self, text: str) -> str:
        opts = POWER_OPTIONS.get(self.state.world_subtype, self.state.get_power_options())
        chosen = self._match(text, opts)
        self.state.power_system = chosen or (text if len(text) > 2 else (opts[0] if opts else ""))
        self.state.stage = "world_conflict"
        ct = self.state.world_type
        opts2 = CONFLICT_OPTIONS.get(ct, ["自定义"])
        return "核心冲突?\n\n" + "\n".join(f"{i+1}. {o}" for i, o in enumerate(opts2)) + "\n\n(选数字或自己描述)"

    def _handle_world_conflict(self, text: str) -> str:
        opts = CONFLICT_OPTIONS.get(self.state.world_type, ["自定义"])
        chosen = self._match(text, opts)
        self.state.core_conflict = chosen or (text if len(text) > 2 else (opts[0] if opts else ""))
        self.state.stage = "world_name"
        return "这个世界叫什么名字?"

    def _handle_world_name(self, text: str) -> str:
        self.state.world_name = text.strip() or f"未命名{self.state.world_type}世界"
        self.state.world_summary = self._auto_summary()
        self.done = True
        self.state.stage = "done"
        s = self.state
        return f"构建完成!\n\n世界: {s.world_name}\n类型: {s.world_type}-{s.world_subtype}\n力量: {s.power_system}\n冲突: {s.core_conflict}\n\n进入场景设计阶段。"

    def _match(self, text: str, options: list) -> str:
        text = text.strip()
        if not text or not options: return ""
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(options): return options[idx]
        for o in options:
            if text in o or o in text: return o
        return ""

    def _auto_summary(self) -> str:
        s = self.state
        p = [f"这是一个{s.world_type}世界"]
        if s.world_subtype: p.append(f"属于{s.world_subtype}类型")
        if s.power_system: p.append(f"力量体系采用{s.power_system}")
        if s.core_conflict: p.append(f"核心冲突围绕{s.core_conflict}展开")
        return "；".join(p)
