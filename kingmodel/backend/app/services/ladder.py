from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def normalize_trade_date(value: str) -> str:
    compact = str(value).strip().replace("-", "").replace(".", "").replace("/", "")
    return compact if len(compact) == 8 and compact.isdigit() else ""


@dataclass(frozen=True)
class LadderMetrics:
    consecutive: int
    recent_limit_count: int
    recent_window_days: int


def trade_dates_from_tdx_kline(payload: dict[str, Any], target_date: str, count: int = 15) -> list[str]:
    target = normalize_trade_date(target_date)
    headers = payload.get("ListHead", {}).get("ItemHead", [])
    try:
        date_index = headers.index("Data")
    except ValueError:
        date_index = 0
    dates: set[str] = set()
    for entry in payload.get("ListItem", []):
        values = entry.get("Item", [])
        if len(values) <= date_index:
            continue
        trade_date = normalize_trade_date(str(values[date_index]))
        if trade_date and trade_date <= target:
            dates.add(trade_date)
    ordered = sorted(dates, reverse=True)[:count]
    if not target or not ordered or ordered[0] != target:
        raise ValueError(f"通达信K线缺少目标交易日 {target or target_date}")
    return ordered


def calculate_ladder_metrics(
    limit_dates: list[str],
    trade_dates: list[str],
    target_date: str,
    window_days: int = 5,
) -> LadderMetrics:
    target = normalize_trade_date(target_date)
    calendar = sorted(
        {date for value in trade_dates if (date := normalize_trade_date(value)) and date <= target},
        reverse=True,
    )
    if not target or not calendar or calendar[0] != target:
        return LadderMetrics(0, 0, min(window_days, len(calendar)))

    limits = {date for value in limit_dates if (date := normalize_trade_date(value))}
    consecutive = 0
    for trade_date in calendar:
        if trade_date not in limits:
            break
        consecutive += 1

    recent_dates = calendar[:window_days]
    return LadderMetrics(
        consecutive=consecutive,
        recent_limit_count=sum(trade_date in limits for trade_date in recent_dates),
        recent_window_days=len(recent_dates),
    )
