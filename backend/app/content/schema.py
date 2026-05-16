from pydantic import BaseModel, Field


class CardDraft(BaseModel):
    """OpenAI structured-output schema for one TikTok-style educational card.

    Two outward-facing fields the user spec'd (visual_hook, script) plus one
    internal field (image_prompt) that drives fal.ai. The image_prompt is generated
    in the same call so it stays tied to the script's specific content."""

    visual_hook: str = Field(
        description=(
            "Text overlay shown on the card. 3-7 words MAX. Must NOT repeat the spoken hook verbatim. "
            "Sentence case, with ALL CAPS only on emphasis words. No emojis."
        )
    )
    script: str = Field(
        description=(
            "Spoken narration. 40-55 words (10-20 seconds spoken). Hook → Twist → Payoff. "
            "Concrete details (real names, dates, numbers). Smart-friend-at-a-bar tone, not lecturer. "
            "End with a reframe or open-loop question."
        )
    )
    image_prompt: str = Field(
        description=(
            "Pure visual metaphor for an AI image model (Flux). 3 to 6 short phrases. "
            "NO text, letters, numbers, equations, names, or labels — diffusion models render those as "
            "garbled glyph soup. Use shapes, silhouettes, color, composition. Will be prepended with a "
            "strict style preamble — do not include style words yourself."
        )
    )
