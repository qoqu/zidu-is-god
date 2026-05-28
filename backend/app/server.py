"""
创世日记引擎 — Web 服务入口

启动:
  uvicorn app.server:app --reload --port 5001
  或 python -m uvicorn app.server:app --port 5001

访问:
  http://localhost:5001
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from app.config import Config
from app.core import simulate as run_simulation

app = FastAPI(
    title="创世日记引擎",
    description="让角色在模拟的世界中书写自己的故事",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 请求/响应模型 ────────────────────────────────────────

class SimulateRequest(BaseModel):
    world: str
    chars: list[str]
    chapters: int = 3
    beats: int = 3
    direction: str = ""

class SimulateResponse(BaseModel):
    chapters: list[dict]
    total_words: int
    quality_scores: list[int]


# ─── API 路由 ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """UI 页面"""
    html_path = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    alt_path = os.path.join(os.path.dirname(__file__), "frontend/index.html")
    
    for p in [html_path, alt_path]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return HTMLResponse("<h1>创世日记引擎</h1><p>前端页面未找到</p>")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "创世日记引擎"}


@app.post("/api/simulate", response_model=SimulateResponse)
async def simulate(req: SimulateRequest):
    """运行叙事模拟"""
    if not req.world.strip():
        raise HTTPException(400, "世界观不能为空")
    if len(req.chars) < 2:
        raise HTTPException(400, "至少需要 2 个角色")

    try:
        result = run_simulation(
            world_description=req.world,
            character_descriptions=req.chars,
            chapters=req.chapters,
            beats_per_chapter=req.beats,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"模拟失败: {str(e)}")


# ─── 启动 ─────────────────────────────────────────────────

def main():
    port = int(os.environ.get("PORT", 5001))
    print(f"🌍 创世日记引擎 Web 服务启动于 http://localhost:{port}")
    print(f"📖 在浏览器中打开 http://localhost:{port} 使用 UI")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
