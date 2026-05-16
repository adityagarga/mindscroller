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
