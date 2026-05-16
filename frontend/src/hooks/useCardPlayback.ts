// Orchestrates audio playback across the scroll-snap feed.
//
// When a card crosses 70% visibility, its <audio> plays.
// When it leaves, it pauses + resets to 0. Only one audio is ever playing.
// Also fires the per-card lifecycle callbacks the Feed uses to record
// view / complete interactions.

import { useEffect, useRef } from "react";

// Gentle narration speedup applied client-side. Gradium TTS itself doesn't
// expose a rate knob in the SDK we use, and pitch-preserving playbackRate is
// the simplest model-agnostic fix. Tune this to taste: 1.15 ≈ "a bit faster";
// >1.25 starts to sound unnaturally rushed for storytelling voices.
const NARRATION_RATE = 1.15;

type Options = {
  containerRef: React.RefObject<HTMLElement>;
  onActiveChange?: (cardId: string | null) => void;
  onComplete?: (cardId: string, durationMs: number) => void;
};

export function useCardPlayback({ containerRef, onActiveChange, onComplete }: Options) {
  const activeRef = useRef<HTMLAudioElement | null>(null);
  const enterTimeRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const cards = Array.from(root.querySelectorAll<HTMLElement>(".feed-card"));
    if (!cards.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const el = entry.target as HTMLElement;
          const cardId = el.dataset.cardId!;
          const audio = el.querySelector<HTMLAudioElement>("audio[data-audio]");

          if (entry.isIntersecting && entry.intersectionRatio >= 0.7) {
            // IntersectionObserver fires when CROSSING 0.7 in either direction.
            // We only want to treat this as "card became active" the first time
            // — otherwise the exit-through-0.7 event resets enterTime and the
            // complete duration ends up as the ~200ms scroll motion.
            const alreadyActive = enterTimeRef.current.has(cardId);
            if (alreadyActive) continue;

            if (activeRef.current && activeRef.current !== audio) {
              activeRef.current.pause();
              activeRef.current.currentTime = 0;
            }
            activeRef.current = audio ?? null;
            enterTimeRef.current.set(cardId, performance.now());
            onActiveChange?.(cardId);
            if (audio) {
              audio.playbackRate = NARRATION_RATE;
              audio.play().catch(() => {
                // Autoplay may be blocked until first user gesture; that's fine —
                // the next swipe is itself a gesture, so subsequent cards will play.
              });
            }
          } else if (entry.intersectionRatio < 0.4) {
            if (audio && !audio.paused) audio.pause();
            const enterT = enterTimeRef.current.get(cardId);
            if (enterT != null) {
              const dur = Math.round(performance.now() - enterT);
              enterTimeRef.current.delete(cardId);
              if (dur >= 800) onComplete?.(cardId, dur);
            }
          }
        }
      },
      { root, threshold: [0, 0.4, 0.7, 1] },
    );

    cards.forEach((c) => observer.observe(c));
    return () => observer.disconnect();
    // Re-run if the cards list mutates — Feed passes a stable container and
    // re-renders cards in place, so we hook on container identity.
  }, [containerRef, onActiveChange, onComplete]);
}
