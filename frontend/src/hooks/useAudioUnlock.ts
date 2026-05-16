// Browser autoplay policy blocks audio.play() until the user has interacted
// with the page. Onboarding's "Start" tap should satisfy this, but the 8-12s
// warming-up splash often outlives the gesture credential in Safari.
//
// This hook listens for the first interaction inside the feed and force-plays
// whatever audio is currently sitting on the active card. Subsequent swipes
// are themselves gestures, so autoplay works from card #2 onward.

import { useEffect, useRef } from "react";

export function useAudioUnlock(containerRef: React.RefObject<HTMLElement>) {
  const unlockedRef = useRef(false);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    function unlock() {
      if (unlockedRef.current) return;
      // Find the audio on the topmost-visible card and force-play it.
      const cards = Array.from(root!.querySelectorAll<HTMLElement>(".feed-card"));
      const rect = root!.getBoundingClientRect();
      const active = cards.find((c) => {
        const r = c.getBoundingClientRect();
        return r.bottom > rect.top + 4 && r.top < rect.bottom - 4;
      });
      const audio = active?.querySelector<HTMLAudioElement>("audio[data-audio]");
      if (audio) audio.playbackRate = 1.15; // keep in sync with NARRATION_RATE
      audio?.play().then(
        () => {
          unlockedRef.current = true;
        },
        () => {
          // still blocked — leave the listeners attached for the next gesture
        },
      );
    }

    const opts = { passive: true } as AddEventListenerOptions;
    root.addEventListener("touchstart", unlock, opts);
    root.addEventListener("pointerdown", unlock, opts);
    root.addEventListener("scroll", unlock, opts);
    root.addEventListener("wheel", unlock, opts);
    root.addEventListener("keydown", unlock, opts);
    return () => {
      root.removeEventListener("touchstart", unlock);
      root.removeEventListener("pointerdown", unlock);
      root.removeEventListener("scroll", unlock);
      root.removeEventListener("wheel", unlock);
      root.removeEventListener("keydown", unlock);
    };
  }, [containerRef]);
}
