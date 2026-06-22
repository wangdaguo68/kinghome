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
CREATE TABLE IF NOT EXISTS daily_collection_jobs (
  trade_date TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  free_attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT
);
CREATE TABLE IF NOT EXISTS limit_up_daily_pool (
  trade_date TEXT NOT NULL,
  code TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (trade_date, code)
);
CREATE TABLE IF NOT EXISTS limit_up_cause_cache (
  trade_date TEXT NOT NULL,
  code TEXT NOT NULL,
  payload TEXT NOT NULL,
  tdx_used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  PRIMARY KEY (trade_date, code)
);
CREATE TABLE IF NOT EXISTS tdx_call_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trade_date TEXT NOT NULL,
  code TEXT NOT NULL,
  purpose TEXT NOT NULL,
  called_at TEXT NOT NULL,
  status TEXT NOT NULL,
  UNIQUE (trade_date, code, purpose)
);
CREATE INDEX IF NOT EXISTS idx_tdx_call_audit_date ON tdx_call_audit(trade_date);
CREATE TABLE IF NOT EXISTS feature_snapshots (
  trade_date TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  scope TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (trade_date, feature_version, scope, entity_id)
);
CREATE TABLE IF NOT EXISTS shadow_plans (
  trade_date TEXT NOT NULL,
  plan_version TEXT NOT NULL,
  rank INTEGER NOT NULL,
  code TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (trade_date, plan_version, code)
);
CREATE TABLE IF NOT EXISTS plan_outcomes (
  trade_date TEXT NOT NULL,
  plan_version TEXT NOT NULL,
  code TEXT NOT NULL,
  horizon INTEGER NOT NULL,
  payload TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY (trade_date, plan_version, code, horizon)
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


def latest_published_snapshot() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT payload FROM snapshots WHERE is_official=1 ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row["payload"]) if row else None


def latest_trusted_snapshot() -> dict[str, Any] | None:
    published = latest_published_snapshot()
    if published:
        return published
    with connect() as conn:
        rows = conn.execute("SELECT payload FROM snapshots ORDER BY id DESC LIMIT 1000").fetchall()
    for row in rows:
        payload = json.loads(row["payload"])
        if payload.get("meta", {}).get("freshness") == "live" and payload.get("ladder"):
            return payload
    return json.loads(rows[0]["payload"]) if rows else None


def upsert_daily_pool(trade_date: str, rows: list[dict[str, Any]]) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM limit_up_daily_pool WHERE trade_date=?", (trade_date,))
        conn.executemany(
            "INSERT INTO limit_up_daily_pool(trade_date,code,payload) VALUES(?,?,?)",
            [(trade_date, str(row["code"]), json.dumps(row, ensure_ascii=False)) for row in rows],
        )


def load_daily_pools(trade_dates: list[str]) -> dict[str, list[dict[str, Any]]]:
    pools = {trade_date: [] for trade_date in trade_dates}
    if not trade_dates:
        return pools
    placeholders = ",".join("?" for _ in trade_dates)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT trade_date,payload FROM limit_up_daily_pool WHERE trade_date IN ({placeholders})",
            trade_dates,
        ).fetchall()
    for row in rows:
        pools[row["trade_date"]].append(json.loads(row["payload"]))
    return pools


def start_collection_job(trade_date: str, started_at: str) -> bool:
    with connect() as conn:
        existing = conn.execute("SELECT status FROM daily_collection_jobs WHERE trade_date=?", (trade_date,)).fetchone()
        if existing and existing["status"] in {"running", "published"}:
            return False
        conn.execute(
            "INSERT INTO daily_collection_jobs(trade_date,status,started_at,free_attempts) VALUES(?, 'running', ?, 1) "
            "ON CONFLICT(trade_date) DO UPDATE SET status='running',started_at=excluded.started_at,free_attempts=free_attempts+1,error=NULL",
            (trade_date, started_at),
        )
    return True


def finish_collection_job(trade_date: str, status: str, finished_at: str, error: str | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE daily_collection_jobs SET status=?,finished_at=?,error=? WHERE trade_date=?",
            (status, finished_at, error, trade_date),
        )


def collection_status(trade_date: str, daily_limit: int) -> dict[str, Any]:
    with connect() as conn:
        job = conn.execute("SELECT * FROM daily_collection_jobs WHERE trade_date=?", (trade_date,)).fetchone()
        calls = conn.execute(
            "SELECT code,called_at,status FROM tdx_call_audit WHERE trade_date=? ORDER BY id",
            (trade_date,),
        ).fetchall()
    return {
        "trade_date": trade_date,
        "job": dict(job) if job else None,
        "tdx_calls_used": len(calls),
        "tdx_daily_limit": daily_limit,
        "tdx_calls": [dict(row) for row in calls],
    }


def reserve_tdx_call(trade_date: str, code: str, purpose: str, called_at: str, daily_limit: int) -> bool:
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT 1 FROM tdx_call_audit WHERE trade_date=? AND code=? AND purpose=?",
            (trade_date, code, purpose),
        ).fetchone()
        used = conn.execute("SELECT COUNT(*) AS count FROM tdx_call_audit WHERE trade_date=?", (trade_date,)).fetchone()["count"]
        if existing or used >= daily_limit:
            return False
        conn.execute(
            "INSERT INTO tdx_call_audit(trade_date,code,purpose,called_at,status) VALUES(?,?,?,?, 'reserved')",
            (trade_date, code, purpose, called_at),
        )
    return True


def complete_tdx_call(trade_date: str, code: str, purpose: str, status: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE tdx_call_audit SET status=? WHERE trade_date=? AND code=? AND purpose=?",
            (status, trade_date, code, purpose),
        )


def get_cause_cache(trade_date: str, code: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT payload FROM limit_up_cause_cache WHERE trade_date=? AND code=?",
            (trade_date, code),
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def save_cause_cache(trade_date: str, code: str, payload: dict[str, Any], tdx_used: bool, created_at: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO limit_up_cause_cache(trade_date,code,payload,tdx_used,created_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(trade_date,code) DO UPDATE SET payload=excluded.payload,tdx_used=excluded.tdx_used,created_at=excluded.created_at",
            (trade_date, code, json.dumps(payload, ensure_ascii=False), int(tdx_used), created_at),
        )


def save_feature_snapshots(
    trade_date: str,
    feature_version: str,
    snapshots: list[tuple[str, str, dict[str, Any]]],
    created_at: str,
) -> None:
    with connect() as conn:
        conn.executemany(
            "INSERT INTO feature_snapshots(trade_date,feature_version,scope,entity_id,payload,created_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(trade_date,feature_version,scope,entity_id) DO UPDATE SET payload=excluded.payload,created_at=excluded.created_at",
            [
                (trade_date, feature_version, scope, entity_id, json.dumps(payload, ensure_ascii=False), created_at)
                for scope, entity_id, payload in snapshots
            ],
        )


def save_shadow_plans(trade_date: str, plan_version: str, plans: list[dict[str, Any]], created_at: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM shadow_plans WHERE trade_date=? AND plan_version=?", (trade_date, plan_version))
        conn.executemany(
            "INSERT INTO shadow_plans(trade_date,plan_version,rank,code,payload,created_at) VALUES(?,?,?,?,?,?)",
            [
                (trade_date, plan_version, index + 1, str(plan["code"]), json.dumps(plan, ensure_ascii=False), created_at)
                for index, plan in enumerate(plans)
            ],
        )


def feature_store_status() -> dict[str, Any]:
    with connect() as conn:
        feature_days = conn.execute("SELECT COUNT(DISTINCT trade_date) AS count FROM feature_snapshots").fetchone()["count"]
        outcome_days = conn.execute("SELECT COUNT(DISTINCT trade_date) AS count FROM plan_outcomes").fetchone()["count"]
        latest = conn.execute("SELECT trade_date,feature_version FROM feature_snapshots ORDER BY trade_date DESC LIMIT 1").fetchone()
    return {
        "feature_days": feature_days,
        "outcome_days": outcome_days,
        "latest_trade_date": latest["trade_date"] if latest else None,
        "feature_version": latest["feature_version"] if latest else None,
    }


def snapshot_history(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, trade_date, source, freshness, is_official FROM snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
