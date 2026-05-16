import { useEffect, useState } from "react";
import { type CategoryStat, type StatRow } from "../lib/api";
import { useApp } from "../lib/store";

// Affinity score per (sub)category — the single number the agent will consume
// when deciding what to generate next. Linear blend of two signals:
//
//   affinity = clamp(watch_share + 10 × likes − 10 × dislikes, 0, 100)
//
// • watch_share is the user's share of total watch time on this bucket (0..100)
// • each net like adds 10 affinity points; each net dislike subtracts 10
//
// The bar visualizes the watch-share base (violet) stacked with the like bonus
// (emerald) so demo viewers can see how the two signals combine.
const LIKE_WEIGHT = 10;
const DISLIKE_WEIGHT = 10;

type AffinityBreakdown = {
  total: number;       // final score 0..100
  watchVisible: number;
  likeVisible: number;
  bonus: number;       // raw + contribution from likes
  penalty: number;     // raw − contribution from dislikes
};

function computeAffinity(s: StatRow): AffinityBreakdown {
  const bonus = s.likes * LIKE_WEIGHT;
  const penalty = s.dislikes * DISLIKE_WEIGHT;
  const total = Math.max(0, Math.min(100, s.watch_percentage + bonus - penalty));
  const watchVisible = Math.min(s.watch_percentage, total);
  const likeVisible = Math.max(0, total - watchVisible);
  return { total, watchVisible, likeVisible, bonus, penalty };
}

// Lightweight stats panel. For each category we show:
//   • share of total watch time (as a horizontal bar + %)
//   • like / dislike counts
//   • tap to expand → per-subtopic rows with the same numbers
export function Dashboard() {
  const stats = useApp((s) => s.stats);
  const fetchStats = useApp((s) => s.fetchStats);

  useEffect(() => {
    if (!stats) fetchStats().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <aside
      className="fixed top-0 right-0 z-30 h-[100dvh] w-[560px] flex-col
                 bg-panel/95 backdrop-blur-md border-l border-border
                 hidden xl:flex"
    >
      <div className="px-7 pt-[max(22px,env(safe-area-inset-top))] pb-5 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="brutal-overlay text-white text-4xl tracking-tight">YOUR STATS</h2>
          <span className="text-sm text-white/60 tabular-nums font-semibold">
            {stats ? `${stats.total_cards_seen} cards` : "—"}
          </span>
        </div>
        {stats && (
          <div className="text-base text-white/75 flex gap-6">
            <span className="flex items-baseline gap-1.5">
              <span className="text-rose-300 text-xl">♥</span>
              <span className="text-white font-bold text-2xl">{stats.total_likes}</span>
            </span>
            <span className="flex items-baseline gap-1.5">
              <span className="text-xl">👎</span>
              <span className="text-white font-bold text-2xl">{stats.total_dislikes}</span>
            </span>
            <span className="flex items-baseline gap-1.5">
              <span className="text-xl">👁</span>
              <span className="text-white font-bold text-2xl">{fmtMs(stats.total_watch_ms)}</span>
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-3.5">
        {!stats || stats.categories.length === 0 ? (
          <div className="text-base text-white/60 italic px-2 mt-4 leading-relaxed">
            Start swiping. As you watch and react, this panel fills in with the
            share of your watch time and your likes / dislikes per category and
            subtopic.
          </div>
        ) : (
          stats.categories.map((c) => <CategoryRow key={c.name} cat={c} />)
        )}
      </div>
    </aside>
  );
}

function CategoryRow({ cat }: { cat: CategoryStat }) {
  const [open, setOpen] = useState(false);
  const hasSubs = cat.subtopics.length > 0;
  return (
    <div className="rounded-xl bg-white/[0.04] hover:bg-white/[0.07] transition-colors">
      <button
        onClick={() => hasSubs && setOpen((v) => !v)}
        className="w-full px-6 py-5 text-left"
        disabled={!hasSubs}
      >
        <div className="flex items-center justify-between gap-3 mb-3">
          <span className="text-[26px] text-white font-bold truncate tracking-tight leading-tight">
            {cat.name}
          </span>
          <span className="tabular-nums shrink-0 flex items-center gap-4">
            <span className="flex items-baseline gap-1.5 text-rose-300 font-black">
              <span className="text-[20px] leading-none">♥</span>
              <span className="text-[30px] leading-none">{cat.likes}</span>
            </span>
            <span className="flex items-baseline gap-1.5 text-white/65 font-black">
              <span className="text-[20px] leading-none">👎</span>
              <span className="text-[30px] leading-none">{cat.dislikes}</span>
            </span>
            {hasSubs && (
              <span className={"text-white/45 transition-transform text-2xl " + (open ? "rotate-180" : "")}>
                ▾
              </span>
            )}
          </span>
        </div>
        <AffinityBar row={cat} />
        <AffinityCaption row={cat} />
        <div className="flex justify-between text-[14px] text-white/45 mt-1.5 tabular-nums">
          <span>{cat.cards_seen} cards · {fmtMs(cat.watch_ms)}</span>
        </div>
      </button>

      {open && hasSubs && (
        <div className="pl-8 pr-6 pb-4 space-y-3.5">
          {cat.subtopics.map((s) => (
            <div key={s.name} className="border-l-2 border-white/15 pl-4">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-[17px] text-white/90 truncate">
                  ↳ {s.name}
                </span>
                <span className="tabular-nums shrink-0 flex items-center gap-3">
                  <span className="flex items-baseline gap-1 text-rose-300/90 font-bold">
                    <span className="text-[14px] leading-none">♥</span>
                    <span className="text-[20px] leading-none">{s.likes}</span>
                  </span>
                  <span className="flex items-baseline gap-1 text-white/55 font-bold">
                    <span className="text-[14px] leading-none">👎</span>
                    <span className="text-[20px] leading-none">{s.dislikes}</span>
                  </span>
                </span>
              </div>
              <AffinityBar row={s} thin />
              <AffinityCaption row={s} compact />
              <div className="flex justify-between text-[11px] text-white/40 mt-1 tabular-nums">
                <span>{s.cards_seen} · {fmtMs(s.watch_ms)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Stacked affinity bar: violet segment = watch share, emerald segment = like
// bonus stacked on top. Dislike penalty shrinks the total (visible as the
// unfilled tail) and is surfaced numerically in the caption below.
function AffinityBar({ row, thin = false }: { row: StatRow; thin?: boolean }) {
  const a = computeAffinity(row);
  return (
    <div
      className={
        (thin ? "h-2.5 " : "h-3.5 ") +
        "rounded-full bg-white/5 overflow-hidden flex relative"
      }
    >
      <div
        className="h-full bg-gradient-to-r from-violet-400 to-fuchsia-400 transition-all duration-500"
        style={{ width: `${a.watchVisible}%` }}
      />
      <div
        className="h-full bg-gradient-to-r from-emerald-400 to-lime-300 transition-all duration-500"
        style={{ width: `${a.likeVisible}%` }}
      />
    </div>
  );
}

function AffinityCaption({ row, compact = false }: { row: StatRow; compact?: boolean }) {
  const a = computeAffinity(row);
  const size = compact ? "text-[12px]" : "text-[14px]";
  const totalSize = compact ? "text-[16px]" : "text-[20px]";
  return (
    <div className={"flex items-center justify-between gap-2 mt-2 tabular-nums " + size}>
      <span className="flex items-center gap-2 flex-wrap text-white/65 font-semibold">
        <span className="text-violet-300">watch {row.watch_percentage.toFixed(0)}%</span>
        {a.bonus > 0 && <span className="text-emerald-300">+ ♥{a.bonus}</span>}
        {a.penalty > 0 && <span className="text-rose-300">− 👎{a.penalty}</span>}
      </span>
      <span className={"font-black text-white " + totalSize + " leading-none"}>
        {a.total.toFixed(0)}
        <span className="text-white/45 text-[0.6em] ml-0.5">aff</span>
      </span>
    </div>
  );
}

function fmtMs(ms: number): string {
  if (!ms) return "0s";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem ? `${m}m ${rem}s` : `${m}m`;
}
