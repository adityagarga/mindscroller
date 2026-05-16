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
  currentVersion: string;
  error: string | null;

  stats: Stats | null;
  muted: boolean;

  hydrate: () => Promise<void>;
  beginColdStart: (categories: string[], voices?: string[]) => Promise<void>;
  fetchStats: () => Promise<void>;
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
  currentVersion: "",
  error: null,

  stats: null,
  muted: localStorage.getItem(LS_MUTED_KEY) === "1",

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
    const { userId } = get();
    if (!userId) return;
    const s = await api.stats(userId);
    set({ stats: s });
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
    });
  },

  setError: (msg) => set({ stage: "error", error: msg }),
}));
