# Novel World Engine

Let characters write their own stories in the worlds we create.

## What is this?

A multi-agent narrative simulation engine. Characters (Agents) with independent personalities, emotions, memories, and motivations interact freely in a virtual world. Stories don't get written by prompting an LLM — they **emerge** from character interactions and conflicts.

```
Not "AI writes a novel" — it's "characters live out stories in the worlds we create"
```

## Quick Start

### Install

```bash
pip install -r backend/requirements.txt
```

### Configure

```bash
cp backend/.env.example backend/.env
# Edit .env, set your LLM_API_KEY
```

### Run

**One-click start:**
```bash
# Windows
start.bat

# Linux/Mac
bash start.sh
```

Then open http://localhost:5001 in your browser.

**Command line:**
```bash
cd backend
python -m app.cli run --world ../examples/world.txt --chars ../examples/chars.txt --chapters 3
```

**Python API (3 lines):**
```python
from app.core import simulate
result = simulate("A cultivation academy world...", ["Lin Beichen, 16, outer disciple", "Zhao Wuji, 18, inner disciple"], chapters=3)
print(result["chapters"][0]["text"])
```

## Features

### v0.3.0

| Feature | Description |
|---------|-------------|
| **Character Simulation** | Agents with independent personalities, emotions, memories, obsessions, and needs |
| **Living World** | Weather, rumors, world actors, random events, doom threats — all evolve independently |
| **Timeline & Divergence** | Import a novel, build a timeline, insert a new character at any point — the story diverges into an alternate timeline |
| **Parallel Engine** | Up to 5 simultaneous narrative threads with POV switching |
| **6-D Influence** | Characters have independent influence in economic, political, military, knowledge, social, and mystical dimensions |
| **Quality Gate** | Every chapter is automatically scored across 8 dimensions (80-point system) |
| **Web UI** | Configure LLM, visualize relationship graphs, rewrite chapters with director feedback, real-time progress bar |
| **Streaming** | SSE API for real-time chapter generation |
| **Save/Load** | Full state persistence, supports story rollback |


## Version History

### v0.8.x — External Memory + Lazy Building

| Version | Features |
|---------|----------|
| v0.8.1 | **External Memory**: RAG vector retrieval (SQLite) + FDR progressive compression. 80% prompt token reduction |
| v0.8.0 | **Lazy World Building**: Store raw text, parse locations on first visit. Startup from 8 to 2 LLM calls |

### v0.7.x — Character Lifecycle

| Version | Features |
|---------|----------|
| v0.7.1 | **Plot-driven Cast Changes**: Director decides entrances/exits based on tension curve |
| v0.7.0 | **CharacterPool**: active/dormant/deceased lifecycle with forced revival |

### v0.6.x — Extensible Actions

| Version | Features |
|---------|----------|
| v0.6.0 | Extensible action space, LLM-generated weather/threats/events, 7 configurable params |

### v0.5.x — World Fog

| Version | Features |
|---------|----------|
| v0.5.0 | **World Fog**: Characters only perceive what they know. 60%+ prompt reduction |

### v0.4.x — Character Tiers

| Version | Features |
|---------|----------|
| v0.4.0 | **3-tier Characters**: Primary/Secondary/Background. Support 15-20 concurrent characters |

### v0.3.x — Web UI

| Version | Features |
|---------|----------|
| v0.3.0 | Web LLM config, progress bar, relation graph, chapter rewrite, word count control |

### v0.2.x — Timeline + Parallel

| Version | Features |
|---------|----------|
| v0.2.1 | LLM retry (exponential backoff), parallel decisions (ThreadPool) |
| v0.2.0 | Timeline model, novel parser, divergence mechanism |

### v0.1.x — Initial

| Version | Features |
|---------|----------|
| v0.1.0 | 6-layer architecture, CLI + Python API |
### v0.7.0

| Feature | Description |
|---------|-------------|
| **Character Lifecycle** | Characters leave, new ones appear - cast naturally evolves over long stories |

### v0.6.0

| Feature | Description |
|---------|-------------|
| **Extensible Actions** | LLM generates world-specific actions (Cultivate/Work/Drive...) |
| **World Rules from LLM** | Weather, threats, events generated from world description |
| **Configurable Params** | 7 env vars for tuning thresholds without code changes |

### v0.5.0

| Feature | Description |
|---------|-------------|
| **World Fog** | Characters only perceive what they know. 60%+ prompt reduction, 2-3x speedup |

### v0.4.0

| Feature | Description |
|---------|-------------|
| **Character Tiers** | Primary(full LLM) / Secondary(light) / Background(zero LLM) — support 15-20 characters |

### Architecture

```
6 layers:

1. World Model         — Locations, factions, timeline, rules + weather/rumors/threats/actors
2. Character Model     — Personality, emotions, memory, obsessions, stats, influence, resource ledger
3. Narrative Engine    — Beat loop: perceive → LLM decide → conflict resolve → state update
4. Plot Director       — Tension monitoring, catalyst injection, foreshadowing, risk memos
5. Narrator            — Event sequence → novel prose, cross-beat coherence
6. Quality Gate        — 80-point 8-dimension quality check
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## Project Structure

```
novel-world-engine/
├── start.bat / start.sh     # One-click launcher
├── backend/
│   └── app/
│       ├── cli.py           # CLI entry
│       ├── core.py          # Python API (simulate())
│       ├── server.py        # Web server (FastAPI)
│       ├── timeline.py      # Timeline model + divergence
│       ├── novel_parser.py  # Novel → structured extraction
│       ├── persistence.py   # Save/Load story state
│       ├── world/           # World model + weather/rumors/events/threats/actors
│       ├── characters/      # Character model + memory/obsessions
│       ├── engine/          # Core simulation loop + parallel engine
│       ├── plot/            # Plot director + tension/catalysts/foreshadowing
│       ├── narrator/        # Event → prose + quality check
│       └── llm/             # LLM client with retry + error handling
├── tests/                   # Unit tests (15 core tests)
├── examples/                # Sample outputs (19K-word fantasy story)
├── LICENSE                  # AGPL-3.0
├── ARCHITECTURE.md
└── README.md
```

## Use Cases

- **Original Fiction**: Set up a world and characters, let the engine generate a story
- **Fan Fiction**: Import an existing novel, insert an OC at any chapter, explore "what if" scenarios
- **Game NPCs**: Generate backstories and emergent interactions for game characters
- **Writing Assistant**: Generate drafts, iterate with director feedback on specific chapters

## License

AGPL-3.0. See [LICENSE](LICENSE).

For commercial licensing, contact the author.
