import sqlite3
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".thinkvault"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "thinkvault.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS topics (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT NOT NULL,
                tags      TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id   INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS insights (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id    INTEGER,
                content     TEXT NOT NULL,
                insight_type TEXT DEFAULT 'summary',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT DEFAULT '',
                content    TEXT NOT NULL,
                category   TEXT DEFAULT '其他',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        defaults = {
            "ai_provider":       "openai",
            "ai_base_url":       "https://api.openai.com/v1",
            "ai_api_key":        "",
            "ai_model":          "gpt-4o-mini",
            "ai_system_prompt":  "",
            "embedding_provider": "local",
            "embedding_base_url": "https://api.openai.com/v1",
            "embedding_api_key":  "",
            "embedding_model":    "text-embedding-3-small",
            "rag_enabled":        "true",
            "rag_top_k":          "10",
            "stream_enabled":     "true",
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )


# ── Settings ──────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )


# ── Topics ────────────────────────────────────────────────────────────────────

def create_topic(name: str, tags: list[str] | None = None) -> int:
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO topics (name, tags) VALUES (?, ?)", (name, tags_json)
        )
        return cur.lastrowid


def get_topics() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM topics ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"])
        result.append(d)
    return result


def rename_topic(topic_id: int, name: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE topics SET name=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (name, topic_id),
        )


def delete_topic(topic_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM topics WHERE id=?", (topic_id,))


def touch_topic(topic_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE topics SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (topic_id,)
        )


# ── Messages ──────────────────────────────────────────────────────────────────

def add_message(topic_id: int, role: str, content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (topic_id, role, content) VALUES (?, ?, ?)",
            (topic_id, role, content),
        )
        mid = cur.lastrowid
    touch_topic(topic_id)
    return mid


def get_messages(topic_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE topic_id=? ORDER BY created_at ASC",
            (topic_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_message(message_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE id=?", (message_id,))


# ── Insights ──────────────────────────────────────────────────────────────────

def add_insight(content: str, topic_id: int | None = None, insight_type: str = "summary") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO insights (topic_id, content, insight_type) VALUES (?, ?, ?)",
            (topic_id, content, insight_type),
        )
        return cur.lastrowid


def get_insights(topic_id: int | None = None, limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        if topic_id is not None:
            rows = conn.execute(
                "SELECT * FROM insights WHERE topic_id=? ORDER BY created_at DESC LIMIT ?",
                (topic_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM insights ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


# ── Notes ─────────────────────────────────────────────────────────────────────

def add_note(content: str, title: str = "", category: str = "其他") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notes (title, content, category) VALUES (?, ?, ?)",
            (title, content, category),
        )
        return cur.lastrowid


def get_notes(limit: int = 200, category: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM notes WHERE category=? ORDER BY created_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def delete_note(note_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
