"""Source of truth for content taxonomy and hook types.
Surfaced to the workbench UI via GET /api/workbench/taxonomy."""

from __future__ import annotations


# Category -> list of topics (leaves) the user selects from.
# Keep strings verbatim — they flow into the prompt as-is.
TAXONOMY: dict[str, list[str]] = {
    "Arts & culture": [
        "French Impressionists",
        "Parisian museums",
        "American movies",
        "American Blues/Jazz",
    ],
    "Literature": [
        "Shakespeare",
        "American novelists",
    ],
    "Economics": [
        "US monetary history",
        "French luxury industry",
    ],
    "General Knowledge": [
        "Science & nature oddities",
        "History's weird moments",
    ],
}


# Each hook type: a short tagline + an operational rule + a concrete example.
# The rule and example are embedded into the system prompt so the model can
# actually differentiate them. Edit here to tune.
HOOK_TYPE_SPECS: dict[str, dict[str, str]] = {
    "curiosity gap": {
        "tagline": "Withhold the payoff. Make them stay for the answer.",
        "rule": (
            "Open by establishing a specific mystery, anomaly, or unfinished puzzle — name the "
            "characters/place/year, but withhold the resolution. The middle hints, the payoff resolves."
        ),
        "example": (
            "'For thirty years, a single Picasso hung in a Norwegian fisherman's cottage. He didn't "
            "know what it was. The art world didn't know it existed. Then his grandson googled the "
            "signature…'"
        ),
    },
    "counterintuitive": {
        "tagline": "Lead with the thing that contradicts what they assume.",
        "rule": (
            "Open with a single sentence that flatly contradicts a common belief about the topic. "
            "The rest of the script defends the contradiction with evidence. No setup, no preamble — "
            "the first six words must already be the contradiction."
        ),
        "example": (
            "'Monet wasn't going blind when he painted the water lilies — he was seeing colors most "
            "humans physically can't see. After his cataract surgery, he ripped up canvases…'"
        ),
    },
    "stakes": {
        "tagline": "Open with what was on the line. Money, lives, reputation, power.",
        "rule": (
            "First sentence names a specific concrete consequence — money lost or made, a person ruined "
            "or saved, a war started, a career ended. Lead with the stakes BEFORE explaining the cause."
        ),
        "example": (
            "'In 1637, a single tulip bulb cost more than an Amsterdam canal house. Five months later "
            "you couldn't sell it for the price of an onion. What broke first — the market or the people?'"
        ),
    },
    "number": {
        "tagline": "Anchor in one specific, surprising number. The script explains why.",
        "rule": (
            "The first sentence contains one specific, surprising number — a date, a count, a price, a "
            "percentage — that demands an explanation. The script's job is to earn that number. Avoid "
            "round-number filler ('thousands of years'); use exact figures ('1,247 days')."
        ),
        "example": (
            "'Shakespeare invented at least 1,700 words still used today — including \"eyeball\", "
            "\"lonely\", and \"swagger\". He needed them because the English of 1590 literally couldn't "
            "describe what his characters felt.'"
        ),
    },
}

HOOK_TYPES: list[str] = list(HOOK_TYPE_SPECS.keys())


def is_valid(category: str, topic: str, hook_type: str) -> bool:
    return (
        category in TAXONOMY
        and topic in TAXONOMY[category]
        and hook_type in HOOK_TYPES
    )


def render_hook_type_block() -> str:
    """Render the per-hook-type rules + examples for embedding in the system prompt."""
    lines = ["HOOK TYPE RULES (the user picks one per card — match it exactly):"]
    for name, spec in HOOK_TYPE_SPECS.items():
        lines.append(f"\n[{name}] {spec['tagline']}")
        lines.append(f"  Rule: {spec['rule']}")
        lines.append(f"  Example opening: {spec['example']}")
    return "\n".join(lines)
