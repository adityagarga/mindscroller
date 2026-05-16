# mindscroller

A TikTok-style learning feed. Bite-sized, AI-generated educational cards (10-20 second scripts + AI-illustrated background + AI voiceover) that scroll vertically and adapt to your taste.

Built for a hackathon — local-first (SQLite + local media files, no cloud DB).

## Status

- [x] **Phase 1** — content generation engine (OpenAI → fal.ai → Gradium → SQLite).
- [x] **Phase 1.5** — interactive prompt workbench at `/workbench`.
- [x] **Phase 2** — vertical-scroll feed UI (Vite + React + TS + Tailwind + Zustand).
- [ ] **Phase 3** — adaptive recommendation engine.

## What it generates

Each card has:

| Field         | Description                                                      |
| ------------- | ---------------------------------------------------------------- |
| `visual_hook` | 3-7 word text overlay, rendered in brutalist all-caps on the image |
| `script`      | 40-55 word spoken narration (10-20 seconds, Hook → Twist → Payoff) |
| `image_prompt`| AI-authored visual metaphor → rendered by fal.ai as a PNG          |
| `audio`       | Gradium TTS of the script → WAV                                   |

The text model (OpenAI `gpt-4o`) is the brain — it authors the visual hook, the script, **and** the image prompt in a single structured-output call. fal.ai and Gradium are dumb renderers that consume the fields it produces. They never decide what the card is about.

```
                 ┌──────────────────────────────────┐
                 │ OpenAI gpt-4o (structured output)│
                 │ → CardDraft {                    │
                 │     visual_hook,                 │
                 │     script,                      │
                 │     image_prompt                 │
                 │   }                              │
                 └──────────────┬───────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼ asyncio.gather                ▼
        ┌────────────────┐             ┌────────────────┐
        │ fal.ai         │             │ Gradium TTS    │
        │ image_prompt   │             │ script         │
        │ → PNG          │             │ → WAV          │
        └────────┬───────┘             └────────┬───────┘
                 └──────────────┬───────────────┘
                                ▼
                  ┌─────────────────────────┐
                  │ SQLite cards row +      │
                  │ files under media/      │
                  └─────────────────────────┘
```

## Taxonomy

Cards are organized by `category → topic → hook_type`. Configured in `backend/app/content/topics.py`.

| Category          | Topics                                                            |
| ----------------- | ----------------------------------------------------------------- |
| Arts & culture    | French Impressionists, Parisian museums, American movies, American Blues/Jazz |
| Literature        | Shakespeare, American novelists                                   |
| Economics         | US monetary history, French luxury industry                       |
| General Knowledge | Science & nature oddities, History's weird moments                |

**Hook types** (controls the script's opening style):

- **curiosity gap** — withhold the payoff, make them stay for the answer
- **counterintuitive** — open with a claim that contradicts what they assume
- **stakes** — open with what was on the line (money, lives, reputation)
- **number** — anchor in one specific, surprising number; the script earns it

Each hook type has a tagline + operational rule + a concrete worked example, all embedded into the system prompt so the model differentiates them sharply.

## The prompt workbench

`http://localhost:8000/workbench` — the developer tool for iterating on prompts.

- Cascading dropdowns: **category → topic → hook type** (+ a Randomize button)
- Live-editable **system prompt** and **image style prefix** textareas (auto-saved to localStorage)
- Hook-type hint panel under the dropdown — shows the rule + example for whichever hook type is selected
- Result panel renders the card TikTok-style: brutalist visual hook overlaid on the image, plus `<audio>` and the script
- Session history strip — click any past card to re-view
- Skip-audio / skip-image toggles for faster, cheaper iteration

When you find prompts you like in the workbench, paste them into `backend/app/content/prompts.py` to make them the new defaults.

## Setup

Requires Python 3.13 (3.14 not yet supported by pydantic-core's PyO3).

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env   # then fill in OPENAI_API_KEY, FAL_KEY, GRADIUM_API_KEY
```

`.env` (gitignored):

```
OPENAI_API_KEY=sk-...
FAL_KEY=...
GRADIUM_API_KEY=...
GRADIUM_VOICE_ID=RhI-l8fGE2DtXgXV   # Wren (catalog voice, deep + professional)
```

## Run

Two terminals — backend on `:8000`, frontend on `:5173`.

**Terminal A — backend:**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --reload-dir app --port 8000 --log-level info
```

`--reload-dir app` is critical: without it, uvicorn watches `.venv` and reloads itself whenever pip writes there.

**Terminal B — frontend:**

```bash
cd frontend
npm install   # first run only
npm run dev
```

Then open **http://localhost:5173** for the actual app (the TikTok-style feed). The Vite dev server proxies `/api` and `/media` to the backend, so they share an origin from the browser's perspective.

The developer workbench remains at **http://localhost:8000/workbench**.

Routes (backend):

- `GET /` — service index
- `GET /preview`, `GET /preview/{id}` — server-rendered card previews
- `GET /workbench` — prompt iteration UI
- `GET /api/workbench/taxonomy` — taxonomy + hook type specs
- `POST /api/workbench/generate` — generate a card with optional prompt overrides
- `POST /api/users` — create anonymous user, generate 5 cold-start cards in parallel
- `GET /api/feed?user_id=...` — paginated feed queue for a user
- `POST /api/interactions` — record `{like, dislike, dismiss, view, complete, skip}`
- `POST /api/feed/refill` — fire-and-forget background queue top-up

## Phase 2 — what the app actually does

1. **Onboarding:** pick topics (multi-select chips grouped by category). Tap Start.
2. **Cold start:** `POST /api/users` generates 5 cards in parallel from your picks. Splash screen: "warming up your feed" (~8-12s).
3. **Feed:** vertical scroll-snap. The `visual_hook` overlays the image in brutalist all-caps. The `script` and meta chips sit in a bottom panel. Audio auto-plays when a card crosses 70% visibility; pauses + resets when it leaves. Only one audio is ever playing.
4. **Actions:** right rail has 💗 like / 👎 dislike / ✕ skip. Each fires `POST /api/interactions`. Skip auto-scrolls to the next card.
5. **Background refill:** when you're 3 cards from the end, the app fires `POST /api/feed/refill` — backend generates 3 more cards (currently sampling randomly from your topic preferences; Phase 3 will make this adaptive).
6. **Session:** anonymous UUID lives in `localStorage` (`mindscroller.userId`). Visit the app again from the same browser and you pick up where you left off.

## Reset state

```bash
cd backend
rm mindscroller.db
rm -f media/img/*.png media/audio/*.wav
```

The DB schema is recreated on startup.

## Project layout

```
backend/
├── app/
│   ├── main.py                # FastAPI app, mounts /media, lifespan inits DB
│   ├── config.py              # env settings via pydantic-settings
│   ├── content/
│   │   ├── generator.py       # orchestrator: OpenAI → gather(fal, gradium) → SQLite
│   │   ├── prompts.py         # SYSTEM_PROMPT + IMAGE_STYLE_PREFIX (edit me)
│   │   ├── schema.py          # CardDraft pydantic model (OpenAI structured output)
│   │   ├── topics.py          # taxonomy + hook type specs (source of truth)
│   │   ├── openai_client.py
│   │   ├── fal_client.py
│   │   └── gradium_client.py  # uses official gradium SDK (WebSocket TTS)
│   ├── db/
│   │   ├── schema.sql
│   │   └── client.py
│   └── routes/
│       ├── workbench.py       # GET /workbench + /api/workbench/{defaults,taxonomy,generate}
│       ├── feed.py            # POST /api/users · GET /api/feed · POST /api/interactions · POST /api/feed/refill
│       └── preview.py         # GET /preview, /preview/{id}
├── media/{img,audio}/         # generated PNG + WAV (gitignored)
└── mindscroller.db            # SQLite single-file (gitignored)

frontend/
├── src/
│   ├── main.tsx               # React entry
│   ├── App.tsx                # stage router: onboarding / warming / feed / error
│   ├── routes/
│   │   ├── Onboarding.tsx     # topic chip picker
│   │   ├── Splash.tsx         # "warming up your feed" loader
│   │   └── Feed.tsx           # scroll-snap container + IntersectionObserver
│   ├── components/
│   │   ├── Card.tsx           # full-viewport card with brutalist hook overlay
│   │   └── ActionBar.tsx      # like / dislike / skip right rail
│   ├── hooks/
│   │   └── useCardPlayback.ts # audio play/pause on viewport entry
│   ├── lib/
│   │   ├── api.ts             # typed fetch wrappers
│   │   └── store.ts           # Zustand store + session/queue/refill
│   └── styles/index.css       # Tailwind + brutalist overlay class + scroll-snap rules
├── vite.config.ts             # /api and /media proxied to :8000
├── tailwind.config.js
└── package.json
```

## Design notes

- **Image style:** bold editorial illustration, flat vector, strong silhouettes, limited 2-3 color palette. Object-anchored visual metaphors (e.g. a tulip on a scale for tulip mania, an elliptic-curve lattice for Fermat). Pure-Bauhaus geometric primitives were tried and rejected — the more illustrative direction reads better.
- **Visual hook overlay:** brutalist all-caps in the heaviest available sans (Helvetica Neue Black → Arial Black → Impact fallback chain), tight tracking, hard 3px offset shadow.
- **No text inside the image** — diffusion models render text/numbers/equations as garbled glyph soup. The actual text is overlaid in HTML/CSS on top. The system prompt and `IMAGE_STYLE_PREFIX` both enforce this strictly (belt and suspenders).

## License

MIT. Hackathon project, use as you like.
