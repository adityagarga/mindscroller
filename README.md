# mindscroller

A TikTok-style learning feed. Every card is fully generated on demand:
a 40–55 word script written by **OpenAI**, an editorial-illustration image
rendered by **fal.ai**, and a personality-cloned voiceover from **Gradium**.
The feed adapts to your watch / like / dislike behavior via a deterministic
agent loop you can audit live in the dashboard.

Hackathon submission — local-first (SQLite + local media files, no cloud DB).

---

## Demo flow

1. **Onboarding step 1.** Pick categories you want to learn about (8 to
   choose from). Tap **Next**.
2. **Onboarding step 2.** Pick one or more **voices** for narration.
   Avatars are AI-generated; the wordmark below the voice list calls out
   that voice cloning is powered by Gradium.
3. **Splash.** While the splash plays, the backend generates **2 cards per
   selected category** in parallel and seeds your queue with matching
   historical cards behind them. The splash carries a large
   `POWERED BY OpenAI | fal.ai | Gradium` pill so the audience knows who's
   doing what.
4. **Feed.** Vertical scroll-snap. Each card auto-plays its narration when
   it crosses 70% visibility. The mute toggle (top-left) is global. Like /
   dislike / skip on the right rail records interactions.
5. **Dashboard (xl+ screens).** Watch the **ranked categories** reorder
   with a smooth FLIP animation as you interact. Each row shows a single
   `0 / 100` affinity score (formula below). Underneath, a live **NEXT 4
   — BASED ON YOU** preview shows the exact (category, topic, hook type,
   voice) the agent will produce next. Click **GENERATE NEW CONTENT** to
   make those 4 cards real; they splice in immediately after the card
   you're currently watching.

---

## Partner technologies

| Partner       | Used for                                          | Touchpoint                                         |
| ------------- | ------------------------------------------------- | -------------------------------------------------- |
| **OpenAI**    | Script + visual hook + image-prompt authoring     | `backend/app/content/openai_client.py`, model `gpt-4o-2024-08-06` (structured output via `response_format=CardDraft`) |
| **fal.ai**    | Image generation from the model-authored prompts  | `backend/app/content/fal_client.py`, model `fal-ai/flux/schnell`, portrait 3:4, retry with safety-checker fallback |
| **Gradium**   | TTS voice cloning (personality voices)            | `backend/app/content/gradium_client.py`, WebSocket TTS via the official `gradium` SDK, account-wide semaphore at 2 concurrent |

Every content card carries a `POWERED BY OpenAI | fal.ai | Gradium`
attribution pill above its chips, with the official logo for each partner
shipped in `frontend/public/partners/`.

### Voices

Defined in `backend/app/content/voices.py`. Four personality clones plus
the catalog default:

- **Wren** (catalog) — professional, polished baseline.
- **Rhyme Master** — punchy, rhythm-forward delivery.
- **The Cool Uncle** — warm, storytelling, smart-friend-at-a-bar tone.
- **Voice of God** — booming, authoritative, cinematic.
- **Rasta Rapper** — laid-back, inspirational, rapper cadence.

The onboarding voice picker lets the user choose one or more. The agent
cycles through those picks (round-robin, seeded by the user's total
interaction count) so the same voice never sits on every fresh card.

---

## Architecture

```
                  ┌────────────────────────────────────────────┐
                  │  OpenAI gpt-4o (structured output)         │
                  │  → CardDraft {                             │
                  │       visual_hook,                         │
                  │       script,                              │
                  │       image_prompt                         │
                  │     }                                      │
                  └─────────────────┬──────────────────────────┘
                                    │
                  ┌─────────────────┴──────────────────────────┐
                  ▼  asyncio.gather                            ▼
         ┌────────────────────┐                  ┌─────────────────────┐
         │ fal.ai             │                  │ Gradium TTS         │
         │ flux/schnell       │                  │ (WebSocket SDK)     │
         │ → PNG (3:4)        │                  │ → WAV               │
         └──────────┬─────────┘                  └──────────┬──────────┘
                    └────────────────┬──────────────────────┘
                                     ▼
                       ┌─────────────────────────────┐
                       │ SQLite cards row +          │
                       │ media/img + media/audio     │
                       └─────────────┬───────────────┘
                                     ▼
                       ┌─────────────────────────────┐
                       │ Vite + React feed UI        │
                       │ scroll-snap + Zustand store │
                       └─────────────────────────────┘
```

OpenAI is the **brain** — it authors the visual hook, the script, and the
image prompt in a single call. fal.ai and Gradium are dumb renderers that
consume the fields it produces.

---

## Setup

### Prerequisites

- **Python 3.13** (3.14 isn't yet supported by `pydantic-core`'s PyO3).
- **Node 20+** with `npm`.
- API keys for the three partners (set in `backend/.env`):

```
OPENAI_API_KEY=sk-...
FAL_KEY=...
GRADIUM_API_KEY=...
GRADIUM_VOICE_ID=RhI-l8fGE2DtXgXV   # Wren — used as the default catalog voice
```

A starter `.env.example` is committed; copy it to `.env` and fill in
the keys.

### Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env   # fill in OPENAI_API_KEY, FAL_KEY, GRADIUM_API_KEY
```

SQLite + media directories are created automatically on first boot —
no migration step needed.

### Frontend

```bash
cd frontend
npm install
```

---

## Run

Two terminals. The Vite dev server proxies `/api` and `/media` to the
backend so the browser sees them on a single origin.

**Terminal A — backend** (port 8000):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --reload-dir app --port 8000 --log-level info
```

`--reload-dir app` is important: without it `uvicorn` watches `.venv`
and loops forever whenever pip writes a cache file.

**Terminal B — frontend** (port 5173):

```bash
cd frontend
npm run dev
```

Then open:

- **App:** http://localhost:5173
- **Prompt workbench (dev tool):** http://localhost:8000/workbench
- **Card preview:** http://localhost:8000/preview

---

## Backend API

| Method · path                            | Purpose                                                                                       |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| `POST /api/users`                        | Onboard. Body: `{topic_preferences, voice_preferences, per_category_count, ...}`. Generates N cards × every category, cycling voices, then enqueues matching historical cards behind them. |
| `GET /api/feed?user_id=...`              | Paginated feed queue (filtered to the current `CARD_VERSION`).                                 |
| `POST /api/interactions`                 | Record `like | dislike | dismiss | view | complete | skip` with optional `view_duration_ms`.   |
| `POST /api/feed/sync`                    | Append any current-version cards not already in the user's queue. No generation.              |
| `GET /api/agent/state?user_id=...`       | Weighted affinity per dim (category/topic/hook/voice), interaction count, recent events.      |
| `POST /api/agent/brief`                  | Re-compute the LLM brief (OpenAI structured output) for the next-gen agent. Not used by the batch path; kept for future experimentation. |
| `POST /api/agent/generate-next`          | Single LLM-driven card from a brief.                                                          |
| `POST /api/agent/generate-batch`         | **Deterministic 4-card batch.** Uses the same planner the dashboard previews. Returns enqueued cards. |
| `GET /api/agent/stats?user_id=...&voice_preferences=…` | Per-category + per-subtopic stats and the live `next_plan.slots`. Drives the dashboard. |
| `GET /api/agent/voices/custom`           | List of personality voice names (for cycling).                                                |
| `GET /api/workbench/taxonomy`            | Categories, topics, hook types, voices for both the workbench and the app frontend.           |
| `POST /api/workbench/generate`           | Manually generate one card with optional prompt / voice overrides. Used by the workbench UI.  |
| `GET /preview`, `GET /preview/{card_id}` | Server-rendered card preview (for sharing / debugging).                                       |

Static media:

- `GET /media/img/<id>.png` — generated card image
- `GET /media/audio/<id>.wav` — generated narration
- `GET /partners/{openai.svg, fal.png, gradium-icon.png, gradium.svg}` — partner logos served by Vite from `frontend/public/`

---

## Adaptive recommendation — the algorithm

The dashboard's ranking and the batch endpoint's outputs are produced by
the same deterministic function: `backend/app/agent/planner.py:plan_next_batch`.
Identical logic is mirrored on the frontend in `Dashboard.tsx` and
`NextGenPreview.tsx` so what you preview is exactly what gets generated.

**Affinity score per (sub)category** (range 0–100):

```
affinity = clamp(watch_percentage + 10 × likes − 10 × dislikes, 0, 100)
```

Where `watch_percentage` is the user's share of total watch time
attributed to that bucket. The 10× weights are intentionally simple so
the demo audience can predict score changes in real time.

**Picking the next 4 slots:**

1. Rank ALL categories by affinity DESC. Ties: more `cards_seen`, then
   alphabetical. Assign ranks `#1..#N` (displayed in the dashboard).
2. Take the top 4 categories with affinity > 0. If fewer than 4 have
   any signal, fill from the user's onboarding category list, then from
   the global category list.
3. For each picked category, pick a **subtopic**:
   - Highest-affinity subtopic in `TAXONOMY[cat]`.
   - If no subtopic signal, the first untouched subtopic from the
     taxonomy.
4. Pick a **hook_type** per slot: sort `HOOK_TYPES` globally by user
   affinity (`db.affinity_breakdown(user_id)["hook_type"]`), slot `i`
   uses the i-th best. Cold start: declaration order.
5. Pick a **voice** per slot: round-robin through the user's onboarding
   voice picks, with the seed offset set to their total interaction
   count so rotations don't reset between calls.

Affinity-breakdown weights (different signal, used inside the LLM brief
prompt only — not by the planner):

```
like     +3.0
complete +1.0
view     +0.3
dislike  −3.0
skip     −1.0
dismiss  −2.0
```

---

## Frontend data model

`frontend/src/lib/api.ts` is the typed API surface. Key types:

- `Card` — full card row (id, category, topic, hook_type, visual_hook,
  script, image_path, audio_path, voice, version, created_at).
- `Stats` — per-category + per-subtopic watch / like / dislike +
  `next_plan: { slots: PlanSlot[] }`.
- `PlanSlot` — the four planned cards: `{rank, category, topic,
  hook_type, voice, reason}`.

Global state lives in `frontend/src/lib/store.ts` (Zustand):

- `userId`, `categoryPreferences`, `voicePreferences` — persisted to
  `localStorage` so a refresh keeps the session.
- `queue: Card[]`, `activeIndex` — feed + the card currently centered.
- `stats: Stats | null` — refreshed after every interaction.
- `generatingBatch`, `lastBatchError`, `freshlyGeneratedIds` — power
  the GENERATE NEW CONTENT button + the "just generated" badge.
- `generateBatch()` — calls `POST /api/agent/generate-batch`, splices
  the new cards into `queue[activeIndex + 1:]`, then refetches stats so
  the dashboard reorders.

---

## Project layout

```
backend/
├── app/
│   ├── main.py                       # FastAPI app, mounts /media, lifespan inits DB
│   ├── config.py                     # pydantic-settings env loader
│   ├── agent/
│   │   ├── brief.py                  # OpenAI structured-output brief (used by generate-next)
│   │   └── planner.py                # deterministic plan_next_batch (single source of truth)
│   ├── content/
│   │   ├── generator.py              # OpenAI → gather(fal, gradium) → SQLite orchestrator
│   │   ├── prompts.py                # SYSTEM_PROMPT + IMAGE_STYLE_PREFIX (edit me)
│   │   ├── schema.py                 # CardDraft pydantic model for OpenAI structured output
│   │   ├── topics.py                 # TAXONOMY + HOOK_TYPES + spec strings
│   │   ├── voices.py                 # VOICES + CUSTOM_VOICES + round-robin picker
│   │   ├── openai_client.py
│   │   ├── fal_client.py             # image render with retry + safety-checker fallback
│   │   └── gradium_client.py         # WebSocket TTS via the gradium SDK + 2-concurrency semaphore
│   ├── db/
│   │   ├── schema.sql
│   │   └── client.py                 # tiny SQLite helpers + idempotent _migrate
│   └── routes/
│       ├── agent.py                  # /api/agent/{state,brief,generate-next,generate-batch,stats,voices}
│       ├── feed.py                   # /api/users · /api/feed · /api/interactions · /api/feed/sync
│       ├── workbench.py              # /workbench UI + /api/workbench/{taxonomy,generate}
│       └── preview.py                # /preview/{id} card preview
├── scripts/
│   ├── generate_category_images.py   # one-shot: 8 onboarding category illustrations
│   ├── generate_voice_avatars.py     # one-shot: 4 voice character avatars
│   └── backfill_card_images.py       # re-renders any cards with NULL image_path
├── media/{img,audio}/                # generated PNG + WAV (gitignored)
└── mindscroller.db                   # SQLite single-file (gitignored)

frontend/
├── public/
│   └── partners/{openai.svg, fal.png, gradium-icon.png, gradium.svg}
├── src/
│   ├── main.tsx
│   ├── App.tsx                       # stage router: onboarding / warming / feed / error
│   ├── routes/
│   │   ├── Onboarding.tsx            # 2-step: categories then voices (avatars + Gradium attribution)
│   │   ├── Splash.tsx                # "generating your feed" loader with big PartnerStrip
│   │   └── Feed.tsx                  # scroll-snap container + IntersectionObserver
│   ├── components/
│   │   ├── Card.tsx                  # visual_hook overlay, script, partner strip, just-generated badge
│   │   ├── ActionBar.tsx             # like / dislike right rail
│   │   ├── AudioControls.tsx         # 56×56 global mute toggle
│   │   ├── Header.tsx                # MINDSCROLLER brand + card count
│   │   ├── Dashboard.tsx             # ranked stats, FLIP reorder, generate button
│   │   ├── NextGenPreview.tsx        # live "NEXT 4 — BASED ON YOU" panel
│   │   └── PartnerLogos.tsx          # OpenAI / fal.ai / Gradium pill (sm / md / lg sizes)
│   ├── hooks/
│   │   ├── useCardPlayback.ts        # IntersectionObserver-driven audio play/pause + 1.15× playbackRate
│   │   ├── useAudioUnlock.ts         # autoplay-policy first-gesture unlock
│   │   └── useFlipReorder.ts         # offsetTop-based FLIP animation for ranking changes
│   ├── lib/
│   │   ├── api.ts                    # typed fetch wrappers + Card / Stats / PlanSlot types
│   │   └── store.ts                  # Zustand: session, queue, stats, generateBatch
│   └── styles/index.css              # Tailwind + brutalist overlay + scroll-snap rules
├── vite.config.ts                    # /api and /media proxied to :8000
├── tailwind.config.js
└── package.json
```

---

## Reset state

To wipe all generated content and start fresh:

```bash
cd backend
rm mindscroller.db
rm -f media/img/*.png media/audio/*.wav
```

The DB schema and media directories are recreated on next backend boot.

Browser-side session state lives in `localStorage` under
`mindscroller.userId`, `mindscroller.categoryPreferences`,
`mindscroller.voicePreferences`, `mindscroller.muted`. Clear them via
DevTools → Application → Local Storage to force re-onboarding without
deleting the DB.

---

## Design notes

- **The visual hook is HTML, not pixels.** Diffusion models render text,
  numbers, equations, and symbols as garbled glyph soup. The system
  prompt and `IMAGE_STYLE_PREFIX` strictly ban all glyphs from the
  generated image; the actual hook text is overlaid in CSS afterward in
  the heaviest available sans (Helvetica Neue Black → Arial Black →
  Impact fallback), with a hard 3px offset shadow.
- **Image style:** bold editorial illustration, flat vector, strong
  silhouettes, limited 2–3 color palette, object-anchored visual
  metaphors. Pure-Bauhaus geometric primitives were tried and rejected —
  illustrative reads better as thumbnail art.
- **Card version stamping:** every prompt change bumps `CARD_VERSION` in
  `backend/app/content/prompts.py`. Older cards stay archived in the DB
  but are filtered out of every feed query — clean rollback if a prompt
  iteration regresses.
- **Narration playback:** muted by default in localStorage flag,
  IntersectionObserver-driven (one audio playing at a time, paused +
  reset to 0 on exit), browser `playbackRate = 1.15` for tighter pacing
  without re-rendering TTS.
- **Dashboard reorder:** FLIP animation keyed by `offsetTop` (not
  `getBoundingClientRect().top`) so scrolling the list doesn't trigger
  the animation — only an actual rank shift does.

---

## License

MIT. Hackathon submission, use as you like.
