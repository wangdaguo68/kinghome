from __future__ import annotations

from dataclasses import dataclass

from app.data.schemas import CycleState, CycleTag, Pattern, Signal, StockBar
from app.strategies.base import Strategy


@dataclass(frozen=True)
class EnergyBreakoutConfig:
    min_failed_attempts: int = 2
    lookback_days: int = 20
    ma_days: int = 60
    probe_tolerance_pct: float = 0.5
    breakout_buffer_pct: float = 0.5
    max_breakout_pct: float = 35
    upper_shadow_pct: float = 3
    upper_shadow_share: float = 0.45
    volume_ratio_min: float = 1.8
    min_amount_billion: float = 3
    min_close_pct: float = 2
    max_close_pct_main: float = 9.5
    max_close_pct_growth: float = 18
    max_signals: int = 3
    position_pct: float = 5
    stop_loss_pct: float = -5


class EnergyBreakoutStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP, CycleTag.MAIN_RALLY, CycleTag.LOW_SHAKE}

    def __init__(self, config: EnergyBreakoutConfig | None = None, *, cycle_filter: bool = True) -> None:
        self.config = config or EnergyBreakoutConfig()
        self.cycle_filter = cycle_filter

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        return []

    def generate_with_history(
        self,
        cycle: CycleState,
        bars: list[StockBar],
        history_by_symbol: dict[str, list[StockBar]],
    ) -> list[Signal]:
        if self.cycle_filter and cycle.tag not in self.enabled_cycles:
            return []

        candidates: list[tuple[StockBar, EnergyScore]] = []
        for bar in bars:
            score = self._score_candidate(bar, history_by_symbol.get(bar.symbol, []))
            if score is not None:
                candidates.append((bar, score))

        ordered = sorted(candidates, key=lambda item: item[1].sort_key, reverse=True)
        return [
            Signal(
                trade_date=bar.trade_date,
                symbol=bar.symbol,
                name=bar.name,
                pattern=Pattern.ENERGY_BREAKOUT,
                score=score.score,
                planned_position_pct=self.config.position_pct,
                stop_loss_pct=self.config.stop_loss_pct,
                reason=(
                    f"能量策略：近20日 {score.failed_attempts} 次长上影试探60日线未成功，"
                    f"当日放量 {score.volume_ratio:.2f} 倍并收盘站上60日线 {score.breakout_pct:.2f}%。"
                ),
            )
            for bar, score in ordered[: self.config.max_signals]
        ]

    def _score_candidate(self, bar: StockBar, history: list[StockBar]) -> EnergyScore | None:
        config = self.config
        history = [item for item in history if item.trade_date <= bar.trade_date]
        history = sorted(history, key=lambda item: item.trade_date)
        if len(history) < config.ma_days + 1 or history[-1].trade_date != bar.trade_date:
            return None

        signal_index = len(history) - 1
        ma60 = _ma_close(history, signal_index, config.ma_days)
        if ma60 is None or ma60 <= 0:
            return None

        max_close_pct = config.max_close_pct_growth if bar.symbol.startswith(("300", "301")) else config.max_close_pct_main
        if bar.close_pct < config.min_close_pct or bar.close_pct > max_close_pct:
            return None
        if bar.close_price <= ma60 * (1 + config.breakout_buffer_pct / 100):
            return None
        breakout_pct = (bar.close_price / ma60 - 1) * 100
        if breakout_pct > config.max_breakout_pct:
            return None

        prior = history[max(0, signal_index - config.lookback_days) : signal_index]
        if len(prior) < config.lookback_days:
            return None
        avg_amount = sum(item.amount_billion for item in prior) / len(prior)
        if avg_amount <= 0 or bar.amount_billion < config.min_amount_billion:
            return None
        volume_ratio = bar.amount_billion / avg_amount
        if volume_ratio < config.volume_ratio_min:
            return None

        ma60_10_index = signal_index - 10
        ma60_10 = _ma_close(history, ma60_10_index, config.ma_days) if ma60_10_index >= 0 else None
        if ma60_10 is not None and ma60 < ma60_10 * 0.98:
            return None

        failed_attempts = 0
        prior_start = max(0, signal_index - config.lookback_days)
        for attempt_index, attempt in enumerate(prior, start=prior_start):
            attempt_ma60 = _ma_close(history, attempt_index, config.ma_days)
            if attempt_ma60 is None:
                continue
            if _failed_probe(attempt, attempt_ma60, config):
                failed_attempts += 1

        if failed_attempts < config.min_failed_attempts:
            return None

        score = failed_attempts * 10 + volume_ratio * 5 + breakout_pct + bar.amount_billion
        return EnergyScore(
            failed_attempts=failed_attempts,
            volume_ratio=volume_ratio,
            breakout_pct=breakout_pct,
            score=round(score, 2),
        )


@dataclass(frozen=True)
class EnergyScore:
    failed_attempts: int
    volume_ratio: float
    breakout_pct: float
    score: float

    @property
    def sort_key(self) -> tuple[float, float, float, int]:
        return (self.score, self.volume_ratio, self.breakout_pct, self.failed_attempts)


def _ma_close(history: list[StockBar], index: int, window: int) -> float | None:
    if index < window - 1:
        return None
    rows = history[index - window + 1 : index + 1]
    return sum(item.close_price for item in rows) / window


def _failed_probe(bar: StockBar, ma60: float, config: EnergyBreakoutConfig) -> bool:
    if bar.high_price < ma60 * (1 - config.probe_tolerance_pct / 100):
        return False
    if bar.close_price >= ma60:
        return False
    upper_shadow = bar.high_price - max(bar.open_price, bar.close_price)
    day_range = bar.high_price - bar.low_price
    if bar.pre_close <= 0 or day_range <= 0:
        return False
    return (
        upper_shadow / bar.pre_close * 100 >= config.upper_shadow_pct
        or upper_shadow / day_range >= config.upper_shadow_share
    )
