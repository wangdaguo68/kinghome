from datetime import date, timedelta

from app.data.schemas import CycleState, CycleTag, StockBar
from app.strategies.short_energy import ShortEnergyConfig, ShortEnergyStrategy


def test_short_energy_generates_front_row_signal() -> None:
    bars = _history()
    strategy = ShortEnergyStrategy(ShortEnergyConfig(min_avg_amount_billion=1, market_threshold=55))

    signals = strategy.generate_with_history(_cycle(CycleTag.MAIN_RALLY), [bars[-1]], {bars[-1].symbol: bars})

    assert len(signals) == 1
    assert signals[0].pattern == "ShortEnergy"
    assert "市场能量" in signals[0].reason
    assert "主线前排接力" in signals[0].reason


def test_short_energy_rejects_weak_market() -> None:
    bars = _history()
    strategy = ShortEnergyStrategy(ShortEnergyConfig(min_avg_amount_billion=1, market_threshold=60))

    assert strategy.generate_with_history(_weak_cycle(), [bars[-1]], {bars[-1].symbol: bars}) == []


def _cycle(tag: CycleTag) -> CycleState:
    return CycleState(
        trade_date=date(2026, 6, 3),
        red_count=3200,
        limit_up_count=95,
        limit_down_count=5,
        ma3=2800,
        ma5=2500,
        ma3_trend="up",
        ma5_trend="up",
        tag=tag,
        down_count=1500,
        turnover_billion=11000,
    )


def _weak_cycle() -> CycleState:
    return CycleState(
        trade_date=date(2026, 6, 3),
        red_count=900,
        limit_up_count=18,
        limit_down_count=80,
        ma3=1200,
        ma5=1800,
        ma3_trend="down",
        ma5_trend="down",
        tag=CycleTag.DOWNTREND,
        down_count=3700,
        turnover_billion=6500,
    )


def _history() -> list[StockBar]:
    start = date(2026, 5, 1)
    rows: list[StockBar] = []
    for index in range(25):
        close_pct = 0.8
        amount = 2.2
        close = 100 + index * 0.2
        high = close + 1
        low = close - 2
        first_limit = False
        limit_up = False
        if index == 24:
            close_pct = 8.6
            amount = 7.4
            close = 108.6
            high = 109.2
            low = 101.0
            first_limit = True
            limit_up = True
        rows.append(
            StockBar(
                trade_date=start + timedelta(days=index),
                symbol="000001.SZ",
                name="超短样本",
                open_price=100,
                high_price=high,
                low_price=low,
                close_price=close,
                pre_close=100,
                open_pct=0,
                close_pct=close_pct,
                high_pct=high - 100,
                low_pct=low - 100,
                amount_billion=amount,
                auction_amount_million=0,
                volume_ratio=0,
                limit_up=limit_up,
                first_limit=first_limit,
                consecutive_limits=1 if limit_up else 0,
                sector_rank=12,
            )
        )
    return rows
