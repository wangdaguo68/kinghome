from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.backtest.metrics import summarize_trades
from app.backtest.fees import BrokerFeeModel, NO_FEE_MODEL
from app.cycle.engine import build_cycle_states
from app.data.schemas import MarketDay, Pattern, Signal, StockBar, Trade
from app.risk.gates import AccountState, evaluate_signal
from app.strategies.base import Strategy


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    rejected_signals: list[tuple[Signal, tuple[str, ...]]]
    metrics: dict[str, float]


@dataclass(frozen=True)
class OpenPosition:
    symbol: str
    exit_date: date
    position_pct: float
    pnl_pct: float
    cut_loss: bool


class BacktestEngine:
    """Event-ordered MVP backtester using real OHLC price paths when available."""

    def __init__(
        self,
        strategies: list[Strategy],
        *,
        risk_min_amount_billion: float = 5,
        enforce_pattern_cycle: bool = True,
        consecutive_loss_limit: int | None = 2,
        fee_model: BrokerFeeModel = NO_FEE_MODEL,
        capital: float = 100000,
        single_position_limit_pct: float = 20,
        total_position_limit_pct: float | None = None,
    ) -> None:
        self.strategies = strategies
        self.risk_min_amount_billion = risk_min_amount_billion
        self.enforce_pattern_cycle = enforce_pattern_cycle
        self.consecutive_loss_limit = consecutive_loss_limit
        self.fee_model = fee_model
        self.capital = capital
        self.single_position_limit_pct = single_position_limit_pct
        self.total_position_limit_pct = total_position_limit_pct

    def run(self, market_days: list[MarketDay], stock_bars: list[StockBar]) -> BacktestResult:
        cycles = build_cycle_states(market_days)
        bars_by_date = {
            day.trade_date: [bar for bar in stock_bars if bar.trade_date == day.trade_date] for day in market_days
        }
        history_by_symbol: dict[str, list[StockBar]] = {}
        for bar in sorted(stock_bars, key=lambda item: (item.symbol, item.trade_date)):
            history_by_symbol.setdefault(bar.symbol, []).append(bar)
        account = AccountState()
        open_positions: list[OpenPosition] = []
        trades: list[Trade] = []
        rejected: list[tuple[Signal, tuple[str, ...]]] = []

        for index in range(1, len(cycles) - 3):
            entry_cycle = cycles[index]
            decision_cycle = cycles[index - 1]
            today_bars = bars_by_date.get(entry_cycle.trade_date, [])
            decision_bars = bars_by_date.get(decision_cycle.trade_date, [])
            today_by_symbol = {bar.symbol: bar for bar in today_bars}
            decision_by_symbol = {bar.symbol: bar for bar in decision_bars}

            exiting_today = [position for position in open_positions if position.exit_date == entry_cycle.trade_date]
            self._apply_exits(account, exiting_today)
            open_positions = [position for position in open_positions if position.exit_date > entry_cycle.trade_date]
            account.current_position_pct = sum(position.position_pct for position in open_positions)
            entered_symbols_today = {position.symbol for position in open_positions}

            for strategy in self.strategies:
                for signal in strategy.generate_with_history(decision_cycle, decision_bars, history_by_symbol):
                    if signal.symbol in entered_symbols_today:
                        rejected.append((signal, ("同一标的同一开仓日已被其他模式占用",)))
                        continue

                    decision_bar = decision_by_symbol.get(signal.symbol)
                    if decision_bar is None:
                        rejected.append((signal, ("决策日缺少标的行情，信号被拒绝",)))
                        continue

                    entry_bar = today_by_symbol.get(signal.symbol)
                    if entry_bar is None:
                        rejected.append((signal, ("入场日缺少行情，无法成交",)))
                        continue

                    if signal.min_entry_open_pct is not None and entry_bar.open_pct < signal.min_entry_open_pct:
                        rejected.append((signal, (f"次日开盘强度不足 {signal.min_entry_open_pct}%",)))
                        continue

                    decision = evaluate_signal(
                        signal,
                        decision_cycle,
                        decision_bar,
                        account,
                        min_amount_billion=self.risk_min_amount_billion,
                        enforce_pattern_cycle=self.enforce_pattern_cycle,
                        consecutive_loss_limit=self.consecutive_loss_limit,
                        single_position_limit_pct=self.single_position_limit_pct,
                        total_position_limit_pct=self.total_position_limit_pct,
                    )
                    if not decision.allowed:
                        rejected.append((signal, decision.reasons))
                        continue

                    exit_day, pnl_pct, exit_reason = self._simulate_exit(
                        index=index,
                        cycles=cycles,
                        stock_bars=stock_bars,
                        symbol=signal.symbol,
                        entry_price=entry_bar.open_price,
                        stop_loss_pct=signal.stop_loss_pct,
                    )
                    gross_pnl_pct = pnl_pct
                    buy_amount = self.capital * signal.planned_position_pct / 100
                    sell_amount = buy_amount * (1 + gross_pnl_pct / 100)
                    fee_amount = self.fee_model.estimate_fee(signal.symbol, buy_amount, max(0, sell_amount))
                    fee_pct = 0 if buy_amount <= 0 else fee_amount / buy_amount * 100
                    pnl_pct = gross_pnl_pct - fee_pct
                    after_3d_day = cycles[index + 3].trade_date
                    after_3d_bar = self._find_bar(stock_bars, after_3d_day, signal.symbol)
                    after_3d = (
                        None
                        if after_3d_bar is None or entry_bar.open_price <= 0
                        else round((after_3d_bar.close_price / entry_bar.open_price - 1) * 100, 2)
                    )
                    exit_price = round(entry_bar.open_price * (1 + pnl_pct / 100), 3)
                    trades.append(
                        Trade(
                            signal_date=signal.trade_date,
                            entry_date=entry_cycle.trade_date,
                            exit_date=exit_day,
                            symbol=signal.symbol,
                            name=signal.name,
                            pattern=signal.pattern,
                            cycle_tag=decision_cycle.tag,
                            entry_price=entry_bar.open_price,
                            exit_price=exit_price,
                            position_pct=signal.planned_position_pct,
                            pnl_pct=round(pnl_pct, 2),
                            exit_reason=exit_reason,
                            signal_reason=signal.reason,
                            after_3d_return_pct=after_3d,
                            gross_pnl_pct=round(gross_pnl_pct, 2),
                            fee_pct=round(fee_pct, 2),
                            fee_amount=round(fee_amount, 2),
                        )
                    )

                    position = OpenPosition(
                        symbol=signal.symbol,
                        exit_date=exit_day,
                        position_pct=signal.planned_position_pct,
                        pnl_pct=pnl_pct,
                        cut_loss=pnl_pct <= signal.stop_loss_pct,
                    )
                    open_positions.append(position)
                    account.current_position_pct += signal.planned_position_pct
                    entered_symbols_today.add(signal.symbol)

            account.cut_loss_today = False

        return BacktestResult(trades=trades, rejected_signals=rejected, metrics=summarize_trades(trades))

    def _simulate_exit(
        self,
        index: int,
        cycles: list,
        stock_bars: list[StockBar],
        symbol: str,
        entry_price: float,
        stop_loss_pct: float,
    ) -> tuple[date, float, str]:
        max_exit_index = min(index + 2, len(cycles) - 1)
        first_sell_index = min(index + 1, len(cycles) - 1)
        for exit_index in range(first_sell_index, max_exit_index + 1):
            day = cycles[exit_index].trade_date
            bar = self._find_bar(stock_bars, day, symbol)
            if bar and entry_price > 0 and (bar.low_price / entry_price - 1) * 100 <= stop_loss_pct:
                return day, stop_loss_pct, "T+1硬止损"

        exit_day = cycles[max_exit_index].trade_date
        exit_bar = self._find_bar(stock_bars, exit_day, symbol)
        if exit_bar is None or entry_price <= 0:
            return exit_day, 0, "退出日缺少个股行情（停牌/数据缺口）"
        return exit_day, round((exit_bar.close_price / entry_price - 1) * 100, 2), "时间止损/两日退出"

    @staticmethod
    def _apply_exits(account: AccountState, positions: list[OpenPosition]) -> None:
        if not positions:
            return
        for position in positions:
            account.consecutive_losses = account.consecutive_losses + 1 if position.pnl_pct < 0 else 0
        account.cut_loss_today = account.cut_loss_today or any(position.cut_loss for position in positions)

    @staticmethod
    def _find_bar(stock_bars: list[StockBar], trade_date: date, symbol: str) -> StockBar | None:
        return next((candidate for candidate in stock_bars if candidate.trade_date == trade_date and candidate.symbol == symbol), None)
