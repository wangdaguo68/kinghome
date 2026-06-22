from __future__ import annotations

from dataclasses import dataclass


def normalize_trade_date(value: str) -> str:
    compact = str(value).strip().replace("-", "").replace(".", "").replace("/", "")
    return compact if len(compact) == 8 and compact.isdigit() else ""


@dataclass(frozen=True)
class LadderMetrics:
    consecutive: int
    recent_limit_count: int
    recent_window_days: int


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
