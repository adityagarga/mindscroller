"""SQLite client. Single-file DB. Sync API is fine for hackathon scale —
swap in aiosqlite if any endpoint shows up in flame graphs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.config import DB_PATH


_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA_PATH.read_text())
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight SQLite migrations. Idempotent — safe to run on every boot."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(cards)").fetchall()}
    if "version" not in cols:
        conn.execute("ALTER TABLE cards ADD COLUMN version TEXT NOT NULL DEFAULT 'v0'")
    if "voice" not in cols:
        conn.execute("ALTER TABLE cards ADD COLUMN voice TEXT")
    # Always (re)create indexes; idempotent.
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_version ON cards(version)")
    # Backfill any row that somehow ended up with a blank version (e.g. earlier
    # builds that didn't write the column at insert time).
    conn.execute("UPDATE cards SET version = 'v0' WHERE version IS NULL OR version = ''")


def insert_card(row: dict[str, Any]) -> None:
    cols = list(row.keys())
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    values = [
        json.dumps(v) if isinstance(v, (list, dict)) else v
        for v in row.values()
    ]
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO cards ({col_list}) VALUES ({placeholders})",
            values,
        )


def get_card(card_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        row = cur.fetchone()
    return _row_to_card(row) if row else None


def list_cards(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM cards ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    return [_row_to_card(r) for r in rows]


def sample_existing_cards(
    topics: list[str] | None = None,
    categories: list[str] | None = None,
    limit: int = 10,
    version: str | None = None,
) -> list[dict[str, Any]]:
    """Return the latest cards matching any of `topics` AND any of `categories`.
    Either / both / neither can be passed. If `version` is provided, filter by it.
    Used to seed a new user's queue without generating fresh content."""
    clauses: list[str] = []
    params: list[Any] = []
    if topics:
        placeholders = ",".join("?" * len(topics))
        clauses.append(f"topic IN ({placeholders})")
        params.extend(topics)
    if categories:
        placeholders = ",".join("?" * len(categories))
        clauses.append(f"category IN ({placeholders})")
        params.extend(categories)
    if version is not None:
        clauses.append("version = ?")
        params.append(version)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM cards {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_card(r) for r in rows]


def _row_to_card(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def insert_interaction(
    user_id: str,
    card_id: str,
    event_type: str,
    view_duration_ms: int | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO interactions (user_id, card_id, event_type, view_duration_ms) VALUES (?, ?, ?, ?)",
            (user_id, card_id, event_type, view_duration_ms),
        )


def insert_user(user_id: str, topic_preferences: list[str]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (id, topic_preferences) VALUES (?, ?)",
            (user_id, json.dumps(topic_preferences)),
        )


def enqueue_cards(user_id: str, card_ids: Iterable[str], start_position: int = 0) -> None:
    with _connect() as conn:
        for i, cid in enumerate(card_ids):
            conn.execute(
                "INSERT OR REPLACE INTO feed_queue (user_id, card_id, position) VALUES (?, ?, ?)",
                (user_id, cid, start_position + i),
            )


def get_user(user_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for col in ("topic_preferences", "topic_affinity"):
        try:
            d[col] = json.loads(d[col]) if d.get(col) else ([] if col == "topic_preferences" else {})
        except (TypeError, json.JSONDecodeError):
            d[col] = [] if col == "topic_preferences" else {}
    return d


def get_feed(
    user_id: str,
    offset: int = 0,
    limit: int = 20,
    version: str | None = None,
) -> list[dict[str, Any]]:
    """Return ordered queue entries joined with full card rows. If `version`
    is provided, only cards with that version are included."""
    sql = """
        SELECT c.*
        FROM feed_queue q
        JOIN cards c ON c.id = q.card_id
        WHERE q.user_id = ?
    """
    params: list[Any] = [user_id]
    if version is not None:
        sql += " AND c.version = ?"
        params.append(version)
    sql += " ORDER BY q.position ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_card(r) for r in rows]


def feed_length(user_id: str, version: str | None = None) -> int:
    sql = """
        SELECT COUNT(*)
        FROM feed_queue q
        JOIN cards c ON c.id = q.card_id
        WHERE q.user_id = ?
    """
    params: list[Any] = [user_id]
    if version is not None:
        sql += " AND c.version = ?"
        params.append(version)
    with _connect() as conn:
        n = conn.execute(sql, params).fetchone()[0]
    return int(n)


def next_position(user_id: str) -> int:
    """Next free position in the user's feed_queue (max(position)+1, or 0 if empty)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM feed_queue WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row[0]) + 1


# ----------------- discovered topics -----------------


def record_discovered_topic(category: str, topic: str, proposed_by_user: str | None) -> bool:
    """Insert a topic into discovered_topics if it's not already there.
    Returns True if newly inserted, False if it already existed (use_count bumped either way)."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT 1 FROM discovered_topics WHERE category = ? AND topic = ?",
            (category, topic),
        )
        existed = cur.fetchone() is not None
        if not existed:
            conn.execute(
                "INSERT INTO discovered_topics (category, topic, proposed_by_user, use_count) VALUES (?, ?, ?, 1)",
                (category, topic, proposed_by_user),
            )
        else:
            conn.execute(
                "UPDATE discovered_topics SET use_count = use_count + 1 WHERE category = ? AND topic = ?",
                (category, topic),
            )
    return not existed


def list_discovered_topics() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT category, topic, first_seen_at, use_count FROM discovered_topics ORDER BY first_seen_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ----------------- interactions readback (for affinity) -----------------


def recent_interactions_with_cards(user_id: str, limit: int = 25) -> list[dict[str, Any]]:
    """Latest interactions for a user, joined with the card so we can show
    the visual_hook + topic in the dashboard / brief context."""
    sql = """
        SELECT
            i.id, i.event_type, i.view_duration_ms, i.created_at,
            c.id AS card_id, c.category, c.topic, c.hook_type, c.visual_hook, c.voice
        FROM interactions i
        JOIN cards c ON c.id = i.card_id
        WHERE i.user_id = ?
        ORDER BY i.id DESC
        LIMIT ?
    """
    with _connect() as conn:
        rows = conn.execute(sql, (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def affinity_breakdown(user_id: str) -> dict[str, list[dict[str, Any]]]:
    """Aggregate weighted scores per dimension (category / topic / hook_type / voice).
    Weights: like +3, complete +1, view +0.3, dislike -3, skip -1, dismiss -2."""
    weight_case = """
        CASE i.event_type
            WHEN 'like' THEN 3.0
            WHEN 'complete' THEN 1.0
            WHEN 'view' THEN 0.3
            WHEN 'dislike' THEN -3.0
            WHEN 'skip' THEN -1.0
            WHEN 'dismiss' THEN -2.0
            ELSE 0
        END
    """
    out: dict[str, list[dict[str, Any]]] = {}
    with _connect() as conn:
        for dim in ("category", "topic", "hook_type", "voice"):
            sql = f"""
                SELECT
                    c.{dim} AS bucket,
                    SUM({weight_case}) AS score,
                    COUNT(*) AS interactions,
                    SUM(CASE i.event_type WHEN 'like' THEN 1 ELSE 0 END) AS likes,
                    SUM(CASE i.event_type WHEN 'dislike' THEN 1 ELSE 0 END) AS dislikes
                FROM interactions i
                JOIN cards c ON c.id = i.card_id
                WHERE i.user_id = ? AND c.{dim} IS NOT NULL AND c.{dim} != ''
                GROUP BY c.{dim}
                ORDER BY score DESC
            """
            rows = conn.execute(sql, (user_id,)).fetchall()
            out[dim] = [
                {
                    "bucket": r[0],
                    "score": round(float(r[1] or 0), 2),
                    "interactions": int(r[2]),
                    "likes": int(r[3]),
                    "dislikes": int(r[4]),
                }
                for r in rows
            ]
    return out


def interaction_count(user_id: str) -> int:
    with _connect() as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
        )


def watch_and_engagement_stats(user_id: str) -> dict[str, Any]:
    """Per-category and per-subtopic stats: total watch_ms (from completed
    intersections), like counts, dislike counts. Used by the dashboard."""
    cat_sql = """
        SELECT
            c.category AS category,
            COALESCE(SUM(CASE WHEN i.event_type = 'complete' THEN i.view_duration_ms ELSE 0 END), 0) AS watch_ms,
            SUM(CASE WHEN i.event_type = 'like' THEN 1 ELSE 0 END) AS likes,
            SUM(CASE WHEN i.event_type = 'dislike' THEN 1 ELSE 0 END) AS dislikes,
            COUNT(DISTINCT i.card_id) AS cards_seen
        FROM interactions i
        JOIN cards c ON c.id = i.card_id
        WHERE i.user_id = ?
        GROUP BY c.category
    """
    topic_sql = """
        SELECT
            c.category, c.topic,
            COALESCE(SUM(CASE WHEN i.event_type = 'complete' THEN i.view_duration_ms ELSE 0 END), 0) AS watch_ms,
            SUM(CASE WHEN i.event_type = 'like' THEN 1 ELSE 0 END) AS likes,
            SUM(CASE WHEN i.event_type = 'dislike' THEN 1 ELSE 0 END) AS dislikes,
            COUNT(DISTINCT i.card_id) AS cards_seen
        FROM interactions i
        JOIN cards c ON c.id = i.card_id
        WHERE i.user_id = ?
        GROUP BY c.category, c.topic
    """
    with _connect() as conn:
        cat_rows = conn.execute(cat_sql, (user_id,)).fetchall()
        topic_rows = conn.execute(topic_sql, (user_id,)).fetchall()

    total_watch_ms = sum(int(r["watch_ms"]) for r in cat_rows)

    # Bucket topics under their parent category for easy nested rendering.
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in topic_rows:
        cat = r["category"]
        watch_ms = int(r["watch_ms"])
        by_cat.setdefault(cat, []).append(
            {
                "name": r["topic"],
                "watch_ms": watch_ms,
                "watch_percentage": (100.0 * watch_ms / total_watch_ms) if total_watch_ms else 0.0,
                "likes": int(r["likes"]),
                "dislikes": int(r["dislikes"]),
                "cards_seen": int(r["cards_seen"]),
            }
        )

    categories: list[dict[str, Any]] = []
    for r in cat_rows:
        cat = r["category"]
        watch_ms = int(r["watch_ms"])
        subs = sorted(by_cat.get(cat, []), key=lambda s: s["watch_ms"], reverse=True)
        categories.append(
            {
                "name": cat,
                "watch_ms": watch_ms,
                "watch_percentage": (100.0 * watch_ms / total_watch_ms) if total_watch_ms else 0.0,
                "likes": int(r["likes"]),
                "dislikes": int(r["dislikes"]),
                "cards_seen": int(r["cards_seen"]),
                "subtopics": subs,
            }
        )
    categories.sort(key=lambda c: c["watch_ms"], reverse=True)

    return {
        "categories": categories,
        "total_watch_ms": total_watch_ms,
        "total_likes": sum(c["likes"] for c in categories),
        "total_dislikes": sum(c["dislikes"] for c in categories),
        "total_cards_seen": sum(c["cards_seen"] for c in categories),
    }
