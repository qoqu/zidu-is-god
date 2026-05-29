# Novel World Engine — 创世日记引擎

让角色在我们创造的世界中书写自己的故事。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

```bash
cp .env.example .env
# 编辑 .env, 填入你的 LLM API Key
```

支持任意兼容 OpenAI SDK 格式的 API（硅基流动、阿里百炼、DeepSeek、OpenAI 等）。

## 快速开始

## v0.2.0 新特性

| 特性 | 说明 |
|------|------|
| **通用时间轴** | 记录每章状态/事件/角色, 支持任意时间点分歧 |
| **小说解析器** | 从一本小说 txt 中提取世界观/角色/时间轴 |
| **同人分歧** | 在时间轴上任选一点插入新角色 → 剧情偏离原著 |
| **状态持久化** | 保存/加载故事进度, 支持续写 |
| **流式输出** | Narrator 逐段生成 + SSE API |
| **错误处理** | 7 种中文友好提示 (API Key/模型/超时等) |
| **Web 可视化** | 张力曲线图、质量进度条 |
| **单元测试** | 15 项核心测试 |

## 快速开始

### CLI 方式

```bash
# 使用内置演示 (需要先配置 .env)
python -m app.cli demo

# 从文件读入世界观和角色
python -m app.cli run --world examples/world.txt --chars examples/chars.txt --chapters 3

# 交互式输入
python -m app.cli interactive

# 指定输出文件
python -m app.cli run --world world.txt --chars chars.txt --chapters 3 --output story.txt
```

### Web UI 方式

```bash
# 启动 Web 服务
novel-world-engine-server

# 然后在浏览器中打开 http://localhost:5001
```

界面中可以直接编辑世界观和角色设定，调整章节数，点击开始模拟运行。

---

### Python API 方式

```python
from app.core import simulate

# 一行调用, 返回结构化结果
result = simulate(
    world_description="""
    一个灵气复苏的武道学院世界。
    地点: 演武场、宿舍区、藏书阁
    修炼体系: 炼体→凝气→筑基
    """,
    character_descriptions=[
        "林北辰, 16岁, 外门弟子, 沉默寡言但意志坚定",
        "赵无极, 18岁, 内门弟子, 嚣张跋扈",
        "苏晚晴, 17岁, 内门天才, 表面高傲内心善良",
    ],
    chapters=3,
)

for chapter in result["chapters"]:
    print(f"第{chapter['number']}章 ({chapter['word_count']}字)")
    print(chapter["text"][:200])
```

### 分步调用

```python
from app.world.builder import WorldBuilder
from app.characters.generator import CharacterGenerator
from app.engine.simulation import Engine
from app.plot.director import PlotDirector
from app.narrator.narrator import Narrator
from app.narrator.quality import QualityChecker
from app.world.engine import WorldEngine
from app.llm.client import LLMClient

# 1. 初始化 LLM
llm = LLMClient()

# 2. 构建世界
world = WorldBuilder(llm).build("""
  一个灵气复苏的武道学院世界。
  地点: 演武场、宿舍区、藏书阁
""")

# 3. 生成角色
chars = CharacterGenerator(llm).generate_batch([
    "林北辰, 16岁, 外门弟子, 沉默寡言但意志坚定",
    "赵无极, 18岁, 内门弟子, 嚣张跋扈",
])
for c in chars:
    c.current_location = list(world.locations.keys())[0]
char_name_map = {c.id: c.name for c in chars}

# 4. 启动世界引擎 (天气/谣言/事件/势力自动演化)
world.world_engine = WorldEngine(world)

# 5. 初始化引擎和导演
engine = Engine(world, chars, llm)
director = PlotDirector(world, chars)

# 6. 逐章模拟
narrator = Narrator(llm)
quality = QualityChecker()

for chap in range(1, 4):
    blueprint = director.plan_chapter(chap)
    beat_logs = engine.run_chapter(director, blueprint)
    chapter_text = narrator.narrate_chapter(beat_logs, char_name_map=char_name_map)
    qr = quality.check(chapter_text, chapter_num=chap)
    print(f"第{chap}章: {qr['total']}/80 分")
```

## 架构

```
六层架构:

1. 世界模型        — 地点/势力/时间线/规则 + 天气/谣言/随机事件/毁灭威胁
2. 角色模型        — 人格/动机/情绪/记忆/执念/伤势/需求/六维影响力/资源账本
3. 叙事引擎        — Beat 循环: 感知→LLM决策→冲突解析→状态更新
4. 剧情导演        — 张力监控/催化剂/伏笔/风险备忘/情绪曲线
5. 叙事生成        — 事件序列→小说文本, 跨 Beat 连贯
6. 质量门禁        — 80分八维度质量检查
```

详见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 核心概念

| 概念 | 说明 |
|------|------|
| **Beat** | 叙事的最小原子单元 (~200-500字) |
| **执念** | 角色永远忘不掉的东西, 永不衰减 |
| **六维影响力** | 财富/权谋/武力/学识/声望/超凡, 各维度独立 |
| **世界行动者** | 独立于主角的顶层势力, 自动演化 |
| **因果链** | 每个事件记录 because→therefore |
| **资源账本** | 物品/装备/道具的生命周期管理 |

## 项目结构

```
novel-world-engine/
├── backend/
│   └── app/
│       ├── cli.py            # CLI 入口
│       ├── core.py           # 一键调用接口
│       ├── world/            # 世界模型 + 天气/谣言/事件/威胁/行动者
│       ├── characters/       # 角色模型 + 记忆/执念/资源账本
│       ├── engine/           # 叙事引擎 + 多线并行/环境交互
│       ├── plot/             # 剧情导演 + 张力/伏笔/催化剂
│       ├── narrator/         # 叙事生成 + 质量检查
│       └── llm/              # LLM 客户端
├── examples/                 # 示例输入文件
└── LICENSE                   # AGPL-3.0
```

## 许可证

AGPL-3.0。详见 [LICENSE](LICENSE)。

商用授权请联系作者。
