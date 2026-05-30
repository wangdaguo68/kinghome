from __future__ import annotations

from app.data.schemas import CycleState, CycleTag, Pattern, Signal, StockBar
from app.strategies.base import Strategy


class ExtremeArbitrageStrategy(Strategy):
    enabled_cycles = {CycleTag.ICE_POINT, CycleTag.TURN_UP, CycleTag.CLIMAX}

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        if cycle.tag not in self.enabled_cycles:
            return []
        candidates = [
            bar
            for bar in bars
            if not bar.limit_up and bar.amount_billion >= 5 and bar.sector_rank <= 30 and bar.close_pct >= 4
        ]
        return [
            Signal(
                trade_date=bar.trade_date,
                symbol=bar.symbol,
                name=bar.name,
                pattern=Pattern.EXTREME_ARBITRAGE,
                score=bar.amount_billion + bar.close_pct,
                planned_position_pct=8 if cycle.tag != CycleTag.CLIMAX else 3,
                stop_loss_pct=-5,
                reason="非涨停强势修复或极值日标的，成交额和强度排名达标；仅使用 Tushare 日线字段",
            )
            for bar in sorted(candidates, key=lambda item: (item.close_pct, item.amount_billion), reverse=True)[:2]
        ]
