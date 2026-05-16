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
    Pass `style_prefix` to override the default IMAGE_STYLE_PREFIX (used by the workbench).

    Robustness: up to 3 attempts with backoff. The LAST attempt drops fal's
    safety checker — flux's safety pass over-filters on math/history/numeric
    prompts (returns 0 images), which is the dominant failure mode we see in
    practice. The style prompt itself bans humans/faces so dropping the
    checker on a single final attempt is acceptable risk for the demo.
    """
    if not settings.fal_key:
        raise RuntimeError("FAL_KEY not configured")
    os.environ.setdefault("FAL_KEY", settings.fal_key)

    prefix = style_prefix if style_prefix is not None else IMAGE_STYLE_PREFIX
    full_prompt = prefix + image_prompt

    last_error: Exception | None = None
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            result = await fal_client.subscribe_async(
                settings.fal_image_model,
                arguments={
                    "prompt": full_prompt,
                    "image_size": "portrait_4_3",
                    "num_images": 1,
                    # Drop the safety pass on the final attempt — it's the
                    # main reason innocuous prompts return zero images.
                    "enable_safety_checker": attempt < attempts,
                },
            )
            images = result.get("images") or []
            if not images:
                raise RuntimeError(
                    f"fal.ai returned no images (attempt {attempt}/{attempts})"
                )
            url = images[0]["url"]
            _IMG_DIR.mkdir(parents=True, exist_ok=True)
            out_path = _IMG_DIR / f"{card_id}.png"
            await _download(url, out_path)
            return f"/media/img/{card_id}.png"
        except Exception as e:
            last_error = e
            if attempt < attempts:
                # Linear backoff: 1s, 2s. Avoid log spam since the wrapper
                # in generator._img() also logs once.
                await asyncio.sleep(attempt)
                continue
            raise RuntimeError(
                f"fal.ai failed after {attempts} attempts for card {card_id}: {e}"
            ) from last_error
    # Unreachable but keeps mypy happy.
    raise RuntimeError(f"fal.ai loop exited without result for card {card_id}")


async def _download(url: str, out_path: Path) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        await asyncio.to_thread(out_path.write_bytes, resp.content)
