"""End-to-end card generation.

Pipeline (strict ordering):
    1. OpenAI -> CardDraft (visual_hook + script + image_prompt)  [the brain]
    2 & 3. asyncio.gather:
           fal.ai(draft.image_prompt) -> image file
           Gradium(draft.script)      -> audio file (TTS reads the script verbatim)
    4. Persist row to SQLite.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.content.openai_client import generate_card_draft
from app.content.fal_client import render_image
from app.content.gradium_client import render_audio
from app.content.prompts import CARD_VERSION
from app.content.schema import CardDraft
from app.content.voices import DEFAULT_VOICE, voice_id_for
from app.db import client as db

log = logging.getLogger(__name__)


async def generate_card(
    category: str,
    topic: str,
    hook_type: str,
    angle: str | None = None,
    created_for_user: str | None = None,
    parent_card_id: str | None = None,
    thread_order: int | None = None,
    skip_audio: bool = False,
    skip_image: bool = False,
    system_prompt_override: str | None = None,
    style_prefix_override: str | None = None,
    voice: str | None = None,
) -> dict[str, Any]:
    """Generate one card end-to-end and persist it. Returns the full DB row."""
    card_id = str(uuid.uuid4())

    # Step 1: text first (everything downstream depends on this output).
    draft: CardDraft = await generate_card_draft(
        category=category,
        topic=topic,
        hook_type=hook_type,
        angle=angle,
        system_prompt=system_prompt_override,
    )

    # Steps 2 & 3: image + audio in parallel, each consuming a field of `draft`.
    async def _img() -> str | None:
        if skip_image:
            return None
        try:
            return await render_image(card_id, draft.image_prompt, style_prefix=style_prefix_override)
        except Exception as e:
            log.exception("image render failed for card %s: %s", card_id, e)
            return None

    voice_name = voice or DEFAULT_VOICE
    voice_id = voice_id_for(voice_name)

    async def _aud() -> str | None:
        if skip_audio:
            return None
        try:
            return await render_audio(card_id, draft.script, voice_id=voice_id)
        except Exception as e:
            log.exception("audio render failed for card %s: %s", card_id, e)
            return None

    image_path, audio_path = await asyncio.gather(_img(), _aud())

    # Step 4: persist.
    row = {
        "id": card_id,
        "category": category,
        "topic": topic,
        "hook_type": hook_type,
        "visual_hook": draft.visual_hook,
        "script": draft.script,
        "image_prompt": draft.image_prompt,
        "image_path": image_path,
        "audio_path": audio_path,
        "parent_card_id": parent_card_id,
        "thread_order": thread_order,
        "created_for_user": created_for_user,
        "version": CARD_VERSION,
        "voice": voice_name,
    }
    db.insert_card(row)
    return db.get_card(card_id)
