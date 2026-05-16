"""LLM-driven 'next card brief' agent.

Given a user's affinity scores + last N interactions, ask gpt-4o-mini to
propose what to make next: a category (must be in TAXONOMY), a topic (can
be a NEW subtopic — the agent expands the taxonomy), a hook_type, an
angle string (free-form steer for the script writer), and the reasoning.

Voice is NOT picked here — generation cycles through custom voices on
its own. (User instruction: brief shouldn't dictate voice.)

Model: gpt-4o-mini-2024-07-18. ~$0.0002 per brief, fast (<1s).
"""

from __future__ import annotations

from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.content.topics import CATEGORIES, HOOK_TYPES, TAXONOMY
from app.db import client as db


_client: AsyncOpenAI | None = None
_BRIEF_MODEL = "gpt-4o-mini-2024-07-18"


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


class Brief(BaseModel):
    category: str = Field(description="MUST be exactly one of the allowed category strings.")
    topic: str = Field(
        description=(
            "Subtopic within the category. CAN be a new subtopic not yet in the taxonomy — "
            "if the user's behavior suggests an angle the existing leaves don't cover, propose one. "
            "Specific and noun-phrase (e.g. 'Lost Soviet space probes', 'The grammar of haiku' — "
            "NOT 'something interesting about X')."
        )
    )
    hook_type: Literal["curiosity gap", "counterintuitive", "stakes", "number"]
    angle: str = Field(
        description=(
            "1-2 sentences telling the downstream script writer how to angle the card — "
            "what twist, what level, what tone. Concrete and specific."
        )
    )
    reasoning: str = Field(
        description=(
            "1-2 sentences explaining WHY this brief, anchored in the user's behavior. "
            "Reference specific interactions or affinity scores."
        )
    )
    is_new_topic: bool = Field(
        description="True if `topic` is NOT already in the static TAXONOMY for `category`."
    )


_SYSTEM_PROMPT = """\
You are a recommendation agent for a TikTok-style learning app.

Given a user's interaction history and their current affinity scores, you propose
the NEXT educational card to generate for them.

Rules:
- `category` MUST be exactly one of the provided allowed categories.
- `topic` should usually be from the existing subtopics for that category, BUT you
  can propose a NEW subtopic when the user's recent behavior reveals an angle the
  existing leaves don't cover. Set `is_new_topic: true` when you do.
- Lean into the user's positives. If a topic / hook_type has high affinity, give
  them more of that vein (with variation in subject). If a topic has strong
  negative affinity, avoid it.
- Don't repeat the exact same subtopic the user just saw — give them adjacent
  ground.
- `hook_type` matches the user's strongest hook affinity, unless that hook has
  already been used heavily in recent cards (in which case rotate).
- `angle` is concrete. Reference specific people, places, numbers, dates,
  paradoxes, mechanisms. Avoid generic phrasings like "a fascinating story".
- `reasoning` references the user's actual signal — name the affinity numbers
  or interactions you're acting on.

If the user has zero interactions, pick the most universally engaging combination
from their declared category preferences.
"""


def _user_prompt(
    user_id: str,
    category_preferences: list[str],
    affinity: dict,
    recent: list[dict],
    discovered: list[dict],
) -> str:
    cats_block = "\n".join(
        f"  • {cat}: {', '.join(TAXONOMY[cat])}" for cat in CATEGORIES
    )
    disc_block = (
        "\n".join(f"  • [{d['category']}] {d['topic']}" for d in discovered[:20])
        or "  (none yet)"
    )
    prefs = ", ".join(category_preferences) if category_preferences else "(none — pick anything)"

    def top(dim: str, n: int = 5) -> str:
        rows = affinity.get(dim, [])[:n]
        if not rows:
            return "  (no signal yet)"
        return "\n".join(
            f"  • {r['bucket']}: score={r['score']:+.1f}  "
            f"(likes={r['likes']}, dislikes={r['dislikes']}, n={r['interactions']})"
            for r in rows
        )

    recent_block = (
        "\n".join(
            f"  {i+1}. [{r['event_type']}] {r['category']} · {r['topic']} · {r['hook_type']} · "
            f"hook='{r['visual_hook']}'"
            for i, r in enumerate(recent[:15])
        )
        or "  (no interactions yet — user just onboarded)"
    )

    return f"""\
USER ID: {user_id}
User's category preferences (declared in onboarding): {prefs}

ALLOWED CATEGORIES (must pick from this list exactly):
{cats_block}

DISCOVERED SUBTOPICS already added by previous briefs (avoid duplicating exactly):
{disc_block}

CURRENT AFFINITY SCORES:
Top categories:
{top('category')}

Top topics:
{top('topic')}

Hook type affinity:
{top('hook_type', n=4)}

LAST 15 INTERACTIONS (most recent first):
{recent_block}

Propose the next card."""


async def generate_brief(
    user_id: str,
    category_preferences: list[str] | None = None,
) -> Brief:
    """Compute affinity, fetch recent interactions, ask gpt-4o-mini for a brief."""
    affinity = db.affinity_breakdown(user_id)
    recent = db.recent_interactions_with_cards(user_id, limit=15)
    discovered = db.list_discovered_topics()

    client = _get_client()
    resp = await client.beta.chat.completions.parse(
        model=_BRIEF_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _user_prompt(
                    user_id,
                    category_preferences or [],
                    affinity,
                    recent,
                    discovered,
                ),
            },
        ],
        response_format=Brief,
        temperature=0.7,
        max_completion_tokens=600,
    )
    brief = resp.choices[0].message.parsed
    if brief is None:
        raise RuntimeError("brief LLM returned no parsed output")

    # Defensive: category MUST be in TAXONOMY. If the model made one up, snap to
    # the closest declared preference (or the first allowed category).
    if brief.category not in TAXONOMY:
        fallback = (category_preferences or CATEGORIES)[0]
        brief = brief.model_copy(update={"category": fallback})

    # Re-compute is_new_topic server-side so the UI badge can't be gamed.
    existing_topics = set(TAXONOMY.get(brief.category, []))
    brief = brief.model_copy(update={"is_new_topic": brief.topic not in existing_topics})
    return brief
