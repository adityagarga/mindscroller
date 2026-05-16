"""Deterministic next-batch planner.

Single source of truth for "what 4 cards should the agent generate next, given
the user's interaction history". Used by:
  - GET  /api/agent/stats          → to preview the next 4 in the dashboard
  - POST /api/agent/generate-batch → to actually generate them

Frontend mirrors this exact algorithm (see Dashboard.tsx / NextGenPreview.tsx)
so the live preview always matches what the FAB will produce.

Inputs are pre-fetched (no DB calls here) so the function is pure, testable,
and safely callable from concurrent request handlers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.content.topics import CATEGORIES, HOOK_TYPES, TAXONOMY
from app.content.voices import CUSTOM_VOICES


# ---------- Constants (mirror Dashboard.tsx) ----------

LIKE_WEIGHT = 10
DISLIKE_WEIGHT = 10


class PlanSlot(BaseModel):
    """One row in the next-gen bucket. Stable shape across stats/batch APIs."""
    rank: int
    category: str
    topic: str
    hook_type: str
    voice: str
    reason: str


def _affinity(watch_pct: float, likes: int, dislikes: int) -> float:
    """Same formula used in the dashboard. Clamped 0..100."""
    raw = watch_pct + LIKE_WEIGHT * likes - DISLIKE_WEIGHT * dislikes
    return max(0.0, min(100.0, raw))


def _rank_categories(stats: dict[str, Any]) -> list[dict[str, Any]]:
    """Decorate every category in stats with affinity + cards_seen and sort
    DESC. Ties broken by (more cards_seen, alphabetical)."""
    ranked: list[dict[str, Any]] = []
    for c in stats.get("categories", []):
        ranked.append({
            "name": c["name"],
            "affinity": _affinity(c["watch_percentage"], c["likes"], c["dislikes"]),
            "cards_seen": c["cards_seen"],
            "subtopics": c.get("subtopics", []),
        })
    ranked.sort(key=lambda c: (-c["affinity"], -c["cards_seen"], c["name"]))
    return ranked


def _pick_subtopic(category: str, sub_stats: list[dict[str, Any]]) -> str:
    """Highest-affinity subtopic within `category` that exists in TAXONOMY[cat].
    Falls back to the first TAXONOMY entry not yet seen, else TAXONOMY[cat][0]."""
    taxonomy_subs = TAXONOMY.get(category, [])
    if not taxonomy_subs:
        # No taxonomy entry for this category — shouldn't happen, but bail safely.
        return ""

    seen_names = {s["name"] for s in sub_stats}
    # Try the user's top-affinity subtopic that's still in our taxonomy.
    if sub_stats:
        scored = [
            (s["name"], _affinity(s["watch_percentage"], s["likes"], s["dislikes"]))
            for s in sub_stats
            if s["name"] in taxonomy_subs
        ]
        scored.sort(key=lambda x: -x[1])
        if scored and scored[0][1] > 0:
            return scored[0][0]

    # No signal → first untouched subtopic in the static taxonomy.
    for sub in taxonomy_subs:
        if sub not in seen_names:
            return sub
    return taxonomy_subs[0]


def _pick_categories(
    ranked: list[dict[str, Any]],
    category_prefs: list[str],
    n: int,
) -> list[dict[str, Any]]:
    """Take the top `n` categories with affinity > 0; fill with onboarding
    prefs (then global CATEGORIES) when the user has < n with signal."""
    picked: list[dict[str, Any]] = [c for c in ranked if c["affinity"] > 0][:n]
    picked_names = {c["name"] for c in picked}

    def empty_row(name: str) -> dict[str, Any]:
        return {"name": name, "affinity": 0.0, "cards_seen": 0, "subtopics": []}

    # Fill from onboarding category preferences.
    for name in category_prefs:
        if len(picked) >= n:
            break
        if name in picked_names or name not in CATEGORIES:
            continue
        picked.append(empty_row(name))
        picked_names.add(name)

    # Final fill from the global category list.
    for name in CATEGORIES:
        if len(picked) >= n:
            break
        if name in picked_names:
            continue
        picked.append(empty_row(name))
        picked_names.add(name)

    return picked[:n]


def _rank_hook_types(hook_affinity: list[dict[str, Any]]) -> list[str]:
    """Sort HOOK_TYPES by user affinity DESC, falling back to declaration order
    for hooks the user hasn't engaged with yet."""
    score: dict[str, float] = {h["bucket"]: float(h.get("score", 0)) for h in hook_affinity}
    return sorted(HOOK_TYPES, key=lambda h: (-score.get(h, 0.0), HOOK_TYPES.index(h)))


def _reason_for_slot(
    cat_row: dict[str, Any],
    hook_rank_idx: int,
    has_hook_signal: bool,
) -> str:
    if cat_row["affinity"] > 0:
        cat_part = f"your top category by affinity ({cat_row['affinity']:.0f})"
    else:
        cat_part = "from your onboarding picks (no signal yet)"

    if has_hook_signal:
        ordinal = ["#1", "#2", "#3", "#4"][min(hook_rank_idx, 3)]
        hook_part = f"hook = your {ordinal} hook type"
    else:
        hook_part = "hook cycling — no signal yet"

    return f"{cat_part}; {hook_part}"


def plan_next_batch(
    stats: dict[str, Any],
    hook_affinity: list[dict[str, Any]],
    category_prefs: list[str],
    voice_prefs: list[str],
    interaction_count: int,
    n: int = 4,
) -> list[PlanSlot]:
    """Deterministic plan for the next `n` cards.

    Inputs:
      stats:            db.watch_and_engagement_stats(user_id) result
      hook_affinity:    db.affinity_breakdown(user_id)['hook_type'] rows
      category_prefs:   user's onboarding category list (legacy 'topic_preferences')
      voice_prefs:      filtered voice name pool; falls back to CUSTOM_VOICES
      interaction_count: total interactions — used to seed voice cycle offset
                         so rotations don't reset between calls
      n:                slot count (default 4)
    """
    voice_pool = voice_prefs or list(CUSTOM_VOICES)
    has_hook_signal = bool(hook_affinity)

    ranked = _rank_categories(stats)
    picked = _pick_categories(ranked, category_prefs, n)
    hook_order = _rank_hook_types(hook_affinity)

    slots: list[PlanSlot] = []
    for i, cat_row in enumerate(picked):
        topic = _pick_subtopic(cat_row["name"], cat_row["subtopics"])
        # i-th best hook, cycling if HOOK_TYPES has fewer entries.
        hook = hook_order[i % len(hook_order)] if hook_order else HOOK_TYPES[0]
        voice = voice_pool[(interaction_count + i) % len(voice_pool)]
        slots.append(
            PlanSlot(
                rank=i + 1,
                category=cat_row["name"],
                topic=topic,
                hook_type=hook,
                voice=voice,
                reason=_reason_for_slot(cat_row, i, has_hook_signal),
            )
        )
    return slots
