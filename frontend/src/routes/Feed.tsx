import { useCallback, useEffect, useRef, useState } from "react";
import { Card } from "../components/Card";
import { Dashboard } from "../components/Dashboard";
import { Header } from "../components/Header";
import { useAudioUnlock } from "../hooks/useAudioUnlock";
import { useCardPlayback } from "../hooks/useCardPlayback";
import { api, type EventType } from "../lib/api";
import { useApp } from "../lib/store";

export function Feed() {
  const queue = useApp((s) => s.queue);
  const userId = useApp((s) => s.userId);
  const onInteractionRecorded = useApp((s) => s.onInteractionRecorded);
  const setActiveIndex = useApp((s) => s.setActiveIndex);

  const containerRef = useRef<HTMLElement>(null);
  const [, setActiveId] = useState<string | null>(null);

  const recordInteraction = useCallback(
    async (card_id: string, event_type: EventType, view_duration_ms?: number) => {
      if (!userId) return;
      try {
        await api.interact({ user_id: userId, card_id, event_type, view_duration_ms });
      } catch (e) {
        console.warn("interaction record failed", e);
      }
      // Tell the agent state to refresh after every interaction.
      onInteractionRecorded().catch(() => {});
    },
    [userId, onInteractionRecorded],
  );

  // Keep store.activeIndex in sync with the visible card. The batch generator
  // splices new cards in at activeIndex + 1, so this must be live.
  const queueRef = useRef(queue);
  queueRef.current = queue;

  const onActiveChange = useCallback(
    (id: string | null) => {
      setActiveId(id);
      if (id) {
        recordInteraction(id, "view");
        const idx = queueRef.current.findIndex((c) => c.id === id);
        if (idx >= 0) setActiveIndex(idx);
      }
    },
    [recordInteraction, setActiveIndex],
  );

  const onComplete = useCallback(
    (cardId: string, dur: number) => recordInteraction(cardId, "complete", dur),
    [recordInteraction],
  );

  useCardPlayback({
    containerRef,
    cardCount: queue.length,
    onActiveChange,
    onComplete,
  });
  useAudioUnlock(containerRef);

  useEffect(() => {
    if (!queue.length) return;
    setActiveId((cur) => cur ?? queue[0]?.id ?? null);
  }, [queue.length]);

  if (!queue.length) {
    return (
      <>
        <Header />
        <div className="min-h-[100dvh] grid place-items-center text-muted text-center px-6">
          <div>
            <div className="brutal-overlay text-white text-2xl mb-2">NO CARDS YET</div>
            <div className="text-sm">
              Generate some in the workbench at{" "}
              <a
                href="http://localhost:8000/workbench"
                className="underline text-white/80 hover:text-white"
              >
                /workbench
              </a>
              , then reload.
            </div>
          </div>
        </div>
        <Dashboard />
      </>
    );
  }

  return (
    <>
      <Header />
      {/* The feed reserves space for the dashboard on xl+ viewports so the
          portrait card stays centered in the *remaining* width. The card
          itself is capped at a mobile-shaped 440px (see Card.tsx). */}
      <section
        ref={containerRef}
        className="feed xl:!w-[calc(100vw-680px)]"
      >
        {queue.map((c) => (
          <Card
            key={c.id}
            card={c}
            onLike={() => recordInteraction(c.id, "like")}
            onDislike={() => recordInteraction(c.id, "dislike")}
          />
        ))}
      </section>
      <Dashboard />
    </>
  );
}
