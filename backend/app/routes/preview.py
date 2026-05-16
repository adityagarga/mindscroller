"""Server-rendered HTML preview for prompt iteration in Phase 1.
This route exists so you can verify content quality with zero frontend code."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.db import client as db


router = APIRouter()


_PAGE = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>mindscroller · preview · {visual_hook}</title>
  <style>
    :root {{ color-scheme: dark; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: #0a0a0b; color: #e9e9ea; line-height: 1.5; }}
    .wrap {{ max-width: 480px; margin: 0 auto; padding: 32px 16px 80px; }}
    .meta {{ font-size: 11px; color: #888; margin-bottom: 12px; letter-spacing: 0.06em; text-transform: uppercase; }}
    .img-wrap {{ position: relative; aspect-ratio: 3/4; border-radius: 12px; overflow: hidden; background: #18181b; margin: 0 0 16px; }}
    .img-wrap img {{ width: 100%; height: 100%; object-fit: cover; }}
    .visual-hook {{
      position: absolute; inset: 0; display:flex; align-items:center; justify-content:center;
      padding: 20px; text-align: center;
      font-family: "Helvetica Neue", "Arial Black", Impact, system-ui, sans-serif;
      font-weight: 900; text-transform: uppercase;
      font-size: clamp(32px, 10vw, 56px);
      line-height: 0.92; letter-spacing: -0.02em;
      color: white;
      -webkit-text-stroke: 1px rgba(0,0,0,0.55);
      text-shadow: 0 0 1px rgba(0,0,0,0.95), 3px 3px 0 rgba(0,0,0,0.75);
      background: linear-gradient(180deg, rgba(0,0,0,0) 35%, rgba(0,0,0,0.5) 100%);
    }}
    audio {{ width: 100%; margin: 8px 0 20px; }}
    .script {{ font-size: 16px; padding: 14px 16px; background: #14141a; border-radius: 8px; }}
    details {{ margin-top: 24px; color: #888; font-size: 13px; }}
    details pre {{ white-space: pre-wrap; background: #121214; padding: 12px; border-radius: 6px; font-size: 12px; color: #aaa; }}
    nav {{ margin-bottom: 20px; font-size: 13px; }}
    nav a {{ color: #8b8bff; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="wrap">
    <nav><a href="/preview">← all cards</a></nav>
    <div class="meta">{category} · {topic} · {hook_type}</div>
    <div class="img-wrap">
      {image_block}
      <div class="visual-hook">{visual_hook}</div>
    </div>
    {audio_block}
    <div class="script">{script}</div>
    <details>
      <summary>image_prompt (LLM-authored, before STYLE_PREFIX)</summary>
      <pre>{image_prompt}</pre>
    </details>
  </div>
</body>
</html>
"""


_INDEX = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>mindscroller · all previews</title>
  <style>
    body {{ margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:#0a0a0b; color:#e9e9ea; }}
    .wrap {{ max-width: 880px; margin: 0 auto; padding: 32px 24px; }}
    h1 {{ font-size: 22px; margin: 0 0 24px; }}
    a.card {{ display:block; padding:16px; margin-bottom:12px; background:#14141a; border-radius:8px;
              color:#e9e9ea; text-decoration:none; border:1px solid #222; }}
    a.card:hover {{ border-color:#8b5cf6; }}
    .meta {{ font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.05em; }}
    .hook {{ font-size:16px; margin-top:4px; font-weight:600; }}
    .empty {{ color:#888; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>mindscroller · all previews</h1>
    {body}
  </div>
</body>
</html>
"""


@router.get("/preview", response_class=HTMLResponse)
async def preview_index() -> str:
    cards = db.list_cards(limit=200)
    if not cards:
        return _INDEX.format(body='<p class="empty">No cards yet. Use the <a href="/workbench" style="color:#8b8bff">workbench</a> to make some.</p>')
    items = []
    for c in cards:
        items.append(
            f'<a class="card" href="/preview/{c["id"]}">'
            f'<div class="meta">{_esc(c["category"])} · {_esc(c["topic"])} · {_esc(c["hook_type"])}</div>'
            f'<div class="hook">{_esc(c["visual_hook"])}</div>'
            f"</a>"
        )
    return _INDEX.format(body="\n".join(items))


@router.get("/preview/{card_id}", response_class=HTMLResponse)
async def preview_card(card_id: str) -> str:
    card = db.get_card(card_id)
    if not card:
        raise HTTPException(404, "card not found")
    return _PAGE.format(
        category=_esc(card["category"]),
        topic=_esc(card["topic"]),
        hook_type=_esc(card["hook_type"]),
        visual_hook=_esc(card["visual_hook"]),
        script=_esc(card["script"]),
        image_prompt=_esc(card["image_prompt"]),
        image_block=(f'<img src="{card["image_path"]}" alt="" />' if card.get("image_path") else ""),
        audio_block=(f'<audio controls src="{card["audio_path"]}"></audio>' if card.get("audio_path") else ""),
    )


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
