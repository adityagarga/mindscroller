"""One-shot: render 4 voice-avatar portraits with a unified style.

Outputs are saved to backend/media/img/_voice_<slug>.png and served at
/media/img/_voice_<slug>.png by the existing static mount. Same visual
treatment as the category illustrations so the onboarding feels cohesive.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.content.fal_client import render_image


# Shared style prefix — same warm cream backdrop + flat editorial vector style
# as the category images, but the subject is a stylized character silhouette
# instead of an abstract object.
VOICE_STYLE_PREFIX = (
    "Bold editorial illustration, flat geometric vector style, strong silhouette, "
    "warm cream off-white background (#f5efe4), single accent color, "
    "centered shoulders-up profile portrait, museum poster aesthetic, "
    "absolutely no text, no letters, no numbers, no digits, no symbols, "
    "no facial features (eyes/nose/mouth abstracted to negative space), "
    "no decorative ornament. Pure visual character study. Square 1:1. Subject: "
)

VOICES: dict[str, str] = {
    "rhyme_master":   "a confident performer silhouette wearing a wide-brim hat with one hand at the brim, punchy crimson red on cream",
    "the_cool_uncle": "a relaxed bearded figure silhouette with a tweed shoulder line, warm caramel brown on cream",
    "voice_of_god":   "a monumental robed figure silhouette with a high collar and looming presence, deep slate navy on cream",
    "rasta_rapper":   "a laid-back silhouette with long dreadlocks falling over the shoulders, sun-warmed terracotta orange on cream",
}


async def main() -> None:
    async def one(slug: str, subject: str) -> None:
        card_id = f"_voice_{slug}"
        try:
            path = await render_image(card_id, subject, style_prefix=VOICE_STYLE_PREFIX)
            print(f"OK  {slug:18s} -> {path}")
        except Exception as e:
            print(f"ERR {slug:18s} -> {e}")

    await asyncio.gather(*(one(slug, subj) for slug, subj in VOICES.items()))


if __name__ == "__main__":
    asyncio.run(main())
