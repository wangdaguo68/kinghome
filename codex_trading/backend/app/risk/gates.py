from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.data.schemas import CycleState, CycleTag, Pattern, RiskDecision, Signal, StockBar


PATTERN_CYCLES: dict[Pattern, set[CycleTag]] = {
    Pattern.EXTREME_ARBITRAGE: {CycleTag.ICE_POINT, CycleTag.TURN_UP, CycleTag.CLIMAX},
    Pattern.FIRST_LIMIT: {CycleTag.TURN_UP, CycleTag.MAIN_RALLY, CycleTag.LOW_SHAKE},
    Pattern.ONE_TO_TWO: {CycleTag.TURN_UP, CycleTag.MAIN_RALLY},
    Pattern.ENERGY_BREAKOUT: {CycleTag.TURN_UP, CycleTag.MAIN_RALLY, CycleTag.LOW_SHAKE},
}

POSITION_LIMITS: dict[CycleTag, float] = {
    CycleTag.ICE_POINT: 100,
    CycleTag.TURN_UP: 60,
    CycleTag.MAIN_RALLY: 70,
    CycleTag.CLIMAX: 30,
    CycleTag.TURN_DOWN: 10,
    CycleTag.DOWNTREND: 10,
    CycleTag.LOW_SHAKE: 20,
    CycleTag.HIGH_SHAKE: 20,
}

SINGLE_POSITION_LIMIT_PCT = 20.0


@dataclass
class AccountState:
    current_position_pct: float = 0
    consecutive_losses: int = 0
    cut_loss_today: bool = False
    afternoon_index_fading: bool = False


def evaluate_signal(
    signal: Signal,
    cycle: CycleState,
    bar: StockBar,
    account: AccountState,
    *,
    min_amount_billion: float = 5,
    enforce_pattern_cycle: bool = True,
    consecutive_loss_limit: int | None = 2,
    single_position_limit_pct: float = SINGLE_POSITION_LIMIT_PCT,
    total_position_limit_pct: float | None = None,
) -> RiskDecision:
    reasons: list[str] = []
    if signal.trade_date != cycle.trade_date or bar.trade_date != cycle.trade_date:
        reasons.append("信号、周期、行情日期不一致")
    if signal.symbol != bar.symbol:
        reasons.append("信号标的与行情标的不一致")
    if not 0 < signal.planned_position_pct <= single_position_limit_pct:
        reasons.append("计划仓位必须大于 0 且不超过单票上限")
    if not -20 <= signal.stop_loss_pct < 0:
        reasons.append("硬止损必须为 -20% 到 0% 之间的负数")
    if not isfinite(signal.score):
        reasons.append("信号分数无效")
    if enforce_pattern_cycle and cycle.tag not in PATTERN_CYCLES[signal.pattern]:
        reasons.append(f"{signal.pattern} 未在 {cycle.tag} 周期启用")
    if bar.amount_billion < min_amount_billion:
        reasons.append(f"容量不达标：成交额低于 {min_amount_billion:g} 亿")
    if signal.stop_loss_pct >= 0:
        reasons.append("未设置有效硬止损")
    total_limit = POSITION_LIMITS[cycle.tag] if total_position_limit_pct is None else total_position_limit_pct
    if account.current_position_pct + signal.planned_position_pct > total_limit:
        reasons.append("超过当前周期总仓位上限")
    if consecutive_loss_limit is not None and account.consecutive_losses >= consecutive_loss_limit:
        reasons.append(f"连续亏损 {consecutive_loss_limit} 笔后禁止买入")
    if account.cut_loss_today:
        reasons.append("割肉当天禁止买新票")
    if account.afternoon_index_fading:
        reasons.append("下午指数回落时禁止买入")
    return RiskDecision(allowed=not reasons, reasons=tuple(reasons))
