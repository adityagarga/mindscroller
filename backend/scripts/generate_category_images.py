"""One-shot: render 8 onboarding category images with a unified style.

Outputs are saved to backend/media/img/_cat_<slug>.png and served at
/media/img/_cat_<slug>.png by the existing static mount.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.content.fal_client import render_image


# Shared visual contract: every category uses the same prefix so the eight
# images feel like a single set. Subjects are pure visual metaphors.
CATEGORY_STYLE_PREFIX = (
    "Bold editorial illustration, flat geometric vector style, strong silhouettes, "
    "warm cream off-white background (#f5efe4), single accent color object, "
    "centered composition, soft drop shadow, museum poster aesthetic, "
    "absolutely no text, no letters, no numbers, no digits, no symbols, "
    "no labels, no humans, no faces, no hands, no decorative ornament. "
    "Pure visual metaphor only. Portrait 3:4. Subject: "
)

CATEGORIES: dict[str, str] = {
    "arts": "a single bold paintbrush stroke arcing across the frame, deep crimson red on cream",
    "literature": "an open book silhouette with pages curling upward into a stylized flame, burnt orange on cream",
    "history": "a weathered classical column fragment standing alone, ochre and stone on cream",
    "science": "a single atom orbital diagram simplified into three intersecting ellipses, emerald green on cream",
    "tech": "an isometric stack of three abstract circuit blocks forming a tower, electric blue on cream",
    "economics": "a stylized coin balancing on edge casting a long shadow, mustard gold on cream",
    "psychology": "a profile silhouette of a head filled with concentric ring patterns, deep violet on cream",
    "philosophy": "a single perfect sphere resting on a flat plane with a long shadow, charcoal grey on cream",
}


async def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "media" / "img"
    out_dir.mkdir(parents=True, exist_ok=True)

    async def one(slug: str, subject: str) -> None:
        card_id = f"_cat_{slug}"
        try:
            path = await render_image(card_id, subject, style_prefix=CATEGORY_STYLE_PREFIX)
            print(f"OK  {slug:14s} -> {path}")
        except Exception as e:
            print(f"ERR {slug:14s} -> {e}")

    await asyncio.gather(*(one(slug, subj) for slug, subj in CATEGORIES.items()))


if __name__ == "__main__":
    asyncio.run(main())
