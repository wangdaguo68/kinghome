from datetime import date, timedelta

from app.backtest.engine import BacktestEngine, OpenPosition
from app.backtest.fees import BrokerFeeModel
from app.data.demo import demo_market_days, demo_stock_bars
from app.data.schemas import CycleState, CycleTag, MarketDay, Pattern, Signal, StockBar
from app.risk.gates import AccountState
from app.strategies.base import Strategy
from app.strategies.extreme_arbitrage import ExtremeArbitrageStrategy
from app.strategies.first_limit import FirstLimitStrategy
from app.strategies.one_to_two import OneToTwoStrategy


def test_backtest_produces_trades_and_metrics() -> None:
    engine = BacktestEngine([ExtremeArbitrageStrategy(), FirstLimitStrategy(), OneToTwoStrategy()])
    result = engine.run(demo_market_days(), demo_stock_bars())
    assert result.metrics["trade_count"] > 0
    assert "total_return_pct" in result.metrics
    assert all(trade.after_3d_return_pct is not None for trade in result.trades)


class FixedSignalStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP}

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        if cycle.tag != CycleTag.TURN_UP:
            return []
        return [
            Signal(
                trade_date=cycle.trade_date,
                symbol="000001",
                name="华夏科技",
                pattern=Pattern.FIRST_LIMIT,
                score=1,
                planned_position_pct=20,
                stop_loss_pct=-5,
                reason="fixed test signal",
            )
        ]


class DuplicateSignalStrategy(FixedSignalStrategy):
    pass


def _market_days() -> list[MarketDay]:
    start = date(2026, 5, 1)
    counts = [900, 1200, 1500, 1800, 2100, 2300, 2500]
    return [MarketDay(start + timedelta(days=i), count, 10, 3, 0, 900) for i, count in enumerate(counts)]


def _bars(low_pct: float = 0, close_price: float = 103) -> list[StockBar]:
    rows = []
    for day in _market_days():
        rows.append(
            StockBar(
                trade_date=day.trade_date,
                symbol="000001",
                name="华夏科技",
                open_price=100,
                high_price=105,
                low_price=100 + low_pct,
                close_price=close_price,
                pre_close=100,
                open_pct=0,
                close_pct=3,
                high_pct=5,
                low_pct=low_pct,
                amount_billion=12,
                auction_amount_million=0,
                volume_ratio=0,
                limit_up=True,
                first_limit=True,
                consecutive_limits=1,
                sector_rank=1,
            )
        )
    return rows


def test_backtest_enters_after_decision_day_not_same_day() -> None:
    result = BacktestEngine([FixedSignalStrategy()]).run(_market_days(), _bars())
    assert result.trades
    assert result.trades[0].entry_date > date(2026, 5, 2)


def test_backtest_uses_intraday_low_for_hard_stop() -> None:
    result = BacktestEngine([FixedSignalStrategy()]).run(_market_days(), _bars(low_pct=-7))
    assert result.trades
    assert result.trades[0].exit_reason == "T+1硬止损"
    assert result.trades[0].pnl_pct == -5


def test_backtest_respects_a_share_t_plus_one_exit_rule() -> None:
    result = BacktestEngine([FixedSignalStrategy()]).run(_market_days(), _bars(low_pct=-7))

    assert result.trades
    assert result.trades[0].exit_date > result.trades[0].entry_date


def test_backtest_uses_real_exit_close_price_path() -> None:
    result = BacktestEngine([FixedSignalStrategy()]).run(_market_days(), _bars(close_price=110))
    assert result.trades
    assert result.trades[0].pnl_pct == 10
    assert result.trades[0].exit_price == 110


def test_missing_exit_bar_reports_data_gap_reason() -> None:
    days = _market_days()
    bars = [bar for bar in _bars() if bar.trade_date != days[3].trade_date]
    exit_day, pnl_pct, exit_reason = BacktestEngine([FixedSignalStrategy()])._simulate_exit(
        index=1,
        cycles=days,
        stock_bars=bars,
        symbol="000001",
        entry_price=100,
        stop_loss_pct=-5,
    )

    assert exit_day == days[3].trade_date
    assert pnl_pct == 0
    assert exit_reason == "退出日缺少个股行情（停牌/数据缺口）"


def test_backtest_can_report_net_return_after_fees() -> None:
    fee_model = BrokerFeeModel("test", 1, 5, 0, 0.0002, 0.0005, 0)
    result = BacktestEngine([FixedSignalStrategy()], fee_model=fee_model, capital=50000).run(
        _market_days(),
        _bars(close_price=110),
    )

    assert result.trades[0].gross_pnl_pct == 10
    assert result.trades[0].fee_amount == 15.5
    assert result.trades[0].fee_pct == 0.15
    assert result.trades[0].pnl_pct == 9.85


def test_same_symbol_enters_once_per_entry_day() -> None:
    result = BacktestEngine([FixedSignalStrategy(), DuplicateSignalStrategy()]).run(_market_days(), _bars())
    assert len(result.trades) == 1
    assert result.rejected_signals
    assert "同一标的" in result.rejected_signals[0][1][0]


def test_same_day_hard_stop_updates_account_state() -> None:
    account = AccountState()
    position = OpenPosition("000001", date(2026, 5, 2), 20, -5, True)
    BacktestEngine._apply_exits(account, [position])
    assert account.consecutive_losses == 1
    assert account.cut_loss_today


def test_multiple_exits_keep_cut_loss_flag() -> None:
    account = AccountState()
    positions = [
        OpenPosition("000001", date(2026, 5, 2), 20, -5, True),
        OpenPosition("000002", date(2026, 5, 2), 20, 3, False),
    ]
    BacktestEngine._apply_exits(account, positions)
    assert account.cut_loss_today


class MissingSymbolStrategy(Strategy):
    enabled_cycles = {CycleTag.TURN_UP}

    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        return [
            Signal(
                trade_date=cycle.trade_date,
                symbol="999999",
                name="不存在标的",
                pattern=Pattern.FIRST_LIMIT,
                score=1,
                planned_position_pct=5,
                stop_loss_pct=-5,
                reason="missing symbol",
            )
        ]


def test_missing_decision_bar_rejects_signal_without_crashing() -> None:
    result = BacktestEngine([MissingSymbolStrategy()]).run(_market_days(), _bars())
    assert not result.trades
    assert result.rejected_signals
    assert "决策日缺少" in result.rejected_signals[0][1][0]
