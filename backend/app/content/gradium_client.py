"""Gradium TTS via the official `gradium` Python SDK.

Endpoint is a WebSocket (`wss://api.gradium.ai/api/speech/tts`) wrapped by
the SDK's `GradiumClient.tts(setup, text)` async API. We use the buffered
(non-streaming) variant since we pre-generate audio at card-creation time.

Output format: WAV. Gradium does not support mp3; WAV plays natively in
<audio> tags in every browser.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from gradium.client import GradiumClient

from app.config import MEDIA_DIR, settings


_AUDIO_DIR = MEDIA_DIR / "audio"
_client: GradiumClient | None = None

# Gradium hard-caps at 3 concurrent WebSocket TTS sessions. We gate to 2 to
# leave headroom for retries / human-in-the-loop workbench calls happening
# in parallel with batched feed generation.
_GRADIUM_CONCURRENCY = 2
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_GRADIUM_CONCURRENCY)
    return _semaphore


def _get_client() -> GradiumClient:
    global _client
    if _client is None:
        if not settings.gradium_api_key:
            raise RuntimeError("GRADIUM_API_KEY not configured")
        _client = GradiumClient(api_key=settings.gradium_api_key)
    return _client


async def render_audio(
    card_id: str,
    tts_script: str,
    voice_id: str | None = None,
) -> str:
    """Synthesize narration to media/audio/{card_id}.wav, return public path.
    Pass `voice_id` to override the default; falls back to env / Wren catalog."""
    _AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _AUDIO_DIR / f"{card_id}.wav"

    # Precedence: explicit voice_id arg > GRADIUM_VOICE_ID env var > Wren catalog voice.
    resolved = voice_id or settings.gradium_voice_id
    if not resolved or resolved == "default":
        resolved = "RhI-l8fGE2DtXgXV"  # Wren

    setup: dict = {
        "model_name": settings.gradium_model_name,
        "voice_id": resolved,
        "output_format": "wav",
    }

    client = _get_client()
    async with _get_semaphore():
        result = await client.tts(setup=setup, text=tts_script)
    await asyncio.to_thread(out_path.write_bytes, result.raw_data)
    return f"/media/audio/{card_id}.wav"
