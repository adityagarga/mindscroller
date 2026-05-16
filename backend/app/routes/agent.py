"""Phase 3 agent endpoints.

- GET  /api/agent/state?user_id=...   → affinity + recent + brief + discovered (one shot for the dashboard)
- POST /api/agent/brief                → recompute & return the latest brief
- POST /api/agent/generate-next        → take a brief, generate one card, append to queue, return it

Generation here is MANUAL ONLY — triggered by the dashboard's Generate button.
Nothing fires automatically on interactions.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.brief import Brief, generate_brief
from app.content.generator import generate_card
from app.content.voices import CUSTOM_VOICES, pick_custom_voice
from app.content.topics import HOOK_TYPES, TAXONOMY
from app.db import client as db


log = logging.getLogger(__name__)
router = APIRouter()


# ---------- helpers ----------


def _agent_snapshot(user_id: str) -> dict:
    """The shape the dashboard renders."""
    return {
        "affinity": db.affinity_breakdown(user_id),
        "interactions_total": db.interaction_count(user_id),
        "recent_interactions": db.recent_interactions_with_cards(user_id, limit=10),
        "discovered_topics": db.list_discovered_topics(),
    }


# ---------- routes ----------


class AgentStateResponse(BaseModel):
    affinity: dict
    interactions_total: int
    recent_interactions: list[dict]
    discovered_topics: list[dict]


@router.get("/api/agent/state", response_model=AgentStateResponse)
async def get_state(user_id: str) -> dict:
    if not db.get_user(user_id):
        raise HTTPException(404, f"user {user_id!r} not found")
    return _agent_snapshot(user_id)


class BriefResponse(BaseModel):
    brief: Brief
    snapshot: AgentStateResponse


@router.post("/api/agent/brief", response_model=BriefResponse)
async def post_brief(user_id: str) -> dict:
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, f"user {user_id!r} not found")
    category_prefs = user.get("topic_preferences") or []
    brief = await generate_brief(user_id, category_preferences=category_prefs)
    return {"brief": brief.model_dump(), "snapshot": _agent_snapshot(user_id)}


class GenerateNextRequest(BaseModel):
    user_id: str
    brief: Brief | None = Field(
        default=None,
        description="Optional explicit brief. If omitted, a fresh brief is computed first.",
    )


@router.post("/api/agent/generate-next")
async def post_generate_next(req: GenerateNextRequest) -> dict:
    user = db.get_user(req.user_id)
    if not user:
        raise HTTPException(404, f"user {req.user_id!r} not found")

    category_prefs = user.get("topic_preferences") or []
    brief = req.brief or await generate_brief(req.user_id, category_preferences=category_prefs)

    if brief.category not in TAXONOMY:
        raise HTTPException(422, f"brief category {brief.category!r} not in TAXONOMY")
    if brief.hook_type not in HOOK_TYPES:
        raise HTTPException(422, f"brief hook_type {brief.hook_type!r} not in HOOK_TYPES")

    # Persist a newly-discovered subtopic before generation so it shows in the
    # taxonomy regardless of whether generation succeeds.
    if brief.is_new_topic:
        db.record_discovered_topic(brief.category, brief.topic, req.user_id)

    # Round-robin the personality voices across this user's generations.
    voice = pick_custom_voice(db.interaction_count(req.user_id))

    card = await generate_card(
        category=brief.category,
        topic=brief.topic,
        hook_type=brief.hook_type,
        angle=None if not brief.angle else brief.angle,
        created_for_user=req.user_id,
        voice=voice,
    )
    # Append to the user's feed queue at the END so they don't lose their place.
    db.enqueue_cards(req.user_id, [card["id"]], start_position=db.next_position(req.user_id))

    return {
        "card": card,
        "brief": brief.model_dump(),
        "voice_used": voice,
        "snapshot": _agent_snapshot(req.user_id),
    }


@router.get("/api/agent/voices/custom")
async def get_custom_voices() -> dict:
    return {"voices": CUSTOM_VOICES}


@router.get("/api/agent/stats")
async def get_stats(user_id: str) -> dict:
    """Simple per-category / per-subtopic stats for the dashboard:
    watch percentage (share of total watch_ms), like count, dislike count."""
    if not db.get_user(user_id):
        raise HTTPException(404, f"user {user_id!r} not found")
    return db.watch_and_engagement_stats(user_id)
