from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Iterator

try:
    import pymysql
    from pymysql.connections import Connection
except ImportError:  # pragma: no cover - optional dependency in local test envs
    pymysql = None
    Connection = Any  # type: ignore[assignment]


DAILY_TABLE = "tushare_daily"
_SCHEMA_READY = False


def mysql_enabled() -> bool:
    return os.getenv("MARKET_DB_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


@contextmanager
def mysql_connection() -> Iterator[Connection | None]:
    if not mysql_enabled() or pymysql is None:
        yield None
        return
    try:
        connection = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "king"),
            database=os.getenv("MYSQL_DATABASE", "codex_trading"),
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=3,
            read_timeout=20,
            write_timeout=20,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception:
        yield None
        return
    try:
        ensure_schema_once(connection)
        yield connection
    finally:
        connection.close()


def ensure_schema_once(connection: Connection) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    ensure_schema(connection)
    _SCHEMA_READY = True


def ensure_schema(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DAILY_TABLE} (
                trade_date DATE NOT NULL,
                ts_code VARCHAR(16) NOT NULL,
                open_price DOUBLE NOT NULL DEFAULT 0,
                high_price DOUBLE NOT NULL DEFAULT 0,
                low_price DOUBLE NOT NULL DEFAULT 0,
                close_price DOUBLE NOT NULL DEFAULT 0,
                pre_close DOUBLE NOT NULL DEFAULT 0,
                pct_chg DOUBLE NOT NULL DEFAULT 0,
                amount DOUBLE NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (trade_date, ts_code),
                KEY idx_ts_code_date (ts_code, trade_date),
                KEY idx_trade_date_amount (trade_date, amount)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND index_name = 'idx_trade_date_amount'
            """,
            (DAILY_TABLE,),
        )
        row = cursor.fetchone()
        if not row or int(row.get("count", 0)) == 0:
            cursor.execute(f"CREATE INDEX idx_trade_date_amount ON {DAILY_TABLE} (trade_date, amount)")


def load_daily_rows(trade_date: date) -> list[dict[str, Any]] | None:
    try:
        with mysql_connection() as connection:
            if connection is None:
                return None
            rows = load_daily_rows_from_connection(connection, trade_date)
    except Exception:
        return None
    return rows


def load_daily_rows_from_connection(connection: Connection, trade_date: date) -> list[dict[str, Any]] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT trade_date, ts_code, open_price, high_price, low_price,
                   close_price, pre_close, pct_chg, amount
            FROM {DAILY_TABLE}
            WHERE trade_date = %s
            ORDER BY ts_code
            """,
            (trade_date,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return [_db_row_to_daily(row) for row in rows]


def load_market_aggregate_from_connection(connection: Connection, trade_date: date) -> dict[str, float] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) AS red_count,
                SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) AS down_count,
                SUM(CASE WHEN ts_code LIKE '%%.SH' THEN amount ELSE 0 END) / 100000 AS sh_turnover_billion,
                SUM(CASE WHEN ts_code LIKE '%%.SZ' THEN amount ELSE 0 END) / 100000 AS sz_turnover_billion
            FROM {DAILY_TABLE}
            WHERE trade_date = %s
              AND (ts_code LIKE '%%.SH' OR ts_code LIKE '%%.SZ')
            """,
            (trade_date,),
        )
        row = cursor.fetchone()
    if not row or row.get("red_count") is None:
        return None
    sh_turnover = _float(row.get("sh_turnover_billion"))
    sz_turnover = _float(row.get("sz_turnover_billion"))
    return {
        "red_count": int(row["red_count"] or 0),
        "down_count": int(row["down_count"] or 0),
        "sh_turnover_billion": sh_turnover,
        "sz_turnover_billion": sz_turnover,
        "turnover_billion": sh_turnover + sz_turnover,
    }


def load_limit_candidate_rows_from_connection(connection: Connection, trade_date: date) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT trade_date, ts_code, open_price, high_price, low_price,
                   close_price, pre_close, pct_chg, amount
            FROM {DAILY_TABLE}
            WHERE trade_date = %s
              AND (ts_code LIKE '%%.SH' OR ts_code LIKE '%%.SZ')
              AND pre_close > 0
              AND (
                (
                  (ts_code LIKE '300%%' OR ts_code LIKE '301%%' OR ts_code LIKE '688%%')
                  AND (high_price >= ROUND(pre_close * 1.20, 2) OR low_price <= ROUND(pre_close * 0.80, 2))
                )
                OR
                (
                  NOT (ts_code LIKE '300%%' OR ts_code LIKE '301%%' OR ts_code LIKE '688%%')
                  AND (high_price >= ROUND(pre_close * 1.10, 2) OR low_price <= ROUND(pre_close * 0.90, 2))
                )
              )
            """,
            (trade_date,),
        )
        rows = cursor.fetchall()
    return [_db_row_to_daily(row) for row in rows]


def load_top_amount_rows_from_connection(connection: Connection, trade_date: date, limit: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT trade_date, ts_code, open_price, high_price, low_price,
                   close_price, pre_close, pct_chg, amount
            FROM {DAILY_TABLE}
            WHERE trade_date = %s
              AND (
                ts_code LIKE '600%%.SH' OR ts_code LIKE '601%%.SH' OR ts_code LIKE '603%%.SH' OR ts_code LIKE '605%%.SH'
                OR ts_code LIKE '000%%.SZ' OR ts_code LIKE '001%%.SZ' OR ts_code LIKE '002%%.SZ'
                OR ts_code LIKE '003%%.SZ' OR ts_code LIKE '300%%.SZ' OR ts_code LIKE '301%%.SZ'
              )
            ORDER BY amount DESC
            LIMIT %s
            """,
            (trade_date, limit),
        )
        rows = cursor.fetchall()
    return [_db_row_to_daily(row) for row in rows]


def save_daily_rows(trade_date: date, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    values = [
        (
            trade_date,
            str(row.get("ts_code", "")),
            _float(row.get("open")),
            _float(row.get("high")),
            _float(row.get("low")),
            _float(row.get("close")),
            _float(row.get("pre_close")),
            _float(row.get("pct_chg")),
            _float(row.get("amount")),
        )
        for row in rows
        if row.get("ts_code")
    ]
    if not values:
        return
    try:
        with mysql_connection() as connection:
            if connection is None:
                return
            save_daily_values_from_connection(connection, values)
    except Exception:
        return


def save_daily_rows_from_connection(connection: Connection, trade_date: date, rows: list[dict[str, Any]]) -> None:
    values = [
        (
            trade_date,
            str(row.get("ts_code", "")),
            _float(row.get("open")),
            _float(row.get("high")),
            _float(row.get("low")),
            _float(row.get("close")),
            _float(row.get("pre_close")),
            _float(row.get("pct_chg")),
            _float(row.get("amount")),
        )
        for row in rows
        if row.get("ts_code")
    ]
    if values:
        save_daily_values_from_connection(connection, values)


def save_daily_values_from_connection(connection: Connection, values: list[tuple[Any, ...]]) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            f"""
            INSERT INTO {DAILY_TABLE}
                (trade_date, ts_code, open_price, high_price, low_price, close_price, pre_close, pct_chg, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                pre_close = VALUES(pre_close),
                pct_chg = VALUES(pct_chg),
                amount = VALUES(amount)
            """,
            values,
        )


def _db_row_to_daily(row: dict[str, Any]) -> dict[str, Any]:
    trade_date = row["trade_date"]
    if isinstance(trade_date, str):
        parsed = datetime.strptime(trade_date, "%Y-%m-%d").date()
    else:
        parsed = trade_date
    return {
        "ts_code": row["ts_code"],
        "trade_date": parsed.strftime("%Y%m%d"),
        "open": row["open_price"],
        "high": row["high_price"],
        "low": row["low_price"],
        "close": row["close_price"],
        "pre_close": row["pre_close"],
        "pct_chg": row["pct_chg"],
        "amount": row["amount"],
    }


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)
