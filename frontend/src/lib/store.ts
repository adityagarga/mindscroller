// Global app state. Anonymous device UUID + current feed queue + lightweight
// per-user stats (watch % + likes/dislikes per category/subtopic).
//
// The brief / generate-next agent path is still wired on the backend, but the
// UI surfaces only the simple stats panel for now — agent flows return when
// we iterate on the recommendation pipeline.

import { create } from "zustand";
import { api, type Card, type Stats } from "./api";

const LS_USER_KEY = "mindscroller.userId";
const LS_PREFS_KEY = "mindscroller.categoryPreferences";
const LS_VOICES_KEY = "mindscroller.voicePreferences";
const LS_MUTED_KEY = "mindscroller.muted";

type Stage = "onboarding" | "warming" | "feed" | "error";

interface AppState {
  stage: Stage;
  userId: string | null;
  categoryPreferences: string[];
  voicePreferences: string[];
  queue: Card[];
  /** Index of the card currently centered in the feed. Used by generateBatch
   * to splice fresh cards in immediately after the active one. */
  activeIndex: number;
  currentVersion: string;
  error: string | null;

  stats: Stats | null;
  muted: boolean;

  /** True while the batch endpoint is in flight. Disables the FAB. */
  generatingBatch: boolean;
  lastBatchError: string | null;
  /** IDs of cards produced by /api/agent/generate-batch in this session, so
   * the Card UI can tag them as freshly generated. Cleared on resetSession. */
  freshlyGeneratedIds: Set<string>;

  hydrate: () => Promise<void>;
  beginColdStart: (categories: string[], voices?: string[]) => Promise<void>;
  fetchStats: () => Promise<void>;
  setActiveIndex: (i: number) => void;
  /** Trigger deterministic batch generation and splice the result into the
   * queue at activeIndex + 1. */
  generateBatch: () => Promise<void>;
  /** Called after every user interaction so the stats panel stays live. */
  onInteractionRecorded: () => Promise<void>;
  toggleMute: () => void;
  resetSession: () => void;
  setError: (msg: string) => void;
}

export const useApp = create<AppState>((set, get) => ({
  stage: "onboarding",
  userId: null,
  categoryPreferences: [],
  voicePreferences: [],
  queue: [],
  activeIndex: 0,
  currentVersion: "",
  error: null,

  stats: null,
  muted: localStorage.getItem(LS_MUTED_KEY) === "1",

  generatingBatch: false,
  lastBatchError: null,
  freshlyGeneratedIds: new Set<string>(),

  hydrate: async () => {
    const userId = localStorage.getItem(LS_USER_KEY);
    const prefs = JSON.parse(localStorage.getItem(LS_PREFS_KEY) || "[]") as string[];
    const voices = JSON.parse(localStorage.getItem(LS_VOICES_KEY) || "[]") as string[];
    if (!userId) {
      set({ stage: "onboarding" });
      return;
    }
    set({ userId, categoryPreferences: prefs, voicePreferences: voices });
    try {
      await api.syncFeed(userId).catch((e) =>
        console.warn("hydrate: sync failed (continuing)", e),
      );
      const { cards, version } = await api.feed(userId);
      if (cards.length === 0) {
        set({ currentVersion: version, stage: "onboarding" });
        return;
      }
      set({ queue: cards, currentVersion: version, stage: "feed" });
      get().fetchStats().catch((e) => console.warn("stats load failed", e));
    } catch (e) {
      console.warn("hydrate: feed fetch failed, resetting session", e);
      get().resetSession();
    }
  },

  beginColdStart: async (categories, voices = []) => {
    set({
      stage: "warming",
      error: null,
      categoryPreferences: categories,
      voicePreferences: voices,
    });
    localStorage.setItem(LS_PREFS_KEY, JSON.stringify(categories));
    localStorage.setItem(LS_VOICES_KEY, JSON.stringify(voices));
    try {
      const { user_id, cards } = await api.createUser({
        topic_preferences: categories,
        voice_preferences: voices,
        // Onboarding: fresh-generate 2 cards per selected category, cycling
        // through the voices the user picked.
        per_category_count: 2,
      });
      localStorage.setItem(LS_USER_KEY, user_id);
      set({ userId: user_id, queue: cards, stage: "feed" });
      get().fetchStats().catch((e) => console.warn("stats load failed", e));
    } catch (e: any) {
      set({ stage: "error", error: String(e?.message ?? e) });
    }
  },

  fetchStats: async () => {
    const { userId, voicePreferences } = get();
    if (!userId) return;
    const s = await api.stats(userId, voicePreferences);
    set({ stats: s });
  },

  setActiveIndex: (i) => set({ activeIndex: i }),

  generateBatch: async () => {
    const { userId, voicePreferences, queue, activeIndex, generatingBatch } = get();
    if (!userId || generatingBatch) return;
    set({ generatingBatch: true, lastBatchError: null });
    try {
      const { cards } = await api.agentGenerateBatch(userId, 4, voicePreferences);
      // Splice the new cards in immediately after the currently active one so
      // the next swipe lands on a fresh, personalized card.
      const insertAt = Math.min(queue.length, Math.max(0, activeIndex) + 1);
      const nextQueue = [
        ...queue.slice(0, insertAt),
        ...cards,
        ...queue.slice(insertAt),
      ];
      const nextFresh = new Set(get().freshlyGeneratedIds);
      for (const c of cards) nextFresh.add(c.id);
      set({
        queue: nextQueue,
        freshlyGeneratedIds: nextFresh,
        generatingBatch: false,
      });
      // Refresh stats so the Next-Gen preview reflects the new feed-state
      // (and any rank shifts once the user starts interacting with the new
      // cards).
      get().fetchStats().catch((e) => console.warn("post-batch stats refresh failed", e));
    } catch (e: any) {
      set({ generatingBatch: false, lastBatchError: String(e?.message ?? e) });
    }
  },

  onInteractionRecorded: async () => {
    // Cheap SQL aggregate — refresh on every event.
    await get().fetchStats().catch(() => {});
  },

  toggleMute: () => {
    const next = !get().muted;
    localStorage.setItem(LS_MUTED_KEY, next ? "1" : "0");
    set({ muted: next });
  },

  resetSession: () => {
    localStorage.removeItem(LS_USER_KEY);
    localStorage.removeItem(LS_PREFS_KEY);
    localStorage.removeItem(LS_VOICES_KEY);
    set({
      stage: "onboarding",
      userId: null,
      categoryPreferences: [],
      voicePreferences: [],
      queue: [],
      stats: null,
      error: null,
      freshlyGeneratedIds: new Set<string>(),
    });
  },

  setError: (msg) => set({ stage: "error", error: msg }),
}));
