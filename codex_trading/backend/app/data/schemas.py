from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class CycleTag(StrEnum):
    ICE_POINT = "IcePoint"
    TURN_UP = "TurnUp"
    MAIN_RALLY = "MainRally"
    CLIMAX = "Climax"
    TURN_DOWN = "TurnDown"
    DOWNTREND = "Downtrend"
    LOW_SHAKE = "LowShake"
    HIGH_SHAKE = "HighShake"


class Pattern(StrEnum):
    EXTREME_ARBITRAGE = "ExtremeArbitrage"
    FIRST_LIMIT = "FirstLimit"
    ONE_TO_TWO = "OneToTwo"


@dataclass(frozen=True)
class MarketDay:
    trade_date: date
    red_count: int
    limit_up_count: int
    limit_down_count: int
    index_return: float
    turnover_billion: float
    down_count: int = 0
    sh_turnover_billion: float = 0
    sz_turnover_billion: float = 0


@dataclass(frozen=True)
class StockBar:
    trade_date: date
    symbol: str
    name: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    pre_close: float
    open_pct: float
    close_pct: float
    high_pct: float
    low_pct: float
    amount_billion: float
    auction_amount_million: float
    volume_ratio: float
    limit_up: bool
    first_limit: bool
    consecutive_limits: int
    sector_rank: int


@dataclass(frozen=True)
class CycleState:
    trade_date: date
    red_count: int
    limit_up_count: int
    limit_down_count: int
    ma3: float
    ma5: float
    ma3_trend: str
    ma5_trend: str
    tag: CycleTag
    down_count: int = 0
    turnover_billion: float = 0
    sh_turnover_billion: float = 0
    sz_turnover_billion: float = 0


@dataclass(frozen=True)
class Signal:
    trade_date: date
    symbol: str
    name: str
    pattern: Pattern
    score: float
    planned_position_pct: float
    stop_loss_pct: float
    reason: str
    min_entry_open_pct: float | None = None


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Trade:
    signal_date: date
    entry_date: date
    exit_date: date
    symbol: str
    name: str
    pattern: Pattern
    cycle_tag: CycleTag
    entry_price: float
    exit_price: float
    position_pct: float
    pnl_pct: float
    exit_reason: str
    signal_reason: str
    after_3d_return_pct: float | None = None
    gross_pnl_pct: float | None = None
    fee_pct: float = 0
    fee_amount: float = 0
