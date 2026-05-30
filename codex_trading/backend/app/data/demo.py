from __future__ import annotations

from datetime import date, timedelta

from app.data.schemas import MarketDay, StockBar


def demo_market_days() -> list[MarketDay]:
    red_counts = [2450, 1980, 1320, 860, 1180, 1540, 2130, 2860, 4050, 3520, 2480, 1760]
    start = date(2026, 5, 11)
    return [
        MarketDay(
            trade_date=start + timedelta(days=i),
            red_count=value,
            limit_up_count=max(0, value // 120),
            limit_down_count=max(0, (4200 - value) // 180),
            index_return=round((value - red_counts[i - 1]) / 10000, 4) if i else 0,
            turnover_billion=820 + i * 28,
        )
        for i, value in enumerate(red_counts)
    ]


def demo_stock_bars() -> list[StockBar]:
    names = [
        ("000001", "华夏科技"),
        ("000002", "北辰电新"),
        ("000003", "星河传媒"),
        ("000004", "远东智能"),
    ]
    rows: list[StockBar] = []
    for i, day in enumerate(demo_market_days()):
        for j, (symbol, name) in enumerate(names):
            base = (i * 1.7 + j * 2.1) % 8
            limit_up = (i in {4, 5, 6} and j in {0, 1}) or (i == 8 and j == 2)
            consecutive = 2 if i == 5 and j == 0 else 1 if limit_up else 0
            rows.append(
                StockBar(
                    trade_date=day.trade_date,
                    symbol=symbol,
                    name=name,
                    open_price=100 + round(base - 2 + j, 2),
                    high_price=100 + (10.0 if limit_up else round(base + 1.4, 2)),
                    low_price=100 + round(base - 5.8, 2),
                    close_price=100 + (9.9 if limit_up else round(base - 3.2, 2)),
                    pre_close=100,
                    open_pct=round(base - 2 + j, 2),
                    close_pct=9.9 if limit_up else round(base - 3.2, 2),
                    high_pct=10.0 if limit_up else round(base + 1.4, 2),
                    low_pct=round(base - 5.8, 2),
                    amount_billion=8.5 + i * 0.7 + j * 1.8,
                    auction_amount_million=1600 + i * 180 + j * 520,
                    volume_ratio=1.1 + (i % 4) * 0.25 + j * 0.12,
                    limit_up=limit_up,
                    first_limit=limit_up and consecutive == 1,
                    consecutive_limits=consecutive,
                    sector_rank=j + 1,
                )
            )
    return rows
