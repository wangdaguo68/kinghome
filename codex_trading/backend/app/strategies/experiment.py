from __future__ import annotations

from dataclasses import dataclass

from app.data.schemas import CycleState, CycleTag, Pattern, Signal, StockBar
from app.strategies.base import Strategy
from app.strategies.energy_breakout import EnergyBreakoutConfig, EnergyBreakoutStrategy


@dataclass(frozen=True)
class StrategyPreset:
    id: str
    name: str
    description: str
    amount_min_billion: float
    rank_limit: int
    first_limit_mode: str
    one_to_two_open_min_pct: float
    include_extreme: bool
    cycle_filter: bool = True
    position_pct: float | None = None
    max_signals_per_strategy: int = 4
    research_only: bool = False
    include_energy: bool = True


PRESETS: tuple[StrategyPreset, ...] = (
    StrategyPreset(
        id="conservative",
        name="保守版",
        description="严格收盘封首板，成交额和强度排名要求较高。",
        amount_min_billion=5,
        rank_limit=30,
        first_limit_mode="sealed",
        one_to_two_open_min_pct=3,
        include_extreme=True,
    ),
    StrategyPreset(
        id="balanced",
        name="平衡版",
        description="首板可放宽到盘中触板且收盘强势，扩大候选排名。",
        amount_min_billion=3,
        rank_limit=300,
        first_limit_mode="touched_strong_close",
        one_to_two_open_min_pct=1,
        include_extreme=True,
    ),
    StrategyPreset(
        id="aggressive",
        name="进攻版",
        description="接受接近涨停的强势票，周期过滤放宽，用于找更多样本。",
        amount_min_billion=2,
        rank_limit=500,
        first_limit_mode="strong_momentum",
        one_to_two_open_min_pct=0,
        include_extreme=True,
        cycle_filter=False,
    ),
)


class ExperimentalFirstLimitStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP, CycleTag.MAIN_RALLY, CycleTag.LOW_SHAKE}

    def __init__(self, preset: StrategyPreset) -> None:
        self.preset = preset

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        if self.preset.cycle_filter and cycle.tag not in self.enabled_cycles:
            return []
        candidates = [
            bar
            for bar in bars
            if self._matches_first_limit(bar)
            and bar.amount_billion >= self.preset.amount_min_billion
            and bar.sector_rank <= self.preset.rank_limit
        ]
        return [
            Signal(
                trade_date=bar.trade_date,
                symbol=bar.symbol,
                name=bar.name,
                pattern=Pattern.FIRST_LIMIT,
                score=bar.close_pct + bar.amount_billion,
                planned_position_pct=self.preset.position_pct or 6,
                stop_loss_pct=-5,
                reason=f"{self.preset.name}首板实验：{self.preset.description}",
            )
            for bar in sorted(candidates, key=lambda item: (item.close_pct, item.amount_billion), reverse=True)[: self.preset.max_signals_per_strategy]
        ]

    def _matches_first_limit(self, bar: StockBar) -> bool:
        if self.preset.first_limit_mode == "sealed":
            return bar.first_limit
        if self.preset.first_limit_mode == "touched_strong_close":
            return _touch_limit(bar) and _strong_close(bar, main_pct=7, cyb_pct=14)
        return _strong_close(bar, main_pct=7, cyb_pct=14)


class ExperimentalOneToTwoStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP, CycleTag.MAIN_RALLY}

    def __init__(self, preset: StrategyPreset) -> None:
        self.preset = preset

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        if self.preset.cycle_filter and cycle.tag not in self.enabled_cycles:
            return []
        candidates = [
            bar
            for bar in bars
            if self._base_signal(bar)
            and bar.amount_billion >= self.preset.amount_min_billion
            and bar.sector_rank <= self.preset.rank_limit
        ]
        return [
            Signal(
                trade_date=bar.trade_date,
                symbol=bar.symbol,
                name=bar.name,
                pattern=Pattern.ONE_TO_TWO,
                score=bar.close_pct + bar.amount_billion,
                planned_position_pct=self.preset.position_pct or 5,
                stop_loss_pct=-5,
                reason=f"{self.preset.name}一进二实验：信号日强势，次日开盘门槛 {self.preset.one_to_two_open_min_pct}%",
                min_entry_open_pct=self.preset.one_to_two_open_min_pct,
            )
            for bar in sorted(candidates, key=lambda item: (item.close_pct, item.amount_billion), reverse=True)[: self.preset.max_signals_per_strategy]
        ]

    def _base_signal(self, bar: StockBar) -> bool:
        if self.preset.first_limit_mode == "sealed":
            return bar.first_limit
        if self.preset.first_limit_mode == "touched_strong_close":
            return _touch_limit(bar) and _strong_close(bar, main_pct=7, cyb_pct=14)
        return _strong_close(bar, main_pct=7, cyb_pct=14)


class ExperimentalExtremeStrategy(Strategy):
    enabled_cycles = {CycleTag.ICE_POINT, CycleTag.TURN_UP, CycleTag.CLIMAX}

    def __init__(self, preset: StrategyPreset) -> None:
        self.preset = preset

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        if not self.preset.include_extreme:
            return []
        if self.preset.cycle_filter and cycle.tag not in self.enabled_cycles:
            return []
        close_min = 4 if self.preset.id == "conservative" else 3 if self.preset.id == "balanced" else 2
        candidates = [
            bar
            for bar in bars
            if not bar.limit_up
            and bar.close_pct >= close_min
            and bar.amount_billion >= self.preset.amount_min_billion
            and bar.sector_rank <= self.preset.rank_limit
        ]
        return [
            Signal(
                trade_date=bar.trade_date,
                symbol=bar.symbol,
                name=bar.name,
                pattern=Pattern.EXTREME_ARBITRAGE,
                score=bar.amount_billion + bar.close_pct,
                planned_position_pct=self.preset.position_pct or (8 if cycle.tag != CycleTag.CLIMAX else 3),
                stop_loss_pct=-5,
                reason=f"{self.preset.name}极值/强势修复实验",
            )
            for bar in sorted(candidates, key=lambda item: (item.close_pct, item.amount_billion), reverse=True)[: self.preset.max_signals_per_strategy]
        ]


def strategies_for_preset(preset: StrategyPreset) -> list[Strategy]:
    return [
        ExperimentalExtremeStrategy(preset),
        ExperimentalFirstLimitStrategy(preset),
        ExperimentalOneToTwoStrategy(preset),
        ExperimentalEnergyBreakoutStrategy(preset),
    ]


class ExperimentalEnergyBreakoutStrategy(EnergyBreakoutStrategy):
    def __init__(self, preset: StrategyPreset) -> None:
        volume_ratio = 2.0 if preset.id == "conservative" else 1.8 if preset.id == "balanced" else 1.5
        min_amount = max(preset.amount_min_billion, 5 if preset.id == "conservative" else 3)
        config = EnergyBreakoutConfig(
            min_failed_attempts=2,
            volume_ratio_min=volume_ratio,
            min_amount_billion=min_amount,
            max_signals=max(1, min(3, preset.max_signals_per_strategy)),
            position_pct=preset.position_pct or 5,
        )
        super().__init__(config, cycle_filter=preset.cycle_filter)
        self.preset = preset

    def generate_with_history(
        self,
        cycle: CycleState,
        bars: list[StockBar],
        history_by_symbol: dict[str, list[StockBar]],
    ) -> list[Signal]:
        if not self.preset.include_energy:
            return []
        signals = super().generate_with_history(cycle, bars, history_by_symbol)
        return [
            Signal(
                trade_date=signal.trade_date,
                symbol=signal.symbol,
                name=signal.name,
                pattern=signal.pattern,
                score=signal.score,
                planned_position_pct=signal.planned_position_pct,
                stop_loss_pct=signal.stop_loss_pct,
                reason=f"{self.preset.name}{signal.reason}",
                min_entry_open_pct=signal.min_entry_open_pct,
            )
            for signal in signals
        ]


def _touch_limit(bar: StockBar) -> bool:
    ratio = 1.20 if bar.symbol.startswith(("300", "301")) else 1.10
    return bar.high_price >= round(bar.pre_close * ratio + 1e-8, 2)


def _strong_close(bar: StockBar, main_pct: float, cyb_pct: float) -> bool:
    threshold = cyb_pct if bar.symbol.startswith(("300", "301")) else main_pct
    return bar.close_pct >= threshold
