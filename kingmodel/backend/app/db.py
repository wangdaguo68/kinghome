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
CREATE TABLE IF NOT EXISTS market_bars (
  code TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  payload TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (code, trade_date)
);
CREATE TABLE IF NOT EXISTS model_registry (
  model_id INTEGER PRIMARY KEY AUTOINCREMENT,
  task TEXT NOT NULL,
  segment TEXT NOT NULL,
  version TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  sample_count INTEGER NOT NULL,
  artifact TEXT NOT NULL,
  metrics TEXT NOT NULL,
  trained_at TEXT NOT NULL,
  UNIQUE (task, segment, version)
);
CREATE INDEX IF NOT EXISTS idx_model_registry_role ON model_registry(task, segment, role, status);
CREATE TABLE IF NOT EXISTS training_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL UNIQUE,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  sample_count INTEGER NOT NULL DEFAULT 0,
  report TEXT NOT NULL DEFAULT '{}',
  error TEXT
);
CREATE TABLE IF NOT EXISTS model_predictions (
  trade_date TEXT NOT NULL,
  model_version TEXT NOT NULL,
  task TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (trade_date, model_version, task, entity_id)
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


def _compact_trade_date(value: Any) -> str:
    return str(value or "").replace(".", "").replace("-", "")


def _has_reliable_market_context(payload: dict[str, Any]) -> bool:
    breadth = payload.get("breadth") or {}
    capacity = payload.get("capacity") or {}
    return int(breadth.get("eligible") or 0) > 0 and int(capacity.get("sample") or 0) > 0


def latest_reliable_snapshot_before(trade_date: str) -> dict[str, Any] | None:
    """Return the newest official snapshot before trade_date with usable breadth/capacity context."""
    target = _compact_trade_date(trade_date)
    with connect() as conn:
        rows = conn.execute("SELECT payload FROM snapshots WHERE is_official=1 ORDER BY id DESC LIMIT 200").fetchall()
    for row in rows:
        payload = json.loads(row["payload"])
        payload_date = _compact_trade_date(payload.get("meta", {}).get("trade_date"))
        if not payload_date or payload_date >= target:
            continue
        if _has_reliable_market_context(payload):
            return payload
    return None


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


def load_pending_shadow_plans() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT s.trade_date,s.plan_version,s.code,s.payload "
            "FROM shadow_plans s WHERE NOT EXISTS ("
            "SELECT 1 FROM plan_outcomes o WHERE o.trade_date=s.trade_date AND o.plan_version=s.plan_version "
            "AND o.code=s.code AND o.horizon=10) ORDER BY s.trade_date,s.rank"
        ).fetchall()
    return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]


def upsert_market_bars(code: str, rows: list[dict[str, Any]], source: str, created_at: str) -> None:
    with connect() as conn:
        conn.executemany(
            "INSERT INTO market_bars(code,trade_date,payload,source,created_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(code,trade_date) DO UPDATE SET payload=excluded.payload,source=excluded.source,created_at=excluded.created_at",
            [(code, str(row["trade_date"]), json.dumps(row, ensure_ascii=False), source, created_at) for row in rows],
        )


def load_market_bars(code: str, after_trade_date: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT payload FROM market_bars WHERE code=? AND trade_date>? ORDER BY trade_date",
            (code, after_trade_date),
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def save_plan_outcomes(
    trade_date: str, plan_version: str, code: str, outcomes: list[tuple[int, dict[str, Any]]], completed_at: str
) -> None:
    with connect() as conn:
        conn.executemany(
            "INSERT INTO plan_outcomes(trade_date,plan_version,code,horizon,payload,completed_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(trade_date,plan_version,code,horizon) DO UPDATE SET payload=excluded.payload,completed_at=excluded.completed_at",
            [
                (trade_date, plan_version, code, horizon, json.dumps(payload, ensure_ascii=False), completed_at)
                for horizon, payload in outcomes
            ],
        )


def load_training_rows(horizon: int = 1) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT f.trade_date,f.entity_id,f.payload AS features,o.payload AS outcome "
            "FROM feature_snapshots f JOIN plan_outcomes o ON o.trade_date=f.trade_date AND o.code=f.entity_id "
            "WHERE f.scope='stock' AND o.horizon=? ORDER BY f.trade_date,f.entity_id",
            (horizon,),
        ).fetchall()
    return [
        {"trade_date": row["trade_date"], "code": row["entity_id"], "features": json.loads(row["features"]), "outcome": json.loads(row["outcome"])}
        for row in rows
    ]


def load_feature_scope(scope: str, feature_version: str = "rule-v1") -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT trade_date,entity_id,payload FROM feature_snapshots WHERE scope=? AND feature_version=? ORDER BY trade_date,entity_id",
            (scope, feature_version),
        ).fetchall()
    return [
        {"trade_date": row["trade_date"], "entity_id": row["entity_id"], "payload": json.loads(row["payload"])}
        for row in rows
    ]


def start_training_run(version: str, started_at: str) -> bool:
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO training_runs(version,started_at,status) VALUES(?,?,'running')",
                (version, started_at),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def finish_training_run(version: str, status: str, finished_at: str, sample_count: int, report: dict[str, Any], error: str | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE training_runs SET finished_at=?,status=?,sample_count=?,report=?,error=? WHERE version=?",
            (finished_at, status, sample_count, json.dumps(report, ensure_ascii=False), error, version),
        )


def register_model(model: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO model_registry(task,segment,version,role,status,feature_version,sample_count,artifact,metrics,trained_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(task,segment,version) DO UPDATE SET "
            "role=excluded.role,status=excluded.status,sample_count=excluded.sample_count,artifact=excluded.artifact,metrics=excluded.metrics,trained_at=excluded.trained_at",
            (
                model["task"], model["segment"], model["version"], model["role"], model["status"],
                model["feature_version"], model["sample_count"], json.dumps(model["artifact"], ensure_ascii=False),
                json.dumps(model["metrics"], ensure_ascii=False), model["trained_at"],
            ),
        )


def champion_model(task: str, segment: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM model_registry WHERE task=? AND segment=? AND role='champion' AND status='active' ORDER BY model_id DESC LIMIT 1",
            (task, segment),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["artifact"] = json.loads(result["artifact"])
    result["metrics"] = json.loads(result["metrics"])
    return result


def promote_model(task: str, segment: str, version: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE model_registry SET role='archived',status='inactive' WHERE task=? AND segment=? AND role='champion'",
            (task, segment),
        )
        conn.execute(
            "UPDATE model_registry SET role='champion',status='active' WHERE task=? AND segment=? AND version=?",
            (task, segment, version),
        )


def model_system_status() -> dict[str, Any]:
    feature = feature_store_status()
    with connect() as conn:
        models = conn.execute(
            "SELECT task,segment,version,role,status,sample_count,metrics,trained_at FROM model_registry ORDER BY model_id DESC"
        ).fetchall()
        last_run = conn.execute("SELECT * FROM training_runs ORDER BY run_id DESC LIMIT 1").fetchone()
    days = int(feature["outcome_days"] or 0)
    stage = "rule_only" if days < 20 else "shadow_learning" if days < 60 else "assisted" if days < 120 else "live_eligible"
    return {
        **feature,
        "stage": stage,
        "minimum_train_days": 20,
        "assisted_days": 60,
        "live_eligible_days": 120,
        "models": [{**dict(row), "metrics": json.loads(row["metrics"])} for row in models],
        "last_training_run": ({**dict(last_run), "report": json.loads(last_run["report"])} if last_run else None),
    }


def outcome_review(limit: int = 100) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT o.trade_date,o.code,o.horizon,o.payload,s.payload AS plan "
            "FROM plan_outcomes o LEFT JOIN shadow_plans s ON s.trade_date=o.trade_date AND s.plan_version=o.plan_version AND s.code=o.code "
            "ORDER BY o.trade_date DESC,o.horizon,o.code LIMIT ?",
            (limit,),
        ).fetchall()
    items = []
    for row in rows:
        outcome = json.loads(row["payload"])
        plan = json.loads(row["plan"]) if row["plan"] else {}
        items.append({"trade_date": row["trade_date"], "code": row["code"], "name": plan.get("name", row["code"]), "rank": plan.get("rank"), "horizon": row["horizon"], **outcome})
    summary = []
    for horizon in (1, 3, 5, 10):
        values = [item for item in items if item["horizon"] == horizon and item.get("tradable")]
        returns = [float(item.get("net_return") or 0) for item in values]
        summary.append({
            "horizon": horizon, "samples": len(values),
            "win_rate": round(sum(value > 0 for value in returns) / len(returns), 4) if returns else None,
            "average_return": round(sum(returns) / len(returns), 6) if returns else None,
        })
    return {"summary": summary, "items": items}


def snapshot_history(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, trade_date, source, freshness, is_official FROM snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
