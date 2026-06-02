from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_local_env
from app.data.mysql_store import DAILY_TABLE, ensure_schema, mysql_connection

REQUIRED_FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "pct_chg", "amount"]
BATCH_SIZE = 5000


def main() -> None:
    load_local_env()
    cache_dir = _cache_dir()
    if not cache_dir.exists():
        raise SystemExit(f"cache dir not found: {cache_dir}")

    with mysql_connection() as connection:
        if connection is None:
            raise SystemExit("mysql connection unavailable")
        ensure_schema(connection)
        batch: list[tuple[Any, ...]] = []
        total_rows = 0
        total_files = 0
        for path in cache_dir.glob("*.json"):
            rows = _rows_from_file(path)
            if not rows:
                continue
            total_files += 1
            batch.extend(rows)
            if len(batch) >= BATCH_SIZE:
                total_rows += _flush(connection, batch)
                batch.clear()
        if batch:
            total_rows += _flush(connection, batch)
        print(f"imported_rows={total_rows} source_files={total_files}")


def _rows_from_file(path: Path) -> list[tuple[Any, ...]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    fields = payload.get("fields") or []
    items = payload.get("items") or []
    if not items or not all(field in fields for field in REQUIRED_FIELDS):
        return []
    index = {field: fields.index(field) for field in REQUIRED_FIELDS}
    rows = []
    for item in items:
        try:
            rows.append(
                (
                    _date_value(str(item[index["trade_date"]])),
                    str(item[index["ts_code"]]),
                    _float(item[index["open"]]),
                    _float(item[index["high"]]),
                    _float(item[index["low"]]),
                    _float(item[index["close"]]),
                    _float(item[index["pre_close"]]),
                    _float(item[index["pct_chg"]]),
                    _float(item[index["amount"]]),
                )
            )
        except Exception:
            continue
    return rows


def _flush(connection, rows: list[tuple[Any, ...]]) -> int:
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
            rows,
        )
    return len(rows)


def _date_value(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _cache_dir() -> Path:
    candidates = [
        ROOT / "cache" / "tushare" / "daily",
        PROJECT_ROOT / "cache" / "tushare" / "daily",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


if __name__ == "__main__":
    main()
