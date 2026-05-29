# Novel World Engine — 架构设计文档

## 一、核心理念

基于多智能体模拟的小说叙事引擎。角色（Agent）在虚拟世界中自由交互，剧情导演（PlotDirector）把控宏观节奏，叙事者（Narrator）将事件序列转化为小说文本。

**不是**：传统 LLM 写小说工具  
**是**：角色自主决策 + 剧情涌现的模拟驱动叙事系统

## 二、核心设计原则

1. **涌现优先，导演掌舵** — Agent 自由决策产生细节，PlotDirector 只控大方向
2. **叙事层分离** — 模拟产生事件序列 → Narrator 转为小说文本，两层解耦
3. **张力驱动 + 情绪驱动** — 外部剧情由张力曲线控制，内部角色由情绪驱动
4. **每个角色都是自己故事的主角** — 配角也有高光时刻
5. **质量内建于引擎** — 质量规则硬编码强制执行
6. **伏笔/悬念是一等公民**

## 三、通用时间轴

时间轴是整个引擎的骨架 — 记录从故事开始到结束的每一个节点。

```
Timeline:
├─ nodes: [TimelineNode, ...]        # 每个节点对应一章
│   ├─ chapter / title / summary     # 章节信息
│   ├─ key_events                    # 关键事件
│   ├─ chars_present                 # 登场角色
│   ├─ world_snapshot                # 该章世界状态快照
│   └─ inserted_chars                # 分歧点插入的新角色
│
├─ insert_character(at_chapter)      # 在任意时间点插入角色 → 产生分歧
├─ diverged_branch()                 # 获取分歧后的分支
├─ original_branch()                 # 获取原著分支 (分歧点之前)
└─ context_for(chapter)              # 给 Engine 的前情提要
```

NovelParser 从一本小说 txt 中解析出 Timeline:
  小说 → 按章节分割 → LLM 提取每章事件/角色/状态 → 建 Timeline
  → 用户选分歧点 → 插入新角色 → Engine 模拟分歧分支

## 四、架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                    世界自主演化层 (WorldEngine)                │
│  每 Tick 自动运行, 不受角色是否在场影响:                       │
│  ├─ 天气系统 — 晴/雨/雪/灵气潮汐, 影响体力/修炼/情绪         │
│  ├─ 谣言系统 — 事件→传播→发酵 → 角色被动接收                 │
│  ├─ 世界行动者 — 独立于主角的顶层势力, 自主行动               │
│  ├─ 随机事件 — 天灾/奇遇/势力冲突/庆典                       │
│  ├─ 毁灭威胁 — 7 条并行末日线, 高影响力角色加速/减缓          │
│  └─ 时间推进 — 每 Tick = 1 天, 自动推进                      │
└──────────────────────────┬───────────────────────────────────┘
                           │ 世界事件注入
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   多线并行引擎 (ParallelEngine)                │
│  同时维护最多 5 条叙事线, 按 POV 调度切换:                    │
│  ├─ 高张力线优先获得 POV                                     │
│  ├─ 防饿死: 没有线被长期忽略                                 │
│  ├─ split: 角色分头行动 → 分裂为两条线                       │
│  └─ merge: 不同线角色相遇 → 自动合并                         │
└──────────────────────────┬───────────────────────────────────┘
                           │ 多线事件流
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  叙事引擎 (Engine) — 核心循环                 │
│  每 Beat 六步:                                               │
│  1. 场景组装 → 2. 角色感知 → 3. LLM 决策 →                  │
│  4. 行动解析 → 5. 世界更新 → 6. 事件记录                    │
│                                                              │
│  动空间: DIALOGUE / TRADE / EXPLORE / REST / HEAL /          │
│          CULTIVATE / OBSERVE / INNER / ACT / WAIT            │
│                                                              │
│  因果链: 每个事件记录 because→therefore                       │
│  记忆: 每 Beat 自动存入, 四层分级 (working/short/long/core)  │
│  执念: 角色永远忘不掉的东西, 永不衰减, 永远在 prompt 第一条   │
│                                                              │
│  Beat ~ 200-500 字, ~15 Beat = 1 章                           │
└──────────────────────┬───────────────────────────────────────┘
                       │ EventLog
                       ▼
┌──────────────────────────────────────────────────────────────┐
│             剧情导演 (PlotDirector)                           │
│  ├─ 章前: 设定张力曲线 + 催化剂池 + 风险备忘                  │
│  ├─ 每 Beat: 检查张力, 偏离时注入催化剂                       │
│  ├─ 章后: 更新伏笔池/情绪曲线/StatusCard/快照                  │
│  └─ 催化剂类型: 威胁升级/秘密揭示/新角色入场/反转/喘息        │
└──────────────────────┬───────────────────────────────────────┘
                       │ 事件序列
                       ▼
┌──────────────────────────────────────────────────────────────┐
│             叙事生成 (Narrator)                               │
│  ├─ 事件序列 → 小说段落 (每 Beat, 带前文上下文)               │
│  ├─ 多线交织: POV 线优先, 其他线用"=== 与此同时 ===" 切换    │
│  ├─ 角色名映射: 确保名字一致性                               │
│  └─ 输出后过质量检查                                          │
└──────────────────────┬───────────────────────────────────────┘
                       │ 章节文本
                       ▼
┌──────────────────────────────────────────────────────────────┐
│             质量门禁 (QualityChecker)                         │
│  80 分八维度评分: 开头/情节/人物/对话/悬念/节奏/展示/语言     │
│  ≥48/80 通过, <48 触发重写                                   │
└──────────────────────────────────────────────────────────────┘
```

## 四、角色模型

```
CharacterRole: primary / secondary / background

  primary (主要角色):
    - 每 Beat 完整 LLM 决策, 完整记忆/情绪/需求/影响力
    - 有自己的 POV 和高光时刻
    - 上限 3-5 个

  secondary (次要角色):
    - 仅跟 primary 同场时调 LLM, 精简感知
    - 保留关键事件记忆, 不做完整需求计算
    - PlotDirector 可根据活跃度升级为 primary
    - 上限 5-10 个

  background (背景角色):
    - 从不调 LLM, 由 Narrator 自动生成背景行为
    - 只记录位置/基本状态
    - 用于填充世界, 数量不限

Character:
├─ role: primary / secondary / background
├─ identity: 年龄/外貌/职业
├─ personality: 特质/说话风格/决策偏向
├─ motivation: 深层欲望/短期目标/恐惧
├─ growth_arc: 成长弧线 (起点→终点→进度)
├─ relationships: 非对称关系网络
│
├─ emotional_state: 两层情绪系统
│   ├─ mood (心境): 跨章延续, 每章变化一次
│   └─ emotion (即时): valence/arousal, 每 Beat 更新
│
├─ memory: 四层记忆系统
│   ├─ working: 最近 3~5 Beat, 完整细节
│   ├─ short_term: 本章内, 有情绪标记
│   ├─ long_term: 跨章, 按重要性排序, 会衰减
│   └─ core: 永不遗忘的关键事件
│
├─ obsessions: 执念列表
│   └─ 角色永远忘不掉的东西 (grudge/goal/trauma/love/secret)
│      永不衰减, 永远出现在决策 prompt 第一条
│
├─ stats: 数值系统
│   ├─ hp / stamina / wealth / reputation / cultivation
│   ├─ injuries: 部位/严重度/恢复
│   ├─ needs: 休息/安全/社交/成就 (驱动行为)
│   ├─ ledger: 资源账本 (物品/装备生命周期)
│   └─ influence: 六维影响力 (economic/political/military/
│                   knowledge/social/mystical)
│      每个维度独立, 影响世界的方式完全不同
│
├─ skills: 能力数值
└─ secrets: 隐藏信息
```

## 五、世界模型

```
WorldEngine (每 Tick = 1 天):
├─ WeatherSystem: 8 种天气 × 4 季权重
├─ RumorSystem: 传播/消散, 高权重角色谣言传得更快
├─ WorldActorSystem: 独立于主角的顶层势力
│   ├─ 由 WorldBuilder 根据世界观 LLM 生成
│   ├─ 也支持用户自定义配置
│   ├─ 按 tick_interval 自主行动
│   └─ 角色按影响力层级感知 (低层看不到顶层博弈)
├─ WorldEventGenerator: 天灾/奇遇/势力冲突/庆典
├─ WorldThreatSystem: 7 条并行末日线
│   ├─ 日常缓慢增长, 高影响力角色加速/减缓
│   ├─ 达到阈值触发灾难
│   └─ 一条触发可能级联触发其他
└─ Timeline: 自动推进, 每 Beat 半个时辰
```

## 六、数据流

```
世界观 + 角色设定
       │
WorldBuilder ──→ World + Actors
CharacterGenerator ──→ Characters (含记忆/执念/影响力)
       │
PlotDirector.plan_chapter() ──→ ChapterBlueprint
       │
Engine.run_chapter() (或 run_parallel_chapter)
  └─ 每 Beat: 时间推进 → 世界 Tick → 场景组装
     → Agent 感知(含天气/传闻/威胁/天下大事/记忆/执念)
     → LLM 决策(含需求/状态/情绪约束)
     → 冲突解析 + 因果链记录
     → 世界更新 + 记忆存储 + 情绪更新
       │
Narrator.narrate_chapter() ──→ 章节文本
       │
QualityChecker.check() ──→ 80 分评分报告
       │
SnapshotManager.save() ──→ 版本化快照 (支持回滚)
```

## 七、延伸模块 (v0.2.0+)

### 7.1 通用时间轴 (timeline.py)

每条叙事线都是一条时间轴，可以在任意节点插入新角色产生分歧。

```
Timeline:
├─ nodes: [TimelineNode]           # 每章一个节点
│   ├─ chapter / title / summary   # 章节信息
│   ├─ key_events                  # 关键事件
│   ├─ chars_present               # 登场角色
│   └─ inserted_chars              # 分歧点插入的新角色
│
├─ insert_character(at_chapter)    # → 产生分歧分支
├─ diverged_branch()               # 获取分歧分支
├─ original_branch()               # 获取原著分支
└─ context_for(chapter)            # 前情提要
```

### 7.5 WorldBuilder 扩展生成 (v0.6.0)

WorldBuilder 不仅能解析世界观, 还能根据世界观用 LLM 生成:

| 方法 | 生成内容 | 消费方 |
|------|---------|--------|
| build_actions() | 本世界特有的行为类型 | deliberation.py → 角色决策 prompt |
| build_weather() | 本世界的天气系统 | world/weather.py |
| build_threats() | 本世界的毁灭威胁 | world/threats.py |
| build_events() | 本世界的随机事件池 | world/events.py |

数据存入 `world.extras`, 子系统优先使用生成的数据, 没有则回退硬编码默认值。

### 7.6 可配置参数 (v0.6.0)

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| QUALITY_PASS | 48 | 质量门禁及格线 |
| TENSION_DANGER_WEIGHT | 0.3 | 张力计算:危险权重 |
| TENSION_EMOTION_WEIGHT | 0.25 | 张力计算:情绪权重 |
| PARALLEL_LINES | 5 | 最大并行线数 |
| BEATS_PER_POV | 3 | POV 切换频率 |
| BATCH_NARRATE | 3 | 叙事批次大小 |

### 7.2 小说解析器 (novel_parser.py)

从一本小说 txt 中提取结构化世界数据，用于同人创作。

```
输入: 小说 txt → 按章节分割 → LLM 提取
├─ 世界观 (地点/势力/规则)
├─ 角色群 (人格/动机/关系/执念)
└─ 时间轴 (每章事件/角色/状态)
→ 用户选分歧点 → 插入新角色 → Engine 模拟分歧
```

### 7.3 状态持久化 (persistence.py)

```
save_story(world, characters, chapters) → JSON 文件
load_story(filepath) → 恢复完整故事状态
list_saves(directory) → 列出所有存档
```

### 7.4 新 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/llm-config | GET/POST | Web 端配置 LLM |
| /api/llm-config/test | GET | 测试 LLM 连接 |
| /api/chapter/rewrite | POST | 单章重写 (导演反馈) |
| /api/simulate/wordcount | POST | 字数控制模拟 |
| /api/simulate/progress | POST | SSE 进度流 |
| /api/relations | POST | 关系网络数据 |
| /api/save | POST | 保存故事 |
| /api/load | POST | 加载故事 |
| /api/saves | GET | 存档列表 |

## 八、技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+ |
| LLM | OpenAI SDK (多供应商兼容) |
| 存储 | SQLite (MVP) / PostgreSQL+pgvector (生产) |
| 通信 | CLI / Python API / HTTP (可选) |
| 部署 | pip install / Docker (可选) |

## 八、目录结构

```
novel-world-engine/
├── backend/
│   ├── app/
│   │   ├── cli.py              # CLI 入口 (novel-world-engine 命令)
│   │   ├── core.py             # 一键 API (simulate())
│   │   ├── config.py           # 配置
│   │   ├── world/              # 世界模型
│   │   │   ├── schema.py       # 地点/势力/规则
│   │   │   ├── builder.py      # LLM 解析世界观
│   │   │   ├── engine.py       # 世界自主演化引擎
│   │   │   ├── weather.py      # 天气系统
│   │   │   ├── rumors.py       # 谣言系统
│   │   │   ├── events.py       # 随机事件
│   │   │   ├── threats.py      # 毁灭威胁
│   │   │   └── actors.py       # 世界行动者
│   │   ├── characters/         # 角色模型
│   │   │   ├── schema.py       # 角色/情绪/影响力/资源账本
│   │   │   ├── memory.py       # 四层记忆 + 执念
│   │   │   └── generator.py    # LLM 角色生成
│   │   ├── engine/             # 叙事引擎
│   │   │   ├── simulation.py   # 核心循环
│   │   │   ├── perception.py   # 环境感知
│   │   │   ├── deliberation.py # LLM 决策
│   │   │   ├── actions.py      # 行动解析 + 冲突
│   │   │   ├── events.py       # 事件模型 + 快照
│   │   │   ├── parallel.py     # 多线并行
│   │   │   └── environment.py  # 环境交互
│   │   ├── plot/               # 剧情导演
│   │   │   ├── director.py     # 导演主逻辑
│   │   │   ├── tension.py      # 张力计算
│   │   │   ├── catalysts.py    # 催化剂
│   │   │   ├── foreshadowing.py # 伏笔池
│   │   │   ├── emotion_curve.py # 情绪曲线
│   │   │   ├── risk_registry.py # 风险备忘
│   │   │   └── status_card.py  # 章间状态
│   │   ├── narrator/           # 叙事生成
│   │   │   ├── narrator.py     # 事件→小说文本
│   │   │   └── quality.py      # 80 分质量检查
│   │   └── llm/
│   │       └── client.py       # LLM 客户端
│   ├── pyproject.toml
│   └── requirements.txt
├── examples/                   # 示例输入
├── LICENSE                     # AGPL-3.0
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTORS.md
└── .gitignore
```
