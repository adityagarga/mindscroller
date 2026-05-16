import { type PlanSlot } from "../lib/api";
import { useApp } from "../lib/store";

// Live preview of the next 4 cards the agent would generate, given current
// stats. Mirrors the deterministic planner on the backend; updates whenever
// the parent re-renders with fresh stats (which happens after every
// interaction via store.onInteractionRecorded). The big GENERATE button at
// the bottom triggers /api/agent/generate-batch with this exact plan.
export function NextGenPreview({
  slots,
  generating = false,
}: {
  slots: PlanSlot[];
  generating?: boolean;
}) {
  const stats = useApp((s) => s.stats);
  const generateBatch = useApp((s) => s.generateBatch);
  const lastBatchError = useApp((s) => s.lastBatchError);

  const hasSignal =
    !!stats &&
    (stats.total_watch_ms > 0 ||
      stats.total_likes > 0 ||
      stats.total_dislikes > 0);

  const disabled = !hasSignal || generating;

  let cta = "GENERATE NEW CONTENT";
  if (generating) cta = "GENERATING 4 NEW CARDS…";
  else if (!hasSignal) cta = "WATCH SOME CARDS FIRST";
  else if (lastBatchError) cta = "RETRY GENERATION";

  return (
    <section className="border-t-2 border-border bg-black/45 px-6 pt-5 pb-[max(20px,env(safe-area-inset-bottom))]">
      <div className="flex items-center justify-between mb-3">
        <h3 className="brutal-overlay text-white text-[26px] tracking-tight">
          NEXT 4 — BASED ON YOU
        </h3>
        <span className="flex items-center gap-1.5 text-[12px] uppercase tracking-[0.18em] font-black text-emerald-300">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          {generating ? "GENERATING…" : "LIVE"}
        </span>
      </div>

      <div className="space-y-2 mb-4">
        {slots.length === 0 ? (
          <div className="text-[15px] text-white/45 italic">
            Waiting for interaction signal…
          </div>
        ) : (
          slots.map((s) => <SlotRow key={s.rank} slot={s} />)
        )}
      </div>

      {/* Primary CTA — replaces the old FAB with an unmissable button. */}
      <button
        onClick={() => !disabled && generateBatch()}
        disabled={disabled}
        className={
          "w-full py-4 brutal-overlay text-[22px] tracking-[0.04em] " +
          "border-2 shadow-[4px_4px_0_rgba(0,0,0,0.6)] transition-all " +
          (disabled
            ? "bg-white/10 border-white/15 text-white/40 cursor-not-allowed"
            : "bg-gradient-to-r from-violet-400 to-fuchsia-500 border-white/50 " +
              "text-ink hover:scale-[1.01] active:scale-95") +
          (lastBatchError && !disabled ? " ring-2 ring-rose-400" : "")
        }
      >
        {generating ? (
          <span className="inline-flex items-center gap-3 justify-center">
            <Spinner /> {cta}
          </span>
        ) : (
          cta
        )}
      </button>
      {lastBatchError && (
        <p className="text-[12px] text-rose-300 mt-2 truncate">
          {lastBatchError}
        </p>
      )}
    </section>
  );
}

function SlotRow({ slot }: { slot: PlanSlot }) {
  return (
    <div
      className="flex gap-3 items-stretch border-2 border-white/15 bg-white/[0.04]
                 shadow-[3px_3px_0_rgba(0,0,0,0.55)]"
    >
      {/* Rank flag — brutalist square block on the left */}
      <div className="bg-violet-400 flex items-center justify-center px-3 min-w-[52px]">
        <span className="brutal-overlay text-ink text-[26px] leading-none">
          #{slot.rank}
        </span>
      </div>

      <div className="flex-1 py-3 pr-3 min-w-0">
        <div className="mb-1">
          <span className="text-white font-black text-[18px] uppercase tracking-[0.04em] truncate block">
            {slot.category}
          </span>
        </div>
        <div className="text-white/85 text-[16px] truncate">
          {slot.topic} <span className="text-white/40 mx-1">·</span>{" "}
          <span className="text-sky-300 uppercase tracking-wider text-[14px] font-bold">
            {slot.hook_type}
          </span>
        </div>
        <div className="text-white/55 text-[13px] italic mt-1 truncate">
          {slot.reason}
        </div>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      className="animate-spin"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        fill="none"
        stroke="rgba(0,0,0,0.25)"
        strokeWidth="2.5"
      />
      <path
        d="M12 3a9 9 0 0 1 9 9"
        fill="none"
        stroke="black"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
