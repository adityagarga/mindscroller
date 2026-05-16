// Typed fetch wrappers for the FastAPI backend.
// Vite proxies /api and /media to localhost:8000 in dev.

export type Card = {
  id: string;
  category: string;
  topic: string;
  hook_type: string;
  visual_hook: string;
  script: string;
  image_prompt: string;
  image_path: string | null;
  audio_path: string | null;
  parent_card_id: string | null;
  thread_order: number | null;
  created_for_user: string | null;
  version: string;
  voice: string | null;
  created_at: string;
};

export type EventType = "like" | "dislike" | "dismiss" | "view" | "complete" | "skip";

export type Taxonomy = {
  taxonomy: Record<string, string[]>;
  hook_types: string[];
  hook_type_specs: Record<
    string,
    { tagline: string; rule: string; example: string }
  >;
  voices?: Record<string, { voice_id: string; description: string }>;
  default_voice?: string;
};

export type AffinityRow = {
  bucket: string;
  score: number;
  interactions: number;
  likes: number;
  dislikes: number;
};

export type RecentInteraction = {
  id: number;
  event_type: string;
  view_duration_ms: number | null;
  created_at: string;
  card_id: string;
  category: string;
  topic: string;
  hook_type: string;
  visual_hook: string;
  voice: string | null;
};

export type DiscoveredTopic = {
  category: string;
  topic: string;
  first_seen_at: string;
  use_count: number;
};

export type AgentState = {
  affinity: {
    category: AffinityRow[];
    topic: AffinityRow[];
    hook_type: AffinityRow[];
    voice: AffinityRow[];
  };
  interactions_total: number;
  recent_interactions: RecentInteraction[];
  discovered_topics: DiscoveredTopic[];
};

export type Brief = {
  category: string;
  topic: string;
  hook_type: string;
  angle: string;
  reasoning: string;
  is_new_topic: boolean;
};

export type StatRow = {
  name: string;
  watch_ms: number;
  watch_percentage: number; // 0..100, share of total watch_ms
  likes: number;
  dislikes: number;
  cards_seen: number;
};

export type CategoryStat = StatRow & {
  subtopics: StatRow[];
};

// One row in the dashboard's Next-Gen bucket — exactly what the agent will
// generate if you click the FAB right now. Backend's planner is the single
// source of truth (backend/app/agent/planner.py).
export type PlanSlot = {
  rank: number;
  category: string;
  topic: string;
  hook_type: string;
  voice: string;
  reason: string;
};

export type Stats = {
  categories: CategoryStat[];
  total_watch_ms: number;
  total_likes: number;
  total_dislikes: number;
  total_cards_seen: number;
  next_plan: { slots: PlanSlot[] };
};

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${r.status} ${r.statusText} — ${text.slice(0, 400)}`);
  }
  return (await r.json()) as T;
}

export const api = {
  taxonomy: () => jsonFetch<Taxonomy>("/api/workbench/taxonomy"),

  createUser: (params: {
    topic_preferences: string[];
    voice_preferences?: string[];
    cold_start_count?: number;
    per_category_count?: number;
    skip_audio?: boolean;
    skip_image?: boolean;
  }) =>
    jsonFetch<{
      user_id: string;
      cards: Card[];
      topic_preferences: string[];
    }>("/api/users", {
      method: "POST",
      body: JSON.stringify({
        cold_start_count: 0,
        per_category_count: 0,
        voice_preferences: [],
        skip_audio: false,
        skip_image: false,
        ...params,
      }),
    }),

  feed: (user_id: string, offset = 0, limit = 500) =>
    jsonFetch<{ cards: Card[]; total: number; version: string }>(
      `/api/feed?user_id=${encodeURIComponent(user_id)}&offset=${offset}&limit=${limit}`,
    ),

  interact: (params: {
    user_id: string;
    card_id: string;
    event_type: EventType;
    view_duration_ms?: number;
  }) =>
    jsonFetch<{ ok: boolean }>("/api/interactions", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  refill: (user_id: string, n = 3) =>
    jsonFetch<{ ok: boolean; queued: number }>("/api/feed/refill", {
      method: "POST",
      body: JSON.stringify({ user_id, n }),
    }),

  syncFeed: (user_id: string) =>
    jsonFetch<{ ok: boolean; added: number; total: number; version: string }>(
      "/api/feed/sync",
      { method: "POST", body: JSON.stringify({ user_id }) },
    ),

  // ---------- Phase 3: agent ----------

  agentState: (user_id: string) =>
    jsonFetch<AgentState>(`/api/agent/state?user_id=${encodeURIComponent(user_id)}`),

  agentBrief: (user_id: string) =>
    jsonFetch<{ brief: Brief; snapshot: AgentState }>(
      `/api/agent/brief?user_id=${encodeURIComponent(user_id)}`,
      { method: "POST" },
    ),

  agentGenerateNext: (user_id: string, brief?: Brief) =>
    jsonFetch<{ card: Card; brief: Brief; voice_used: string; snapshot: AgentState }>(
      "/api/agent/generate-next",
      { method: "POST", body: JSON.stringify({ user_id, brief: brief ?? null }) },
    ),

  stats: (user_id: string, voice_preferences: string[] = []) => {
    const params = new URLSearchParams({ user_id });
    for (const v of voice_preferences) params.append("voice_preferences", v);
    return jsonFetch<Stats>(`/api/agent/stats?${params.toString()}`);
  },

  agentGenerateBatch: (
    user_id: string,
    n = 4,
    voice_preferences: string[] = [],
  ) =>
    jsonFetch<{
      cards: Card[];
      slots: PlanSlot[];
      snapshot: AgentState;
      failed: number;
    }>("/api/agent/generate-batch", {
      method: "POST",
      body: JSON.stringify({ user_id, n, voice_preferences }),
    }),
};
