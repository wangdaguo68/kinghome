from __future__ import annotations

from dataclasses import dataclass

from app.data.schemas import CycleState, CycleTag, Pattern, Signal, StockBar
from app.strategies.base import Strategy


@dataclass(frozen=True)
class ShortEnergyConfig:
    market_threshold: float = 58
    stock_threshold: float = 68
    leader_threshold: float = 56
    min_amount_billion: float = 3
    min_avg_amount_billion: float = 2
    min_close_pct: float = 5
    max_main_close_pct: float = 9.8
    max_growth_close_pct: float = 18.5
    max_sector_rank: int = 120
    max_signals: int = 4
    allow_watch_candidates: bool = False
    position_pct: float = 10
    leader_position_pct: float = 15
    ignition_position_pct: float = 6
    stop_loss_pct: float = -6


@dataclass(frozen=True)
class ShortEnergyScore:
    market_energy: float
    stock_energy: float
    leader_score: float
    volume_ratio: float
    stage: str
    mode: str
    score: float

    @property
    def sort_key(self) -> tuple[float, float, float, float]:
        return (self.score, self.leader_score, self.stock_energy, self.volume_ratio)


class ShortEnergyStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP, CycleTag.MAIN_RALLY, CycleTag.LOW_SHAKE, CycleTag.CLIMAX}

    def __init__(self, config: ShortEnergyConfig | None = None, *, cycle_filter: bool = True) -> None:
        self.config = config or ShortEnergyConfig()
        self.cycle_filter = cycle_filter

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        return self.generate_with_history(cycle, bars, {bar.symbol: [bar] for bar in bars})

    def generate_with_history(
        self,
        cycle: CycleState,
        bars: list[StockBar],
        history_by_symbol: dict[str, list[StockBar]],
    ) -> list[Signal]:
        if self.cycle_filter and cycle.tag not in self.enabled_cycles:
            return []

        market_energy = _market_energy_score(cycle)
        if market_energy < self.config.market_threshold and not self.config.allow_watch_candidates:
            return []
        if market_energy < 30:
            return []

        candidates: list[tuple[StockBar, ShortEnergyScore]] = []
        for bar in bars:
            score = self._score_candidate(cycle, bar, history_by_symbol.get(bar.symbol, []), market_energy)
            if score is not None:
                candidates.append((bar, score))

        ordered = sorted(candidates, key=lambda item: item[1].sort_key, reverse=True)
        return [self._signal(bar, score) for bar, score in ordered[: self.config.max_signals]]

    def _score_candidate(
        self,
        cycle: CycleState,
        bar: StockBar,
        history: list[StockBar],
        market_energy: float,
    ) -> ShortEnergyScore | None:
        config = self.config
        if bar.amount_billion < config.min_amount_billion or bar.close_pct < config.min_close_pct:
            return None
        if bar.sector_rank <= 0 or bar.sector_rank > config.max_sector_rank:
            return None

        max_close_pct = config.max_growth_close_pct if bar.symbol.startswith(("300", "301")) else config.max_main_close_pct
        if bar.close_pct > max_close_pct:
            return None

        history = sorted([item for item in history if item.trade_date <= bar.trade_date], key=lambda item: item.trade_date)
        prior = history[-21:-1] if len(history) > 1 else []
        avg_amount = sum(item.amount_billion for item in prior) / len(prior) if prior else bar.amount_billion
        if avg_amount < config.min_avg_amount_billion:
            return None
        volume_ratio = bar.amount_billion / avg_amount if avg_amount > 0 else 1
        if volume_ratio < 1.15 and not bar.limit_up:
            return None

        stock_energy = _stock_energy_score(bar, history, volume_ratio)
        leader_score = _leader_score(bar, volume_ratio)
        if stock_energy < config.stock_threshold or leader_score < config.leader_threshold:
            return None

        stage = _market_stage(cycle, market_energy)
        mode = _buy_mode(cycle, bar, history, stock_energy, leader_score, market_energy, config.allow_watch_candidates)
        if mode is None:
            return None

        score = round(market_energy * 0.25 + stock_energy * 0.45 + leader_score * 0.30, 2)
        return ShortEnergyScore(
            market_energy=round(market_energy, 2),
            stock_energy=round(stock_energy, 2),
            leader_score=round(leader_score, 2),
            volume_ratio=round(volume_ratio, 2),
            stage=stage,
            mode=mode,
            score=score,
        )

    def _signal(self, bar: StockBar, score: ShortEnergyScore) -> Signal:
        position = self.config.position_pct
        if score.mode == "主线前排接力" and score.leader_score >= 75:
            position = self.config.leader_position_pct
        elif score.mode == "新题材点火试错":
            position = self.config.ignition_position_pct

        return Signal(
            trade_date=bar.trade_date,
            symbol=bar.symbol,
            name=bar.name,
            pattern=Pattern.SHORT_ENERGY,
            score=score.score,
            planned_position_pct=position,
            stop_loss_pct=self.config.stop_loss_pct,
            reason=(
                f"超短能量交易：{score.mode}，市场能量 {score.market_energy:.0f}（{score.stage}），"
                f"个股能量 {score.stock_energy:.0f}，前排/龙头分 {score.leader_score:.0f}，"
                f"成交量约为20日均量 {score.volume_ratio:.2f} 倍，板块强度排名 {bar.sector_rank}。"
            ),
        )


def _market_energy_score(cycle: CycleState) -> float:
    limit_up_score = _clamp(cycle.limit_up_count / 100 * 100)
    limit_down_score = _clamp(100 - cycle.limit_down_count / 80 * 100)
    breadth_total = cycle.red_count + cycle.down_count
    breadth_score = _clamp(cycle.red_count / breadth_total * 100) if breadth_total > 0 else _clamp(cycle.red_count / 4500 * 100)
    turnover_score = _clamp((cycle.turnover_billion - 6000) / 6000 * 100) if cycle.turnover_billion else 55
    trend_score = 65
    if cycle.ma3 >= cycle.ma5 and cycle.ma3_trend == "up":
        trend_score = 85
    elif cycle.ma3_trend == "down" and cycle.ma5_trend == "down":
        trend_score = 35

    tag_bonus = {
        CycleTag.MAIN_RALLY: 10,
        CycleTag.TURN_UP: 8,
        CycleTag.LOW_SHAKE: 2,
        CycleTag.CLIMAX: -6,
        CycleTag.HIGH_SHAKE: -10,
        CycleTag.TURN_DOWN: -18,
        CycleTag.DOWNTREND: -25,
        CycleTag.ICE_POINT: -8,
    }[cycle.tag]
    score = (
        limit_up_score * 0.24
        + limit_down_score * 0.14
        + breadth_score * 0.20
        + turnover_score * 0.18
        + trend_score * 0.24
        + tag_bonus
    )
    return _clamp(score)


def _stock_energy_score(bar: StockBar, history: list[StockBar], volume_ratio: float) -> float:
    price_score = _clamp((bar.close_pct - 4) / 6 * 100)
    volume_score = _clamp((volume_ratio - 1) / 2.5 * 100)
    rank_score = _rank_score(bar.sector_rank)
    limit_quality = 95 if bar.first_limit else 88 if bar.limit_up else 72 if bar.high_pct >= 9 else 58
    resilience = _resilience_score(bar)
    chip_score = _chip_score(bar, history)
    return _clamp(
        price_score * 0.22
        + volume_score * 0.17
        + limit_quality * 0.18
        + rank_score * 0.18
        + resilience * 0.15
        + chip_score * 0.10
    )


def _leader_score(bar: StockBar, volume_ratio: float) -> float:
    board_score = _clamp(bar.consecutive_limits / 3 * 100) if bar.consecutive_limits else (70 if bar.first_limit else 45)
    rank_score = _rank_score(bar.sector_rank)
    quality_score = 95 if bar.limit_up else 72 if bar.close_pct >= 7 else 58
    amount_score = _clamp((bar.amount_billion - 3) / 12 * 100)
    volume_score = _clamp((volume_ratio - 1) / 2 * 100)
    return _clamp(board_score * 0.25 + rank_score * 0.28 + quality_score * 0.22 + amount_score * 0.15 + volume_score * 0.10)


def _market_stage(cycle: CycleState, market_energy: float) -> str:
    if market_energy >= 80:
        return "强能量期"
    if market_energy >= 60:
        return "可交易期"
    if cycle.tag == CycleTag.CLIMAX:
        return "高潮谨慎期"
    return "混沌试错期"


def _buy_mode(
    cycle: CycleState,
    bar: StockBar,
    history: list[StockBar],
    stock_energy: float,
    leader_score: float,
    market_energy: float,
    allow_watch_candidates: bool = False,
) -> str | None:
    low_position = _low_position(bar, history)
    if allow_watch_candidates and market_energy < 50:
        if bar.sector_rank <= 90 and stock_energy >= 58 and leader_score >= 45 and (bar.limit_up or bar.close_pct >= 6):
            return "退潮观察候选"
        return None
    if market_energy >= 60 and bar.sector_rank <= 50 and stock_energy >= 72 and leader_score >= 60:
        return "主线前排接力"
    if bar.first_limit and bar.sector_rank <= 90 and low_position and cycle.tag in {CycleTag.TURN_UP, CycleTag.LOW_SHAKE, CycleTag.MAIN_RALLY}:
        return "主线低位补涨"
    if bar.first_limit and market_energy >= 50 and bar.sector_rank <= 80:
        return "新题材点火试错"
    return None


def _rank_score(rank: int) -> float:
    if rank <= 10:
        return 100
    if rank <= 30:
        return 88
    if rank <= 60:
        return 72
    if rank <= 100:
        return 58
    return 42


def _resilience_score(bar: StockBar) -> float:
    day_range = bar.high_price - bar.low_price
    if day_range <= 0:
        return 60
    close_location = (bar.close_price - bar.low_price) / day_range
    return _clamp(close_location * 100)


def _chip_score(bar: StockBar, history: list[StockBar]) -> float:
    recent = history[-60:] if history else []
    if not recent:
        return 60
    recent_high = max(item.high_price for item in recent)
    if recent_high <= 0:
        return 60
    location = bar.close_price / recent_high
    if location <= 0.82:
        return 92
    if location <= 0.95:
        return 78
    if location <= 1.05:
        return 62
    return 45


def _low_position(bar: StockBar, history: list[StockBar]) -> bool:
    recent = history[-40:] if history else []
    if not recent:
        return False
    recent_high = max(item.high_price for item in recent)
    return recent_high > 0 and bar.close_price <= recent_high * 0.95


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))
