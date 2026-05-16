import { useEffect, useState } from "react";
import { api, type Taxonomy } from "../lib/api";
import { useApp } from "../lib/store";

// Keep keys in sync with backend TAXONOMY top-level names. `slug` selects the
// pre-rendered illustration in /media/img/_cat_<slug>.png; `accent` tints it.
const CATEGORY_STYLE: Record<string, { slug: string; accent: string }> = {
  "Arts & culture": { slug: "arts", accent: "from-rose-900/70 to-rose-950/90" },
  "Literature": { slug: "literature", accent: "from-orange-900/70 to-amber-950/90" },
  "History": { slug: "history", accent: "from-amber-900/70 to-stone-950/90" },
  "Science & Nature": { slug: "science", accent: "from-emerald-900/70 to-teal-950/90" },
  "Tech & Computing": { slug: "tech", accent: "from-sky-900/70 to-indigo-950/90" },
  "Economics & money": { slug: "economics", accent: "from-yellow-900/70 to-lime-950/90" },
  "Psychology & behavior": { slug: "psychology", accent: "from-violet-900/70 to-purple-950/90" },
  "Philosophy & big ideas": { slug: "philosophy", accent: "from-slate-800/70 to-slate-950/90" },
};

// Voice metadata. `slug` selects the pre-rendered avatar in
// /media/img/_voice_<slug>.png (generated once by
// backend/scripts/generate_voice_avatars.py). The backend resolves the name
// to a Gradium voice_id. "Wren" (catalog default) is excluded so users pick
// from the personality clones; matches backend CUSTOM_VOICES.
const VOICE_STYLE: Record<string, { slug: string; tag: string; accent: string }> = {
  "Rhyme Master":   { slug: "rhyme_master",   tag: "Punchy, rhythm-forward", accent: "ring-rose-400/60" },
  "The Cool Uncle": { slug: "the_cool_uncle", tag: "Warm, storytelling",     accent: "ring-amber-400/60" },
  "Voice of God":   { slug: "voice_of_god",   tag: "Booming, cinematic",     accent: "ring-sky-400/60" },
  "Rasta Rapper":   { slug: "rasta_rapper",   tag: "Laid-back, inspirational", accent: "ring-orange-400/60" },
};

function Logo({ className = "" }: { className?: string }) {
  // Bold square mark — a tight square spiral. Evokes "mind" (brain folds /
  // thought coils) and "scroll" (winding feed) in a single silhouette.
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <rect x="0" y="0" width="64" height="64" rx="14" fill="white" />
      <path
        d="M32 32 L32 20 L44 20 L44 44 L20 44 L20 14 L50 14"
        stroke="#0a0a0b"
        strokeWidth="6"
        strokeLinecap="square"
        strokeLinejoin="miter"
        fill="none"
      />
    </svg>
  );
}

type Step = "categories" | "voices";

export function Onboarding() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [step, setStep] = useState<Step>("categories");
  const [selectedCats, setSelectedCats] = useState<Set<string>>(new Set());
  const [selectedVoices, setSelectedVoices] = useState<Set<string>>(new Set());
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const beginColdStart = useApp((s) => s.beginColdStart);

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch((e) => setLoadErr(String(e?.message ?? e)));
  }, []);

  function toggleSet<T>(setState: (u: (prev: Set<T>) => Set<T>) => void, item: T) {
    setState((prev) => {
      const next = new Set(prev);
      if (next.has(item)) next.delete(item);
      else next.add(item);
      return next;
    });
  }

  function next() {
    if (selectedCats.size === 0) return;
    setStep("voices");
  }

  function back() {
    setStep("categories");
  }

  function start() {
    if (selectedCats.size === 0 || selectedVoices.size === 0) return;
    beginColdStart(Array.from(selectedCats), Array.from(selectedVoices));
  }

  if (loadErr) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center p-6">
        <div className="text-red-400 max-w-md text-center">
          Backend unreachable.
          <div className="text-sm text-muted mt-2">{loadErr}</div>
          <div className="mt-4 text-xs text-muted">
            Start it with:{" "}
            <code className="text-white">uvicorn app.main:app --reload --reload-dir app --port 8000</code>
          </div>
        </div>
      </div>
    );
  }

  if (!taxonomy) {
    return <div className="min-h-[100dvh] flex items-center justify-center text-muted">loading…</div>;
  }

  const categories = Object.keys(taxonomy.taxonomy);
  // Personality voices only — the backend's CUSTOM_VOICES list. If the
  // taxonomy ships voices, intersect; otherwise fall back to our local table.
  const allVoiceNames = Object.keys(VOICE_STYLE);
  const voices = taxonomy.voices
    ? allVoiceNames.filter((n) => taxonomy.voices && n in taxonomy.voices)
    : allVoiceNames;

  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden">
      {/* Brand */}
      <div className="px-4 sm:px-5 pt-[max(12px,env(safe-area-inset-top))] pb-1 flex items-center gap-2 sm:gap-3 min-w-0">
        <Logo className="w-[10vw] h-[10vw] sm:w-[clamp(40px,7vw,64px)] sm:h-[clamp(40px,7vw,64px)] max-w-[64px] max-h-[64px] min-w-[36px] min-h-[36px] shrink-0" />
        <div className="brutal-overlay text-white text-[8.5vw] sm:text-[clamp(44px,7vw,68px)] leading-none tracking-tight min-w-0">
          MINDSCROLLER
        </div>
      </div>

      {/* Step indicator + title */}
      <div className="px-4 sm:px-5 pt-2 flex items-center gap-2">
        <StepDot active={step === "categories"} done={step !== "categories"} label="1" />
        <div className="h-px w-6 bg-white/20" />
        <StepDot active={step === "voices"} label="2" />
      </div>

      {step === "categories" ? (
        <CategoryStep
          categories={categories}
          selected={selectedCats}
          onToggle={(c) => toggleSet(setSelectedCats, c)}
          onNext={next}
        />
      ) : (
        <VoiceStep
          voices={voices}
          selected={selectedVoices}
          onToggle={(v) => toggleSet(setSelectedVoices, v)}
          onBack={back}
          onStart={start}
          catCount={selectedCats.size}
        />
      )}
    </div>
  );
}

function StepDot({ active, done, label }: { active: boolean; done?: boolean; label: string }) {
  return (
    <div
      className={
        "w-6 h-6 rounded-full grid place-items-center text-[11px] font-bold transition-colors " +
        (active
          ? "bg-white text-ink"
          : done
            ? "bg-white/40 text-ink"
            : "bg-white/10 text-white/40")
      }
    >
      {done ? "✓" : label}
    </div>
  );
}

function CategoryStep({
  categories,
  selected,
  onToggle,
  onNext,
}: {
  categories: string[];
  selected: Set<string>;
  onToggle: (c: string) => void;
  onNext: () => void;
}) {
  return (
    <>
      <h1 className="px-4 sm:px-5 pt-2 brutal-overlay text-[6.4vw] sm:text-[clamp(32px,5.5vw,46px)] leading-[1] text-white whitespace-nowrap">
        what do you want to learn?
      </h1>
      <p className="px-4 sm:px-5 pt-1.5 pb-2 text-muted text-[3.8vw] sm:text-[clamp(15px,2vw,20px)] leading-snug">
        Mindscroller will expand and adapt to you.
      </p>

      <div className="flex-1 min-h-0 px-4 sm:px-5">
        <div className="grid grid-cols-2 grid-rows-4 sm:grid-cols-4 sm:grid-rows-2 gap-2 h-full">
          {categories.map((cat) => {
            const on = selected.has(cat);
            const style = CATEGORY_STYLE[cat] ?? { slug: "philosophy", accent: "from-neutral-700/70 to-neutral-950/90" };
            return (
              <button
                key={cat}
                onClick={() => onToggle(cat)}
                className={
                  "relative rounded-2xl overflow-hidden transition-all border-2 min-h-0 " +
                  (on
                    ? "border-white scale-[0.98]"
                    : "border-transparent hover:scale-[1.02] hover:brightness-110")
                }
              >
                <img
                  src={`/media/img/_cat_${style.slug}.png`}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                  draggable={false}
                />
                <div className={"absolute inset-0 bg-gradient-to-t " + style.accent} />
                <div className="absolute inset-0 p-2.5 sm:p-3 flex items-end">
                  <div className="brutal-overlay text-white text-[5vw] sm:text-[clamp(20px,3.2vw,34px)] leading-[0.88] break-words text-left">
                    {cat.toUpperCase()}
                  </div>
                </div>
                {on && (
                  <div className="absolute top-2 right-2 w-7 h-7 rounded-full bg-white text-ink grid place-items-center text-sm font-bold">
                    ✓
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="px-4 sm:px-5 pt-2.5 pb-[max(12px,env(safe-area-inset-bottom))]">
        <button
          onClick={onNext}
          disabled={selected.size === 0}
          className="w-full py-3 rounded-2xl bg-white text-ink font-bold text-[clamp(15px,4.2vw,18px)] disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {selected.size === 0
            ? "Pick at least one category"
            : `Next — pick voices (${selected.size} ${selected.size === 1 ? "category" : "categories"})`}
        </button>
      </div>
    </>
  );
}

function VoiceStep({
  voices,
  selected,
  onToggle,
  onBack,
  onStart,
  catCount,
}: {
  voices: string[];
  selected: Set<string>;
  onToggle: (v: string) => void;
  onBack: () => void;
  onStart: () => void;
  catCount: number;
}) {
  const planned = catCount * 2; // matches per_category_count in the store
  return (
    <>
      <h1 className="px-4 sm:px-5 pt-2 brutal-overlay text-[6.4vw] sm:text-[clamp(32px,5.5vw,46px)] leading-[1] text-white whitespace-nowrap">
        pick your voices.
      </h1>
      <p className="px-4 sm:px-5 pt-1.5 pb-2 text-muted text-[3.8vw] sm:text-[clamp(15px,2vw,20px)] leading-snug">
        Each card is narrated. Pick one or more — we'll cycle through them.
      </p>

      <div className="flex-1 min-h-0 px-4 sm:px-5 overflow-y-auto">
        <div className="flex flex-col gap-3">
          {voices.map((v) => {
            const on = selected.has(v);
            const meta = VOICE_STYLE[v] ?? { slug: "rhyme_master", tag: "", accent: "ring-white/20" };
            return (
              <button
                key={v}
                onClick={() => onToggle(v)}
                className={
                  "group relative overflow-hidden rounded-3xl p-4 sm:p-5 text-left " +
                  "transition-all duration-200 border-2 " +
                  (on
                    ? "border-white bg-gradient-to-r from-white/[0.10] to-white/[0.03] " +
                      "shadow-[0_0_0_5px_rgba(255,255,255,0.06)]"
                    : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06] hover:border-white/30 hover:scale-[1.005]")
                }
              >
                {/* Soft accent glow when selected — same hue as the avatar ring. */}
                {on && (
                  <div
                    className={
                      "absolute inset-0 rounded-3xl pointer-events-none opacity-40 " +
                      "bg-gradient-to-r " +
                      (meta.accent.includes("rose")
                        ? "from-rose-400/30"
                        : meta.accent.includes("amber")
                          ? "from-amber-400/30"
                          : meta.accent.includes("sky")
                            ? "from-sky-400/30"
                            : "from-orange-400/30") +
                      " to-transparent"
                    }
                  />
                )}

                <div className="relative flex items-center gap-5 sm:gap-6">
                  {/* Avatar — generated portrait silhouette, sized to dominate
                      the row. Square crop via object-cover keeps the
                      shoulders-up framing readable. */}
                  <div className="relative shrink-0">
                    <div
                      className={
                        "w-24 h-24 sm:w-28 sm:h-28 rounded-full overflow-hidden " +
                        "ring-4 transition-all " +
                        (on ? "ring-white" : meta.accent)
                      }
                    >
                      <img
                        src={`/media/img/_voice_${meta.slug}.png`}
                        alt=""
                        className="w-full h-full object-cover"
                        draggable={false}
                      />
                    </div>
                    {/* Mic badge — anchored to the avatar so it reads as
                        "this is a voice profile". */}
                    <div
                      className={
                        "absolute -bottom-1 -right-1 w-8 h-8 rounded-full " +
                        "grid place-items-center text-[15px] " +
                        "ring-2 ring-ink " +
                        (on ? "bg-white" : "bg-panel")
                      }
                    >
                      🎙
                    </div>
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="brutal-overlay text-white text-[6.4vw] sm:text-[clamp(24px,2.8vw,32px)] leading-[1] mb-2">
                      {v.toUpperCase()}
                    </div>
                    <div className="text-muted text-[3.8vw] sm:text-[clamp(15px,1.6vw,18px)] leading-snug">
                      {meta.tag}
                    </div>
                  </div>

                  <div
                    className={
                      "w-9 h-9 sm:w-10 sm:h-10 rounded-full grid place-items-center " +
                      "text-base font-black shrink-0 transition-all " +
                      (on
                        ? "bg-white text-ink scale-100"
                        : "bg-white/10 text-transparent scale-90 group-hover:bg-white/20")
                    }
                  >
                    ✓
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Gradium attribution — text-only pill, scaled up to read as a
            billboard. Same brutalist style as the content cards' PartnerStrip. */}
        <div className="mt-6 flex justify-center">
          <div
            className="inline-flex items-center gap-6 px-9 py-6 rounded-full
                       bg-black/55 backdrop-blur-md ring-1 ring-white/15 text-white/85"
          >
            <span className="text-[18px] uppercase tracking-[0.22em] font-bold text-white/60 whitespace-nowrap">
              Powered by
            </span>
            <span className="text-[34px] font-black text-white whitespace-nowrap tracking-tight">
              Gradium
            </span>
            <span className="w-px h-11 bg-white/25" aria-hidden />
            <span className="text-[20px] text-white/70 font-semibold tracking-wide whitespace-nowrap">
              Voice cloning
            </span>
          </div>
        </div>
      </div>

      <div className="px-4 sm:px-5 pt-2.5 pb-[max(12px,env(safe-area-inset-bottom))] flex gap-2">
        <button
          onClick={onBack}
          className="px-5 py-3 rounded-2xl bg-white/10 text-white font-semibold text-[clamp(14px,3.8vw,16px)] hover:bg-white/15"
        >
          ← Back
        </button>
        <button
          onClick={onStart}
          disabled={selected.size === 0}
          className="flex-1 py-3 rounded-2xl bg-white text-ink font-bold text-[clamp(15px,4.2vw,18px)] disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {selected.size === 0 ? "Pick at least one voice" : `Generate ${planned} cards →`}
        </button>
      </div>
    </>
  );
}
