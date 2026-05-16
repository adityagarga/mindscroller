from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import MEDIA_DIR
from app.db.client import init_db
from app.routes import agent, feed, preview, workbench


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "img").mkdir(exist_ok=True)
    (MEDIA_DIR / "audio").mkdir(exist_ok=True)
    yield


app = FastAPI(title="mindscroller", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(preview.router)
app.include_router(workbench.router)
app.include_router(feed.router)
app.include_router(agent.router)


@app.get("/")
async def root() -> dict:
    return {
        "ok": True,
        "workbench": "/workbench",
        "preview": "/preview",
        "feed_api": {
            "create_user": "POST /api/users",
            "get_feed": "GET /api/feed?user_id=...",
            "interaction": "POST /api/interactions",
        },
        "agent_api": {
            "state": "GET /api/agent/state?user_id=...",
            "brief": "POST /api/agent/brief?user_id=...",
            "generate_next": "POST /api/agent/generate-next",
        },
    }
