"""Phase 2/3 feed routes: users (onboarding), feed (read), interactions (record).

Onboarding takes CATEGORY preferences (not topics). The feed is seeded from
existing DB cards in those categories — there is no automatic generation.
The dashboard's Generate-Next button (Phase 3) is the only way to mint new
cards from the app surface; the workbench remains the manual generation tool.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.content.generator import generate_card
from app.content.prompts import CARD_VERSION
from app.content.topics import CATEGORIES, HOOK_TYPES, TAXONOMY
from app.content.voices import CUSTOM_VOICES, VOICES
from app.db import client as db


log = logging.getLogger(__name__)
router = APIRouter()


# ---------- Pydantic IO ----------


class CreateUserRequest(BaseModel):
    # Category names from CATEGORIES. Stored in users.topic_preferences (legacy
    # column name kept; semantics upgraded to "category preferences").
    topic_preferences: list[str] = Field(default_factory=list)
    # Friendly voice names from VOICES. When non-empty, fresh generation cycles
    # through this subset instead of the global CUSTOM_VOICES list.
    voice_preferences: list[str] = Field(default_factory=list)
    cold_start_count: int = Field(
        default=0,
        ge=0,
        le=10,
        description="If 0, seed the feed from existing DB cards (no generation). If >0, generate that many fresh cards in parallel.",
    )
    per_category_count: int = Field(
        default=0,
        ge=0,
        le=5,
        description="If >0, generate this many fresh cards per selected category, cycling voices. Takes precedence over cold_start_count.",
    )
    seed_limit: int = Field(
        default=100, ge=0, le=500, description="Max existing cards to seed when cold_start_count == 0."
    )
    skip_audio: bool = False
    skip_image: bool = False


class CreateUserResponse(BaseModel):
    user_id: str
    cards: list[dict]
    topic_preferences: list[str]


class InteractionRequest(BaseModel):
    user_id: str
    card_id: str
    event_type: str = Field(description="like | dislike | dismiss | view | complete | skip")
    view_duration_ms: int | None = None


class SyncRequest(BaseModel):
    user_id: str
    limit: int = Field(default=500, ge=1, le=2000)


# ---------- helpers ----------


def _valid_categories(prefs: list[str]) -> list[str]:
    return [c for c in prefs if c in CATEGORIES]


def _valid_voices(prefs: list[str]) -> list[str]:
    """Filter to known voice names. Falls back to CUSTOM_VOICES if none match."""
    valid = [v for v in prefs if v in VOICES]
    return valid or list(CUSTOM_VOICES)


async def _generate_batch_for_categories(
    user_id: str,
    categories: list[str],
    count: int,
    skip_audio: bool,
    skip_image: bool,
    voices: list[str] | None = None,
) -> list[dict]:
    """Generate `count` cards, sampling categories with replacement and picking
    a random topic + hook for each. Used only when cold_start_count > 0."""
    if not categories:
        categories = CATEGORIES
    voice_pool = voices or list(CUSTOM_VOICES)
    coros = []
    for i in range(count):
        cat = random.choice(categories)
        topic = random.choice(TAXONOMY[cat])
        hook = random.choice(HOOK_TYPES)
        voice = voice_pool[i % len(voice_pool)] if voice_pool else None
        coros.append(
            generate_card(
                category=cat,
                topic=topic,
                hook_type=hook,
                created_for_user=user_id,
                skip_audio=skip_audio,
                skip_image=skip_image,
                voice=voice,
            )
        )
    results = await asyncio.gather(*coros, return_exceptions=True)
    cards: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            log.exception("batch generation failed: %s", r)
            continue
        cards.append(r)
    if cards:
        db.enqueue_cards(user_id, [c["id"] for c in cards], start_position=0)
    return cards


async def _generate_per_category(
    user_id: str,
    categories: list[str],
    n_per_category: int,
    skip_audio: bool,
    skip_image: bool,
    voices: list[str] | None = None,
) -> list[dict]:
    """Generate `n_per_category` cards for EACH selected category, cycling
    through `voices` (or CUSTOM_VOICES) round-robin so the user immediately
    hears the personalities they picked."""
    if not categories:
        categories = CATEGORIES
    voice_pool = voices or list(CUSTOM_VOICES)
    coros = []
    i = 0
    for cat in categories:
        topics = TAXONOMY.get(cat) or []
        if not topics:
            continue
        for _ in range(n_per_category):
            topic = random.choice(topics)
            hook = random.choice(HOOK_TYPES)
            voice = voice_pool[i % len(voice_pool)] if voice_pool else None
            i += 1
            coros.append(
                generate_card(
                    category=cat,
                    topic=topic,
                    hook_type=hook,
                    created_for_user=user_id,
                    skip_audio=skip_audio,
                    skip_image=skip_image,
                    voice=voice,
                )
            )
    results = await asyncio.gather(*coros, return_exceptions=True)
    cards: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            log.exception("per-category generation failed: %s", r)
            continue
        cards.append(r)
    if cards:
        db.enqueue_cards(user_id, [c["id"] for c in cards], start_position=0)
    return cards


# ---------- routes ----------


@router.post("/api/users", response_model=CreateUserResponse)
async def create_user(req: CreateUserRequest) -> CreateUserResponse:
    user_id = str(uuid.uuid4())
    categories = _valid_categories(req.topic_preferences)
    voices = _valid_voices(req.voice_preferences)
    db.insert_user(user_id, categories)

    # Per-category fresh-generation path: N cards × every selected category,
    # cycling through the user's chosen voices. This is the onboarding default
    # for the new flow. We also seed historical current-version cards from the
    # DB after the fresh ones so users have a long enough feed to swipe through
    # before the agent's next-gen kicks in.
    if req.per_category_count > 0:
        fresh = await _generate_per_category(
            user_id=user_id,
            categories=categories,
            n_per_category=req.per_category_count,
            skip_audio=req.skip_audio,
            skip_image=req.skip_image,
            voices=voices,
        )
        fresh_ids = {c["id"] for c in fresh}
        # Append historical cards (same version, matching the user's chosen
        # categories) AFTER the fresh ones so the new generations lead the feed.
        historical = db.sample_existing_cards(
            categories=categories or None,
            limit=req.seed_limit,
            version=CARD_VERSION,
        )
        historical = [c for c in historical if c["id"] not in fresh_ids]
        if historical:
            db.enqueue_cards(
                user_id,
                [c["id"] for c in historical],
                start_position=db.next_position(user_id),
            )
        return CreateUserResponse(
            user_id=user_id,
            cards=fresh + historical,
            topic_preferences=categories,
        )

    # Zero-generation path: seed from existing DB cards filtered by the user's
    # category preferences AND the current prompt version.
    if req.cold_start_count == 0:
        cards = db.sample_existing_cards(
            categories=categories or None,
            limit=req.seed_limit,
            version=CARD_VERSION,
        )
        if cards:
            db.enqueue_cards(user_id, [c["id"] for c in cards], start_position=0)
        return CreateUserResponse(
            user_id=user_id,
            cards=cards,
            topic_preferences=categories,
        )

    # Fresh-generation path (opt-in via cold_start_count > 0).
    cards = await _generate_batch_for_categories(
        user_id=user_id,
        categories=categories,
        count=req.cold_start_count,
        skip_audio=req.skip_audio,
        skip_image=req.skip_image,
        voices=voices,
    )
    return CreateUserResponse(user_id=user_id, cards=cards, topic_preferences=categories)


@router.get("/api/feed")
async def get_feed(user_id: str, offset: int = 0, limit: int = 20) -> dict:
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, f"user {user_id!r} not found")
    cards = db.get_feed(user_id, offset=offset, limit=limit, version=CARD_VERSION)
    return {
        "cards": cards,
        "total": db.feed_length(user_id, version=CARD_VERSION),
        "version": CARD_VERSION,
    }


@router.post("/api/interactions")
async def post_interaction(req: InteractionRequest) -> dict:
    db.insert_interaction(
        user_id=req.user_id,
        card_id=req.card_id,
        event_type=req.event_type,
        view_duration_ms=req.view_duration_ms,
    )
    return {"ok": True}


@router.post("/api/feed/sync")
async def sync_feed(req: SyncRequest) -> dict:
    """Ensure the user's feed_queue contains every recent current-version card.
    No generation; just DB appends."""
    if not db.get_user(req.user_id):
        raise HTTPException(404, f"user {req.user_id!r} not found")
    all_cards = db.sample_existing_cards(limit=req.limit, version=CARD_VERSION)
    existing = db.get_feed(req.user_id, offset=0, limit=10_000, version=CARD_VERSION)
    existing_ids = {c["id"] for c in existing}
    new_ids = [c["id"] for c in all_cards if c["id"] not in existing_ids]
    if new_ids:
        start = db.next_position(req.user_id)
        db.enqueue_cards(req.user_id, new_ids, start_position=start)
    return {
        "ok": True,
        "added": len(new_ids),
        "total": len(existing) + len(new_ids),
        "version": CARD_VERSION,
    }
