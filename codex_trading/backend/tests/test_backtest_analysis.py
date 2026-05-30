from datetime import date

from app.backtest.analysis import board_name, quality_breakdown, trade_reflection
from app.data.schemas import CycleTag, Pattern, Trade


def _trade(symbol: str, entry_date: date, pattern: Pattern, pnl_pct: float) -> Trade:
    return Trade(
        signal_date=entry_date,
        entry_date=entry_date,
        exit_date=entry_date,
        symbol=symbol,
        name="样本",
        pattern=pattern,
        cycle_tag=CycleTag.TURN_UP,
        entry_price=10,
        exit_price=10 * (1 + pnl_pct / 100),
        position_pct=10,
        pnl_pct=pnl_pct,
        exit_reason="test",
        signal_reason="test",
    )


def test_board_name_splits_cyb_from_main_board() -> None:
    assert board_name("300001.SZ") == "创业板"
    assert board_name("301001.SZ") == "创业板"
    assert board_name("600000.SH") == "沪深主板"
    assert board_name("002001.SZ") == "沪深主板"


def test_quality_breakdown_groups_by_pattern_month_and_board() -> None:
    trades = [
        _trade("300001.SZ", date(2026, 1, 3), Pattern.FIRST_LIMIT, 10),
        _trade("600000.SH", date(2026, 1, 4), Pattern.FIRST_LIMIT, -5),
        _trade("002001.SZ", date(2026, 2, 1), Pattern.ONE_TO_TWO, 4),
    ]

    result = quality_breakdown(trades)

    assert [row["key"] for row in result["by_month"]] == ["2026-01", "2026-02"]
    assert {row["key"] for row in result["by_board"]} == {"创业板", "沪深主板"}
    first_limit = next(row for row in result["by_pattern"] if row["key"] == Pattern.FIRST_LIMIT)
    assert first_limit["metrics"]["trade_count"] == 2


def test_trade_reflection_returns_actionable_sections() -> None:
    trades = [
        _trade("300001.SZ", date(2026, 1, day), Pattern.FIRST_LIMIT, 8)
        for day in range(1, 8)
    ] + [
        _trade("600000.SH", date(2026, 2, day), Pattern.ONE_TO_TWO, -5)
        for day in range(1, 8)
    ]

    result = trade_reflection(trades)

    assert result["verdict"]
    assert result["strengths"]
    assert result["weaknesses"]
    assert result["suggestions"]
