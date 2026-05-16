import { useEffect } from "react";
import { useApp } from "../lib/store";

// Mute / unmute toggle anchored to the top-left of the card's inner portrait
// container. Playback itself is driven automatically by the Feed's
// IntersectionObserver — there is no manual play button.

type Props = {
  getAudio: () => HTMLAudioElement | null;
};

export function AudioControls({ getAudio }: Props) {
  const muted = useApp((s) => s.muted);
  const toggleMute = useApp((s) => s.toggleMute);

  // Keep the audio element's `muted` state in sync with the global toggle.
  useEffect(() => {
    const a = getAudio();
    if (a) a.muted = muted;
  }, [muted, getAudio]);

  function onMute(e: React.MouseEvent) {
    e.stopPropagation();
    toggleMute();
  }

  return (
    <div className="absolute top-3 left-3 z-20">
      <button
        onClick={onMute}
        aria-label={muted ? "unmute" : "mute"}
        className="h-10 w-10 rounded-full bg-black/60 backdrop-blur-sm grid place-items-center
                   border border-white/20 hover:bg-black/80 active:scale-90 transition-all"
      >
        {muted ? (
          <svg viewBox="0 0 24 24" width="20" height="20" fill="white">
            <path d="M3 9v6h4l5 5V4L7 9H3z" />
            <line x1="16" y1="9" x2="22" y2="15" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="22" y1="9" x2="16" y2="15" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="20" height="20" fill="white">
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
