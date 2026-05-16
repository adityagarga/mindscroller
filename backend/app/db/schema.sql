CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  created_at TEXT DEFAULT (datetime('now')),
  topic_preferences TEXT DEFAULT '[]',
  topic_affinity TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  topic TEXT NOT NULL,
  hook_type TEXT NOT NULL,
  visual_hook TEXT NOT NULL,
  script TEXT NOT NULL,
  image_prompt TEXT NOT NULL,
  image_path TEXT,
  audio_path TEXT,
  parent_card_id TEXT,
  thread_order INTEGER,
  created_for_user TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cards_category ON cards(category);
CREATE INDEX IF NOT EXISTS idx_cards_topic ON cards(topic);
CREATE INDEX IF NOT EXISTS idx_cards_parent ON cards(parent_card_id);

CREATE TABLE IF NOT EXISTS interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  card_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  view_duration_ms INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_interactions_user_time ON interactions(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS feed_queue (
  user_id TEXT NOT NULL,
  card_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  PRIMARY KEY (user_id, card_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_queue_user_pos ON feed_queue(user_id, position);
