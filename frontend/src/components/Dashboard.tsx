import { useEffect, useMemo, useState } from "react";
import { type CategoryStat, type StatRow } from "../lib/api";
import { useFlipReorder } from "../hooks/useFlipReorder";
import { useApp } from "../lib/store";
import { NextGenPreview } from "./NextGenPreview";

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
  const generatingBatch = useApp((s) => s.generatingBatch);

  useEffect(() => {
    if (!stats) fetchStats().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Rank categories DESC by affinity. Ties broken by (more cards_seen,
  // alphabetical). Mirrors backend planner so the rank shown matches the
  // rank used for next-gen planning.
  const rankedCategories = useMemo(() => {
    if (!stats) return [];
    return [...stats.categories]
      .map((c) => ({ cat: c, affinity: computeAffinity(c).total }))
      .sort((a, b) => {
        if (b.affinity !== a.affinity) return b.affinity - a.affinity;
        if (b.cat.cards_seen !== a.cat.cards_seen) return b.cat.cards_seen - a.cat.cards_seen;
        return a.cat.name.localeCompare(b.cat.name);
      })
      .map((r, i) => ({ rank: i + 1, cat: r.cat }));
  }, [stats]);

  const nextSlots = stats?.next_plan?.slots ?? [];

  return (
    <aside
      className="fixed top-0 right-0 z-30 h-[100dvh] w-[680px] flex-col
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

      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-5 space-y-3.5">
        {!stats || rankedCategories.length === 0 ? (
          <div className="text-base text-white/60 italic px-2 mt-4 leading-relaxed">
            Start swiping. As you watch and react, this panel fills in with the
            share of your watch time and your likes / dislikes per category and
            subtopic.
          </div>
        ) : (
          rankedCategories.map(({ rank, cat }) => (
            <CategoryRow key={cat.name} cat={cat} rank={rank} />
          ))
        )}
      </div>

      <NextGenPreview slots={nextSlots} generating={generatingBatch} />
    </aside>
  );
}

function CategoryRow({ cat, rank }: { cat: CategoryStat; rank: number }) {
  const [open, setOpen] = useState(false);
  const hasSubs = cat.subtopics.length > 0;
  const ref = useFlipReorder<HTMLDivElement>(cat.name);
  return (
    <div
      ref={ref}
      className="rounded-xl bg-white/[0.04] hover:bg-white/[0.07] transition-colors"
    >
      <button
        onClick={() => hasSubs && setOpen((v) => !v)}
        className="w-full px-5 py-4 text-left flex gap-4 items-stretch"
        disabled={!hasSubs}
      >
        {/* Rank flag — brutalist square block on the left. Color intensifies
            with rank #1 so the demo viewer sees who's on top at a glance. */}
        <div
          className={
            "shrink-0 flex items-center justify-center w-12 self-stretch " +
            (rank === 1
              ? "bg-gradient-to-br from-violet-400 to-fuchsia-400"
              : rank === 2
                ? "bg-violet-500/70"
                : rank === 3
                  ? "bg-violet-600/60"
                  : "bg-white/10")
          }
        >
          <span className="brutal-overlay text-ink text-[22px] leading-none">
            #{rank}
          </span>
        </div>

        <div className="flex-1 min-w-0">
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
        <div className="flex items-center gap-4">
          <ScoreBar row={cat} />
          <ScoreNumber row={cat} />
        </div>
        <div className="flex justify-between text-[14px] text-white/45 mt-2 tabular-nums">
          <span>{cat.cards_seen} cards · {fmtMs(cat.watch_ms)}</span>
        </div>
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
              <div className="flex items-center gap-3">
                <ScoreBar row={s} thin />
                <ScoreNumber row={s} compact />
              </div>
              <div className="flex justify-between text-[11px] text-white/40 mt-1.5 tabular-nums">
                <span>{s.cards_seen} · {fmtMs(s.watch_ms)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Single-color score bar. Same formula as before
// (watch% + 10×likes − 10×dislikes, clamped 0..100) — just rendered as a
// straightforward 0→100 points indicator instead of a stacked breakdown.
function ScoreBar({ row, thin = false }: { row: StatRow; thin?: boolean }) {
  const a = computeAffinity(row);
  return (
    <div
      className={
        (thin ? "h-3 " : "h-4 ") +
        "flex-1 rounded-full bg-white/5 overflow-hidden"
      }
    >
      <div
        className="h-full bg-gradient-to-r from-violet-400 to-fuchsia-400 transition-all duration-500"
        style={{ width: `${a.total}%` }}
      />
    </div>
  );
}

function ScoreNumber({ row, compact = false }: { row: StatRow; compact?: boolean }) {
  const a = computeAffinity(row);
  const big = compact ? "text-[24px]" : "text-[36px]";
  const max = compact ? "text-[12px]" : "text-[14px]";
  return (
    <div className="shrink-0 flex items-baseline gap-1 tabular-nums leading-none">
      <span className={"brutal-overlay text-white " + big}>
        {a.total.toFixed(0)}
      </span>
      <span className={"text-white/40 font-bold " + max}>/ 100</span>
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
