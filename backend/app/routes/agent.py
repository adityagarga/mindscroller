"""Phase 3 agent endpoints.

- GET  /api/agent/state?user_id=...   → affinity + recent + brief + discovered (one shot for the dashboard)
- POST /api/agent/brief                → recompute & return the latest brief
- POST /api/agent/generate-next        → take a brief, generate one card, append to queue, return it

Generation here is MANUAL ONLY — triggered by the dashboard's Generate button.
Nothing fires automatically on interactions.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.agent.brief import Brief, generate_brief
from app.agent.planner import plan_next_batch
from app.content.generator import generate_card
from app.content.voices import CUSTOM_VOICES, VOICES, pick_custom_voice
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


def _valid_voice_pool(prefs: list[str]) -> list[str]:
    """Filter to known voice names, fall back to CUSTOM_VOICES."""
    valid = [v for v in prefs if v in VOICES]
    return valid or list(CUSTOM_VOICES)


@router.get("/api/agent/stats")
async def get_stats(
    user_id: str,
    voice_preferences: list[str] = Query(default_factory=list),
) -> dict:
    """Per-category / per-subtopic stats + a live preview of the next 4 cards
    the agent would generate, given current interaction history. The preview
    is computed by the same deterministic planner the batch endpoint uses, so
    the dashboard preview always matches what /generate-batch will produce."""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, f"user {user_id!r} not found")

    stats = db.watch_and_engagement_stats(user_id)
    hook_affinity = db.affinity_breakdown(user_id).get("hook_type", [])
    voice_pool = _valid_voice_pool(voice_preferences)
    category_prefs = user.get("topic_preferences") or []
    slots = plan_next_batch(
        stats=stats,
        hook_affinity=hook_affinity,
        category_prefs=category_prefs,
        voice_prefs=voice_pool,
        interaction_count=db.interaction_count(user_id),
        n=4,
    )
    return {**stats, "next_plan": {"slots": [s.model_dump() for s in slots]}}


class GenerateBatchRequest(BaseModel):
    user_id: str
    n: int = Field(default=4, ge=1, le=8)
    voice_preferences: list[str] = Field(default_factory=list)


@router.post("/api/agent/generate-batch")
async def post_generate_batch(req: GenerateBatchRequest) -> dict:
    """Deterministic batch generation. Computes the same plan the dashboard's
    Next-Gen preview shows, then generates each slot in parallel (Gradium's
    semaphore caps audio concurrency at 2). Cards are enqueued in plan order
    after any existing queue tail; the frontend splices them in at the
    currently active card index for immediate visibility."""
    user = db.get_user(req.user_id)
    if not user:
        raise HTTPException(404, f"user {req.user_id!r} not found")

    stats = db.watch_and_engagement_stats(req.user_id)
    hook_affinity = db.affinity_breakdown(req.user_id).get("hook_type", [])
    voice_pool = _valid_voice_pool(req.voice_preferences)
    category_prefs = user.get("topic_preferences") or []
    slots = plan_next_batch(
        stats=stats,
        hook_affinity=hook_affinity,
        category_prefs=category_prefs,
        voice_prefs=voice_pool,
        interaction_count=db.interaction_count(req.user_id),
        n=req.n,
    )

    # Validate before generation (defensive — the planner only emits valid
    # categories/hooks, but the user's category_prefs could in principle leak
    # legacy values).
    for s in slots:
        if s.category not in TAXONOMY:
            raise HTTPException(500, f"planner produced invalid category {s.category!r}")
        if s.hook_type not in HOOK_TYPES:
            raise HTTPException(500, f"planner produced invalid hook_type {s.hook_type!r}")

    results = await asyncio.gather(
        *[
            generate_card(
                category=s.category,
                topic=s.topic,
                hook_type=s.hook_type,
                created_for_user=req.user_id,
                voice=s.voice,
            )
            for s in slots
        ],
        return_exceptions=True,
    )
    successful: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            log.exception("generate_card failed in batch: %s", r)
        else:
            successful.append(r)

    if successful:
        db.enqueue_cards(
            req.user_id,
            [c["id"] for c in successful],
            start_position=db.next_position(req.user_id),
        )

    return {
        "cards": successful,
        "slots": [s.model_dump() for s in slots],
        "snapshot": _agent_snapshot(req.user_id),
        "failed": len(slots) - len(successful),
    }
