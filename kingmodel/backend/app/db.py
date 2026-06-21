import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  source TEXT NOT NULL,
  freshness TEXT NOT NULL,
  is_official INTEGER NOT NULL DEFAULT 0,
  payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON snapshots(created_at DESC);
CREATE TABLE IF NOT EXISTS collection_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  error TEXT
);
CREATE TABLE IF NOT EXISTS sentiment_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  published_at TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  sector TEXT,
  summary TEXT,
  credibility TEXT NOT NULL,
  heat INTEGER NOT NULL DEFAULT 0
);
"""


def initialize() -> None:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(get_settings().database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_snapshot(payload: dict[str, Any], *, official: bool = False) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO snapshots(created_at, trade_date, source, freshness, is_official, payload) VALUES(?,?,?,?,?,?)",
            (
                payload["meta"]["updated_at"],
                payload["meta"]["trade_date"],
                payload["meta"]["source"],
                payload["meta"]["freshness"],
                int(official),
                json.dumps(payload, ensure_ascii=False),
            ),
        )


def latest_snapshot() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT payload FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row["payload"]) if row else None


def snapshot_history(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, trade_date, source, freshness, is_official FROM snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
