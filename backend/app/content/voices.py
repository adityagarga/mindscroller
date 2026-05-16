"""Available Gradium voices for content generation.

Each entry maps a human-readable name to its Gradium voice_id. The workbench
exposes these as a dropdown so you can pick voice + content together; the chosen
voice name is persisted on the card row for A/B comparison later.
"""

from __future__ import annotations

from typing import TypedDict


class VoiceSpec(TypedDict):
    voice_id: str
    description: str


# Edit here to add/remove voices. Names must be unique.
VOICES: dict[str, VoiceSpec] = {
    "Wren": {
        "voice_id": "RhI-l8fGE2DtXgXV",
        "description": "Default — professional, deep, polished catalog voice.",
    },
    "Rhyme Master": {
        "voice_id": "jGJq0mGTIWVpH6JS",
        "description": "Custom clone — punchy, rhythm-forward delivery.",
    },
    "The Cool Uncle": {
        "voice_id": "-LyoTDj6fcljWW4d",
        "description": "Custom clone — warm, storytelling, smart-friend-at-a-bar tone.",
    },
    "Voice of God": {
        "voice_id": "5iYY7J05fLbYv40N",
        "description": "Custom clone — booming, authoritative, cinematic.",
    },
    "Rasta Rapper": {
        "voice_id": "bVJeC983mMmdyByR",
        "description": "Custom clone — laid-back, inspirational, rapper cadence.",
    },
}

DEFAULT_VOICE = "Wren"

# Voices used for live-feed generation (agent-driven). Excludes the catalog
# Wren so personality voices get airtime in the demo. Order = round-robin order.
CUSTOM_VOICES: list[str] = [
    "Rhyme Master",
    "The Cool Uncle",
    "Voice of God",
    "Rasta Rapper",
]


def pick_custom_voice(seed: int) -> str:
    """Deterministic round-robin over CUSTOM_VOICES. `seed` is typically the
    user's running interaction count so consecutive generations cycle through
    all personality voices instead of repeating."""
    if not CUSTOM_VOICES:
        return DEFAULT_VOICE
    return CUSTOM_VOICES[seed % len(CUSTOM_VOICES)]


def voice_id_for(name: str | None) -> str:
    """Resolve a friendly name to a Gradium voice_id. Falls back to DEFAULT_VOICE
    if the name isn't recognized, so a missing/stale workbench selection never breaks generation."""
    if name and name in VOICES:
        return VOICES[name]["voice_id"]
    return VOICES[DEFAULT_VOICE]["voice_id"]
