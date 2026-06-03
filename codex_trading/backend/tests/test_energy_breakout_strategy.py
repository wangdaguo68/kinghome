from datetime import date, timedelta

from app.data.schemas import CycleState, CycleTag, StockBar
from app.strategies.energy_breakout import EnergyBreakoutConfig, EnergyBreakoutStrategy


def test_energy_breakout_requires_two_failed_ma60_probes() -> None:
    bars = _energy_history(failed_probe_indexes={60, 63})
    cycle = _cycle(bars[-1].trade_date)
    strategy = EnergyBreakoutStrategy(EnergyBreakoutConfig(min_amount_billion=1, volume_ratio_min=1.5))

    signals = strategy.generate_with_history(cycle, [bars[-1]], {bars[-1].symbol: bars})

    assert len(signals) == 1
    assert signals[0].pattern == "EnergyBreakout"
    assert "近20日 2 次" in signals[0].reason


def test_energy_breakout_rejects_single_failed_probe() -> None:
    bars = _energy_history(failed_probe_indexes={63})
    cycle = _cycle(bars[-1].trade_date)
    strategy = EnergyBreakoutStrategy(EnergyBreakoutConfig(min_amount_billion=1, volume_ratio_min=1.5))

    assert strategy.generate_with_history(cycle, [bars[-1]], {bars[-1].symbol: bars}) == []


def _cycle(trade_date: date) -> CycleState:
    return CycleState(
        trade_date=trade_date,
        red_count=2500,
        limit_up_count=60,
        limit_down_count=10,
        ma3=2500,
        ma5=2400,
        ma3_trend="up",
        ma5_trend="up",
        tag=CycleTag.TURN_UP,
        turnover_billion=10000,
    )


def _energy_history(failed_probe_indexes: set[int]) -> list[StockBar]:
    start = date(2026, 1, 1)
    bars: list[StockBar] = []
    for index in range(66):
        close = 100.0
        open_price = 99.8
        high = 101.0
        low = 98.8
        amount = 2.0
        close_pct = 0.2
        if index in failed_probe_indexes:
            open_price = 98.5
            close = 99.0
            high = 104.5
            low = 98.0
            close_pct = -0.5
        if index == 65:
            open_price = 101.0
            close = 103.0
            high = 103.5
            low = 100.5
            amount = 5.0
            close_pct = 3.0
        bars.append(
            StockBar(
                trade_date=start + timedelta(days=index),
                symbol="000001.SZ",
                name="能量样本",
                open_price=open_price,
                high_price=high,
                low_price=low,
                close_price=close,
                pre_close=100,
                open_pct=0,
                close_pct=close_pct,
                high_pct=high / 100 * 100 - 100,
                low_pct=low / 100 * 100 - 100,
                amount_billion=amount,
                auction_amount_million=0,
                volume_ratio=0,
                limit_up=False,
                first_limit=False,
                consecutive_limits=0,
                sector_rank=20,
            )
        )
    return bars
