from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_DAILY_QUOTA = 5
ALLOWED_RESONANCE_REACTIONS = {
    "我也有过",
    "抱抱你",
    "愿你今晚轻一点",
    "你不是一个人",
    "希望明天会好一点",
}


def _db_path() -> Path:
    raw = os.getenv("APP_DB_PATH", "/opt/emotion_app/backend/data/app.db")
    return Path(raw)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                recovery_code TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_quotas (
                user_id TEXT NOT NULL,
                quota_date TEXT NOT NULL,
                remaining INTEGER NOT NULL,
                PRIMARY KEY (user_id, quota_date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resonance_notes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                mood_label TEXT NOT NULL,
                content TEXT NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resonance_reactions (
                note_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reaction TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (note_id, user_id),
                FOREIGN KEY (note_id) REFERENCES resonance_notes(id)
            )
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _new_recovery_code() -> str:
    return secrets.token_hex(3).upper()


def ensure_user(user_id: str) -> dict[str, str | int]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT user_id, recovery_code FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            recovery_code = _new_recovery_code()
            while conn.execute(
                "SELECT 1 FROM users WHERE recovery_code = ?",
                (recovery_code,),
            ).fetchone():
                recovery_code = _new_recovery_code()
            conn.execute(
                """
                INSERT INTO users (user_id, recovery_code, created_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, recovery_code, _now(), _now()),
            )
        else:
            recovery_code = str(row["recovery_code"])
            conn.execute(
                "UPDATE users SET last_seen_at = ? WHERE user_id = ?",
                (_now(), user_id),
            )
        remaining = quota_remaining(conn, user_id)
        return {
            "user_id": user_id,
            "recovery_code": recovery_code,
            "quota_remaining": remaining,
        }


def quota_remaining(conn: sqlite3.Connection, user_id: str) -> int:
    quota_date = _today()
    row = conn.execute(
        "SELECT remaining FROM daily_quotas WHERE user_id = ? AND quota_date = ?",
        (user_id, quota_date),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO daily_quotas (user_id, quota_date, remaining)
            VALUES (?, ?, ?)
            """,
            (user_id, quota_date, DEFAULT_DAILY_QUOTA),
        )
        return DEFAULT_DAILY_QUOTA
    return int(row["remaining"])


def consume_quota(user_id: str) -> tuple[bool, int]:
    profile = ensure_user(user_id)
    user_id = str(profile["user_id"])
    with _connect() as conn:
        remaining = quota_remaining(conn, user_id)
        if remaining <= 0:
            return False, 0
        next_remaining = remaining - 1
        conn.execute(
            """
            UPDATE daily_quotas
            SET remaining = ?
            WHERE user_id = ? AND quota_date = ?
            """,
            (next_remaining, user_id, _today()),
        )
        return True, next_remaining


def _reaction_counts(conn: sqlite3.Connection, note_id: str) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT reaction, COUNT(*) AS count
        FROM resonance_reactions
        WHERE note_id = ?
        GROUP BY reaction
        """,
        (note_id,),
    ).fetchall()
    return {str(row["reaction"]): int(row["count"]) for row in rows}


def _note_payload(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, str | dict[str, int]]:
    note_id = str(row["id"])
    return {
        "id": note_id,
        "mood_label": str(row["mood_label"]),
        "content": str(row["content"]),
        "created_at": str(row["created_at"]),
        "reactions": _reaction_counts(conn, note_id),
    }


def create_resonance_note(
    *, user_id: str, mood_label: str, content: str
) -> dict[str, str | dict[str, int]]:
    ensure_user(user_id)
    note_id = secrets.token_urlsafe(12)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO resonance_notes
                (id, user_id, mood_label, content, hidden, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (note_id, user_id, mood_label, content.strip(), _now()),
        )
        row = conn.execute(
            "SELECT * FROM resonance_notes WHERE id = ?",
            (note_id,),
        ).fetchone()
        return _note_payload(conn, row)


def random_resonance_note(
    *, user_id: str, mood_label: str | None = None
) -> dict[str, str | dict[str, int]] | None:
    ensure_user(user_id)
    with _connect() as conn:
        params: list[str] = [user_id]
        mood_clause = ""
        if mood_label:
            mood_clause = "AND mood_label = ?"
            params.append(mood_label)
        row = conn.execute(
            f"""
            SELECT *
            FROM resonance_notes
            WHERE hidden = 0
              AND user_id != ?
              {mood_clause}
            ORDER BY RANDOM()
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
        if row is None and mood_label:
            row = conn.execute(
                """
                SELECT *
                FROM resonance_notes
                WHERE hidden = 0
                  AND user_id != ?
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return _note_payload(conn, row)


def add_resonance_reaction(
    *, note_id: str, user_id: str, reaction: str
) -> dict[str, int]:
    if reaction not in ALLOWED_RESONANCE_REACTIONS:
        raise ValueError("unsupported reaction")
    ensure_user(user_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO resonance_reactions
                (note_id, user_id, reaction, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(note_id, user_id)
            DO UPDATE SET reaction = excluded.reaction, created_at = excluded.created_at
            """,
            (note_id, user_id, reaction, _now()),
        )
        return _reaction_counts(conn, note_id)
