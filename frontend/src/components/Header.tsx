import { useApp } from "../lib/store";

// The feed header brand. Width matches the feed reservation (100vw − 560px on
// xl screens, where the stats panel takes the right column).
export function Header() {
  const queueLen = useApp((s) => s.queue.length);

  return (
    <header
      className="fixed top-0 left-0 z-40 px-4 pt-[max(10px,env(safe-area-inset-top))] pb-2.5
                 flex items-center justify-between
                 bg-gradient-to-b from-black/85 via-black/55 to-transparent
                 w-full xl:w-[calc(100vw-560px)]"
    >
      <span
        className="brutal-overlay text-white select-none"
        style={{ fontSize: "clamp(28px, 5vw, 44px)", letterSpacing: "-0.03em", lineHeight: 1 }}
      >
        MINDSCROLLER
      </span>

      <span className="text-sm text-white/60 font-bold tabular-nums">
        {queueLen} {queueLen === 1 ? "card" : "cards"}
      </span>
    </header>
  );
}
