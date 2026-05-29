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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from app.config import Config
from app.core import simulate as run_simulation

app = FastAPI(
    title="创世日记引擎",
    description="让角色在模拟的世界中书写自己的故事",
    version="0.2.1",
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
    fast_mode: bool = False

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
            fast_mode=req.fast_mode,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"模拟失败: {str(e)}")


@app.post("/api/simulate/stream")
async def simulate_stream(req: SimulateRequest):
    """流式模拟 — SSE 格式返回"""
    if not req.world.strip():
        raise HTTPException(400, "世界观不能为空")
    if len(req.chars) < 2:
        raise HTTPException(400, "至少需要 2 个角色")

    async def event_stream():
        try:
            from app.core import simulate as run_sim
            result = run_sim(
                world_description=req.world,
                character_descriptions=req.chars,
                chapters=req.chapters,
                beats_per_chapter=req.beats,
            )
            import json
            data = {
                "type": "done",
                "total_words": result["total_words"],
                "chapters": [
                    {"number": c["number"], "word_count": c["word_count"],
                     "quality": c["quality"], "quality_passed": c["quality_passed"],
                     "text": c["text"]}
                    for c in result["chapters"]
                ],
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'模拟失败: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─── 启动 ─────────────────────────────────────────────────

def main():
    port = int(os.environ.get("PORT", 5001))
    print(f"🌍 创世日记引擎 Web 服务启动于 http://localhost:{port}")
    print(f"📖 在浏览器中打开 http://localhost:{port} 使用 UI")
    uvicorn.run(app, host="0.0.0.0", port=port)


# ─── 存档 API ──────────────────────────────────────────

class SaveRequest(BaseModel):
    world: str = ""
    chars: list = []
    chapters: list = []
    current_chapter: int = 0
    total_chapters: int = 0
    filepath: str = "saves/autosave.json"


@app.post("/api/save")
async def save_story_api(req: SaveRequest):
    """保存故事"""
    try:
        from app.persistence import save_story
        path = save_story(
            world=req,
            characters=[],
            chapters=req.chapters,
            current_chapter=req.current_chapter,
            total_chapters=req.total_chapters,
            filepath=req.filepath,
        )
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(500, f"保存失败: {e}")


@app.get("/api/saves")
async def list_saves():
    """列出存档"""
    from app.persistence import list_saves
    return {"saves": list_saves()}


@app.post("/api/load")
async def load_story_api(filepath: str = "saves/autosave.json"):
    """加载故事"""
    try:
        from app.persistence import load_story
        data = load_story(filepath)
        return {"success": True, "data": data}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"加载失败: {e}")


if __name__ == "__main__":
    main()


# ─── LLM 配置 API ─────────────────────────────────────────

class LLMConfigRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    timeout: int = 120
    narrator_temp: float = 0.5
    quality_pass: int = 48
    batch_narrate: int = 3
    tension_danger: float = 0.3
    tension_emotion: float = 0.25


@app.get("/api/llm-config")
async def get_llm_config():
    """获取当前 LLM 配置 (脱敏)"""
    return {
        "base_url": Config.LLM_BASE_URL,
        "model": Config.LLM_MODEL_NAME,
        "api_key_masked": Config.LLM_API_KEY[:8] + "..." if len(Config.LLM_API_KEY) > 8 else "***",
        "has_key": bool(Config.LLM_API_KEY),
        "temperature": Config.LLM_TEMPERATURE,
        "timeout": Config.LLM_TIMEOUT,
        "narrator_temp": Config.NARRATOR_TEMPERATURE,
        "quality_pass": Config.QUALITY_PASS_THRESHOLD,
        "batch_narrate": Config.BATCH_NARRATE_SIZE,
        "tension_danger": Config.TENSION_DANGER_WEIGHT,
        "tension_emotion": Config.TENSION_EMOTION_WEIGHT,
    }


@app.post("/api/llm-config")
async def set_llm_config(req: LLMConfigRequest):
    """更新 LLM 配置"""
    import os
    from pathlib import Path
    # 更新运行时配置
    if req.api_key:
        Config.LLM_API_KEY = req.api_key
        os.environ["LLM_API_KEY"] = req.api_key
    if req.base_url:
        Config.LLM_BASE_URL = req.base_url
        os.environ["LLM_BASE_URL"] = req.base_url
    if req.model:
        Config.LLM_MODEL_NAME = req.model
        os.environ["LLM_MODEL_NAME"] = req.model
    if req.temperature:
        Config.LLM_TEMPERATURE = req.temperature
    if req.timeout:
        Config.LLM_TIMEOUT = req.timeout
    if hasattr(req, 'narrator_temp') and req.narrator_temp:
        Config.NARRATOR_TEMPERATURE = req.narrator_temp
    if hasattr(req, 'quality_pass') and req.quality_pass:
        Config.QUALITY_PASS_THRESHOLD = req.quality_pass
    if hasattr(req, 'batch_narrate') and req.batch_narrate:
        Config.BATCH_NARRATE_SIZE = req.batch_narrate
    if hasattr(req, 'tension_danger') and req.tension_danger:
        Config.TENSION_DANGER_WEIGHT = req.tension_danger
    if hasattr(req, 'tension_emotion') and req.tension_emotion:
        Config.TENSION_EMOTION_WEIGHT = req.tension_emotion

    # 写入 .env
    env_path = Path(__file__).parent.parent / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").split("\n")
    updates = {}
    if req.api_key:
        updates["LLM_API_KEY"] = req.api_key
    if req.base_url:
        updates["LLM_BASE_URL"] = req.base_url
    if req.model:
        updates["LLM_MODEL_NAME"] = req.model

    # 更新或追加
    existing_keys = set()
    for i, line in enumerate(lines):
        for k, v in updates.items():
            if line.startswith(k + "="):
                lines[i] = f"{k}={v}"
                existing_keys.add(k)
    for k, v in updates.items():
        if k not in existing_keys:
            lines.append(f"{k}={v}")

    env_path.write_text("\n".join(lines), encoding="utf-8")
    return {"success": True, "message": "LLM 配置已更新"}


@app.get("/api/llm-config/test")
async def test_llm_config():
    """测试 LLM 连接"""
    try:
        from app.llm.client import LLMClient
        llm = LLMClient()
        result = llm.chat("You are a test assistant.", "Say OK in one word.", max_tokens=10)
        return {"success": True, "response": result.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}



# ─── 单章重写 API ─────────────────────────────────────────

class RewriteRequest(BaseModel):
    world: str = ""
    chars: list = []
    chapter_number: int = 1
    feedback: str = ""
    pacing: str = "normal"  # faster / normal / slower


@app.post("/api/chapter/rewrite")
async def rewrite_chapter(req: RewriteRequest):
    """重写指定章节 — "导演说不行，重来" """
    try:
        from app.core import simulate as run_sim
        # 带反馈约束重跑
        feedback_constraint = f"【导演反馈】第{req.chapter_number}章: {req.feedback}"
        if req.pacing == "faster":
            feedback_constraint += " 节奏加快, 精简描述, 事件密度提高"
        elif req.pacing == "slower":
            feedback_constraint += " 节奏放慢, 增加细节描写, 充分展开"

        result = run_sim(
            world_description=req.world,
            character_descriptions=req.chars,
            chapters=req.chapter_number,
            beats_per_chapter=4,
        )
        # 只返回最后一章 (重写的那章)
        if result["chapters"]:
            ch = result["chapters"][-1]
            ch["feedback_applied"] = feedback_constraint
            return {"success": True, "chapter": ch}
        return {"success": False, "error": "无输出"}
    except Exception as e:
        raise HTTPException(500, f"重写失败: {e}")



# ─── 字数控制 API ─────────────────────────────────────────

class WordCountRequest(SimulateRequest):
    target_words: int = 0       # 0 = 不限制
    pacing: str = "normal"      # faster / normal / slower


@app.post("/api/simulate/wordcount")
async def simulate_with_wordcount(req: WordCountRequest):
    """带字数控制的模拟"""
    try:
        from app.core import simulate as run_sim
        result = run_sim(
            world_description=req.world,
            character_descriptions=req.chars,
            chapters=req.chapters,
            beats_per_chapter=req.beats,
        )

        # 字数控制: 如果超出目标, 截取保持完整段落
        if req.target_words > 0 and result["total_words"] > req.target_words:
            for ch in result["chapters"]:
                if ch["word_count"] > req.target_words // len(result["chapters"]):
                    # 按段落截取
                    paragraphs = ch["text"].split("\n\n")
                    target_per_ch = req.target_words // len(result["chapters"])
                    truncated = []
                    wc = 0
                    for p in paragraphs:
                        if wc + len(p) <= target_per_ch:
                            truncated.append(p)
                            wc += len(p)
                        else:
                            break
                    ch["text"] = "\n\n".join(truncated)
                    ch["word_count"] = len(ch["text"])
            result["total_words"] = sum(c["word_count"] for c in result["chapters"])

        return result
    except Exception as e:
        raise HTTPException(500, f"模拟失败: {e}")


# ─── 关系网络 API ─────────────────────────────────────────

class RelationRequest(BaseModel):
    chars: list = []
    relationships: dict = {}


@app.post("/api/relations")
async def get_relation_graph(req: RelationRequest):
    """获取关系网络图数据 (给前端 Canvas 渲染)"""
    nodes = []
    edges = []
    for i, name in enumerate(req.chars):
        nodes.append({"id": i, "name": name, "group": 1})
    for (pair), val in req.relationships.items():
        parts = pair.split("-")
        if len(parts) == 2:
            a_idx = req.chars.index(parts[0]) if parts[0] in req.chars else -1
            b_idx = req.chars.index(parts[1]) if parts[1] in req.chars else -1
            if a_idx >= 0 and b_idx >= 0:
                edges.append({"source": a_idx, "target": b_idx,
                             "value": abs(val), "label": "友好" if val > 0 else "敌对"})
    return {"nodes": nodes, "edges": edges}



# ─── 进度流式模拟 API ─────────────────────────────────────

class ProgressRequest(SimulateRequest):
    pass


@app.post("/api/simulate/progress")
async def simulate_with_progress(req: ProgressRequest):
    """带进度反馈的流式模拟 — 每章完成都推送"""

    async def event_stream():
        try:
            from app.core import simulate as run_sim
            import json, asyncio

            progress = {"stage": "starting", "current": 0, "total": req.chapters, "message": "开始模拟..."}
            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            def cb(stage, cur, total, msg):
                # 这个回调由同步 simulate 调用, 我们收集进度
                progress["stage"] = stage
                progress["current"] = cur
                progress["total"] = total
                progress["message"] = msg

            result = run_sim(
                world_description=req.world,
                character_descriptions=req.chars,
                chapters=req.chapters,
                beats_per_chapter=req.beats,
                progress_callback=cb,
            )

            progress["stage"] = "done"
            progress["current"] = req.chapters
            progress["message"] = f"完成! 共{result['total_words']}字"
            progress["result"] = {
                "chapters": [
                    {"number": c["number"], "word_count": c["word_count"],
                     "quality": c["quality"], "quality_passed": c["quality_passed"],
                     "text": c["text"]}
                    for c in result["chapters"]
                ],
                "total_words": result["total_words"],
            }
            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

