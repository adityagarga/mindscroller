import { useEffect, useState } from "react";
import { useApp } from "../lib/store";

const PHASES = [
  "writing your first cards",
  "asking flux for posters",
  "warming up the voices",
  "stacking your feed",
];

export function Splash() {
  const topics = useApp((s) => s.categoryPreferences);
  const voices = useApp((s) => s.voicePreferences);
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const id = setInterval(
      () => setPhase((p) => (p + 1) % PHASES.length),
      2200,
    );
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center px-6 text-center relative">
      {/* Animated mark */}
      <div className="mb-7 relative w-20 h-20 sm:w-24 sm:h-24">
        <div className="absolute inset-0 rounded-2xl border-2 border-white/20" />
        <div className="absolute inset-0 rounded-2xl border-2 border-t-white border-r-white/40 border-b-transparent border-l-transparent animate-spin" />
      </div>

      <div className="brutal-overlay text-[clamp(36px,12vw,72px)] leading-[0.9] mb-4">
        generating<br />your feed
      </div>
      <div className="text-muted text-[clamp(14px,3.8vw,18px)] mb-8">{PHASES[phase]}…</div>

      {topics.length > 0 && (
        <div className="flex flex-wrap justify-center gap-2 max-w-xl mb-4">
          {topics.map((t) => (
            <span
              key={t}
              className="px-3 py-1.5 rounded-full text-xs sm:text-sm bg-panel border border-border text-white/70"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      {voices.length > 0 && (
        <div className="flex flex-wrap justify-center gap-2 max-w-xl">
          {voices.map((v) => (
            <span
              key={v}
              className="px-3 py-1 rounded-full text-[11px] sm:text-xs bg-white/5 text-white/55"
            >
              🎙 {v}
            </span>
          ))}
        </div>
      )}

      <div className="absolute bottom-10 left-0 right-0 text-center text-[11px] sm:text-xs text-muted px-6">
        Generating 2 cards per category. This takes ~30s — hold tight.
      </div>
    </div>
  );
}
