import { type AffinityRow } from "../lib/api";

type Props = {
  title: string;
  rows: AffinityRow[];
  limit?: number;
};

// A live-updating list of horizontal bars showing weighted affinity scores
// per bucket (topic / category / hook_type / voice).
export function AffinityBars({ title, rows, limit = 8 }: Props) {
  const slice = rows.slice(0, limit);
  const max = Math.max(1, ...slice.map((r) => Math.abs(r.score)));

  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.14em] text-white/40 font-bold mb-2">
        {title}
      </div>
      {slice.length === 0 ? (
        <div className="text-xs text-white/30 italic">no signal yet</div>
      ) : (
        <div className="space-y-1.5">
          {slice.map((r) => {
            const pct = (Math.abs(r.score) / max) * 100;
            const pos = r.score >= 0;
            return (
              <div key={r.bucket} className="text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-white/85 truncate flex-1 min-w-0">{r.bucket}</span>
                  <span
                    className={
                      "tabular-nums text-[11px] font-medium " +
                      (pos ? "text-emerald-300" : "text-rose-300")
                    }
                    title={`${r.likes} likes / ${r.dislikes} dislikes / ${r.interactions} interactions`}
                  >
                    {pos ? "+" : ""}
                    {r.score.toFixed(1)}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-white/5 overflow-hidden mt-0.5">
                  <div
                    className={
                      "h-full transition-all duration-500 " +
                      (pos ? "bg-emerald-400/80" : "bg-rose-400/80")
                    }
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
