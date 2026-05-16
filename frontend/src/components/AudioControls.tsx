import { useApp } from "../lib/store";

// Mute / unmute toggle anchored to the top-left of the card's inner portrait
// container. Playback itself is driven automatically by the Feed's
// IntersectionObserver — there is no manual play button.
//
// The actual `audio.muted` binding lives on the <audio> element in Card.tsx
// (`muted={muted}` prop), so React applies the global mute state
// synchronously on every render. This component just toggles the store.

type Props = {
  // Kept for API stability; no longer used (mute is bound via JSX prop).
  getAudio?: () => HTMLAudioElement | null;
};

export function AudioControls(_: Props) {
  const muted = useApp((s) => s.muted);
  const toggleMute = useApp((s) => s.toggleMute);

  function onMute(e: React.MouseEvent) {
    e.stopPropagation();
    toggleMute();
  }

  return (
    <div className="absolute top-3 left-3 z-20">
      <button
        onClick={onMute}
        aria-label={muted ? "unmute" : "mute"}
        aria-pressed={muted}
        className="h-14 w-14 rounded-full bg-black/65 backdrop-blur-sm grid place-items-center
                   border-2 border-white/30 hover:bg-black/85 hover:border-white/50
                   active:scale-90 transition-all
                   shadow-[0_4px_12px_rgba(0,0,0,0.45)]"
      >
        {muted ? (
          <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
            <path d="M3 9v6h4l5 5V4L7 9H3z" />
            <line x1="16" y1="9" x2="22" y2="15" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="22" y1="9" x2="16" y2="15" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
            <path d="M3 9v6h4l5 5V4L7 9H3z" />
            <path
              d="M16 8c1.5 1.2 2.5 2.6 2.5 4s-1 2.8-2.5 4M19 5c2.5 1.8 4 4.2 4 7s-1.5 5.2-4 7"
              stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round"
            />
          </svg>
        )}
      </button>
    </div>
  );
}
