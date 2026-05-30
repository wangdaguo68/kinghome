from __future__ import annotations

from app.data.schemas import CycleState, CycleTag, Pattern, Signal, StockBar
from app.strategies.base import Strategy


class OneToTwoStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP, CycleTag.MAIN_RALLY}

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        if cycle.tag not in self.enabled_cycles:
            return []
        candidates = [
            bar
            for bar in bars
            if bar.first_limit and bar.amount_billion >= 5 and bar.sector_rank <= 30
        ]
        return [
            Signal(
                trade_date=bar.trade_date,
                symbol=bar.symbol,
                name=bar.name,
                pattern=Pattern.ONE_TO_TWO,
                score=bar.close_pct + bar.amount_billion,
                planned_position_pct=5,
                stop_loss_pct=-5,
                reason="信号日收盘封住首板，次日按开盘价模拟一进二；股票池排除科创板、北交所、ST",
                min_entry_open_pct=3,
            )
            for bar in sorted(candidates, key=lambda item: (item.close_pct, item.amount_billion), reverse=True)[:1]
        ]
