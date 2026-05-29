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
