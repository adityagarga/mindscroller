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

  const onActiveChange = useCallback(
    (id: string | null) => {
      setActiveId(id);
      if (id) recordInteraction(id, "view");
    },
    [recordInteraction],
  );

  const onComplete = useCallback(
    (cardId: string, dur: number) => recordInteraction(cardId, "complete", dur),
    [recordInteraction],
  );

  useCardPlayback({ containerRef, onActiveChange, onComplete });
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
        className="feed xl:!w-[calc(100vw-560px)]"
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
