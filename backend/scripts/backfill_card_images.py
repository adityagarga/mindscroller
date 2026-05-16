"""Backfill missing card images.

Finds rows in `cards` where image_path is NULL/empty, re-runs render_image
using the stored image_prompt, and updates the row. Parallelised with a
small concurrency cap to avoid hammering fal.

Run:
    cd backend && .venv/bin/python -m scripts.backfill_card_images
"""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DB_PATH
from app.content.fal_client import render_image


# Cap concurrent fal calls. Image gen is light on Gradium so we can push this
# higher than the audio semaphore (2). 4 keeps us well under fal's rate limit
# while still finishing 169 cards in a few minutes.
CONCURRENCY = 4


async def _backfill_one(
    sem: asyncio.Semaphore,
    card_id: str,
    image_prompt: str,
) -> tuple[str, str | None, str | None]:
    """Render an image for one card. Returns (card_id, public_path, error)."""
    async with sem:
        try:
            path = await render_image(card_id, image_prompt)
            return card_id, path, None
        except Exception as e:  # noqa: BLE001
            return card_id, None, f"{type(e).__name__}: {e}"


def _fetch_missing() -> list[tuple[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT id, image_prompt
              FROM cards
             WHERE (image_path IS NULL OR image_path = '')
               AND image_prompt IS NOT NULL
               AND image_prompt != ''
            """
        ).fetchall()
    return rows


def _update_path(card_id: str, image_path: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE cards SET image_path = ? WHERE id = ?",
            (image_path, card_id),
        )


async def main() -> None:
    rows = _fetch_missing()
    if not rows:
        print("No cards missing images. Nothing to do.")
        return

    print(f"Backfilling {len(rows)} cards (concurrency={CONCURRENCY})...\n")
    sem = asyncio.Semaphore(CONCURRENCY)

    coros = [_backfill_one(sem, cid, prompt) for cid, prompt in rows]

    done = 0
    ok = 0
    for fut in asyncio.as_completed(coros):
        card_id, path, err = await fut
        done += 1
        if path:
            _update_path(card_id, path)
            ok += 1
            print(f"[{done:3d}/{len(rows)}] OK  {card_id[:8]} -> {path}")
        else:
            print(f"[{done:3d}/{len(rows)}] ERR {card_id[:8]} | {err}")

    print()
    print(f"Done. {ok}/{len(rows)} images backfilled.")
    if ok < len(rows):
        print(f"     {len(rows) - ok} still missing — re-run to retry.")


if __name__ == "__main__":
    asyncio.run(main())
