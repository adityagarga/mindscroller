from openai import AsyncOpenAI

from app.config import settings
from app.content.prompts import SYSTEM_PROMPT, user_prompt
from app.content.schema import CardDraft


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_card_draft(
    category: str,
    topic: str,
    hook_type: str,
    system_prompt: str | None = None,
) -> CardDraft:
    """Single OpenAI call with structured outputs → CardDraft (visual_hook + script + image_prompt).
    Pass `system_prompt` to override the default SYSTEM_PROMPT (used by the workbench)."""
    client = _get_client()
    resp = await client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(category, topic, hook_type)},
        ],
        response_format=CardDraft,
        temperature=0.9,
        max_completion_tokens=1200,
    )
    draft = resp.choices[0].message.parsed
    if draft is None:
        raise RuntimeError(f"OpenAI returned no parsed draft for topic={topic!r}")
    return draft
