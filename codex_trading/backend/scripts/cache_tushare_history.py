from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.data.tushare_provider import _daily_rows, _parse_trade_date, latest_trade_date, stock_name_map  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache Tushare daily data locally.")
    parser.add_argument("--start-date", default="19900101", help="YYYYMMDD")
    parser.add_argument("--days", type=int, default=0, help="Cache the latest N natural days before end-date")
    parser.add_argument("--end-date", default="", help="YYYYMMDD, default latest Tushare trade date")
    parser.add_argument("--sleep", type=float, default=1.3, help="Seconds between uncached daily calls")
    parser.add_argument("--max-days", type=int, default=0, help="Optional safety limit for scanned natural days")
    return parser.parse_args()


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def main() -> None:
    if not os.getenv("TUSHARE_TOKEN"):
        raise SystemExit("请先设置环境变量 TUSHARE_TOKEN")

    args = parse_args()
    end = parse_date(args.end_date) if args.end_date else latest_trade_date()
    start = end - timedelta(days=args.days) if args.days else parse_date(args.start_date)
    stock_name_map()

    current = end
    scanned = 0
    cached_open_days = 0
    while current >= start:
        rows = _daily_rows(current)
        scanned += 1
        if rows:
            cached_open_days += 1
            print(f"{current:%Y%m%d} cached rows={len(rows)}", flush=True)
        if args.max_days and scanned >= args.max_days:
            break
        current -= timedelta(days=1)
        time.sleep(args.sleep)

    print(f"done scanned={scanned} open_days={cached_open_days}", flush=True)


if __name__ == "__main__":
    main()
