"""fal.ai image renderer. Consumes the LLM-authored image_prompt and saves a PNG locally."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import fal_client
import httpx

from app.config import MEDIA_DIR, settings
from app.content.prompts import IMAGE_STYLE_PREFIX


_IMG_DIR = MEDIA_DIR / "img"


async def render_image(
    card_id: str,
    image_prompt: str,
    style_prefix: str | None = None,
) -> str:
    """Render one image, save to media/img/{card_id}.png, return the public path (e.g. /media/img/<id>.png).
    Pass `style_prefix` to override the default IMAGE_STYLE_PREFIX (used by the workbench)."""
    if not settings.fal_key:
        raise RuntimeError("FAL_KEY not configured")
    os.environ.setdefault("FAL_KEY", settings.fal_key)

    prefix = style_prefix if style_prefix is not None else IMAGE_STYLE_PREFIX
    full_prompt = prefix + image_prompt

    # fal_client.subscribe_async waits for the result; queue size is small for hackathon use.
    result = await fal_client.subscribe_async(
        settings.fal_image_model,
        arguments={
            "prompt": full_prompt,
            "image_size": "portrait_4_3",
            "num_images": 1,
            "enable_safety_checker": True,
        },
    )
    images = result.get("images") or []
    if not images:
        raise RuntimeError(f"fal.ai returned no images for card {card_id}")
    url = images[0]["url"]

    _IMG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _IMG_DIR / f"{card_id}.png"
    await _download(url, out_path)
    return f"/media/img/{card_id}.png"


async def _download(url: str, out_path: Path) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        await asyncio.to_thread(out_path.write_bytes, resp.content)
