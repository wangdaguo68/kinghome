from datetime import date

from app.data.schemas import CycleState, CycleTag, Pattern, Signal, StockBar
from app.risk.gates import AccountState, evaluate_signal


def _cycle(tag: CycleTag) -> CycleState:
    return CycleState(date(2026, 5, 20), 1500, 10, 3, 1400, 1800, "up", "up", tag)


def _bar(amount: float = 12) -> StockBar:
    return StockBar(
        date(2026, 5, 20),
        "000001",
        "华夏科技",
        103,
        110,
        101,
        110,
        100,
        3,
        10,
        10,
        1,
        amount,
        0,
        0,
        True,
        True,
        1,
        1,
    )


def _signal(pattern: Pattern = Pattern.FIRST_LIMIT) -> Signal:
    return Signal(date(2026, 5, 20), "000001", "华夏科技", pattern, 10, 6, -5, "test")


def test_allows_valid_first_limit_signal() -> None:
    decision = evaluate_signal(_signal(), _cycle(CycleTag.TURN_UP), _bar(), AccountState())
    assert decision.allowed


def test_rejects_pattern_disabled_cycle() -> None:
    decision = evaluate_signal(_signal(), _cycle(CycleTag.DOWNTREND), _bar(), AccountState())
    assert not decision.allowed
    assert "未在" in decision.reasons[0]


def test_rejects_low_capacity() -> None:
    decision = evaluate_signal(_signal(), _cycle(CycleTag.TURN_UP), _bar(amount=4.9), AccountState())
    assert not decision.allowed
    assert "容量不达标" in decision.reasons[0]


def test_rejects_after_two_losses() -> None:
    decision = evaluate_signal(_signal(), _cycle(CycleTag.TURN_UP), _bar(), AccountState(consecutive_losses=2))
    assert not decision.allowed
    assert any("连续亏损" in reason for reason in decision.reasons)


def test_rejects_invalid_negative_position() -> None:
    signal = Signal(date(2026, 5, 20), "000001", "华夏科技", Pattern.FIRST_LIMIT, 10, -6, -5, "test")
    decision = evaluate_signal(signal, _cycle(CycleTag.TURN_UP), _bar(), AccountState())
    assert not decision.allowed
    assert any("计划仓位" in reason for reason in decision.reasons)


def test_rejects_signal_bar_mismatch() -> None:
    signal = Signal(date(2026, 5, 20), "000009", "错配标的", Pattern.FIRST_LIMIT, 10, 6, -5, "test")
    decision = evaluate_signal(signal, _cycle(CycleTag.TURN_UP), _bar(), AccountState())
    assert not decision.allowed
    assert any("标的" in reason for reason in decision.reasons)


def test_experiment_can_relax_capacity_gate_explicitly() -> None:
    decision = evaluate_signal(
        _signal(),
        _cycle(CycleTag.TURN_UP),
        _bar(amount=3),
        AccountState(),
        min_amount_billion=3,
    )
    assert decision.allowed


def test_experiment_can_disable_consecutive_loss_gate_explicitly() -> None:
    decision = evaluate_signal(
        _signal(),
        _cycle(CycleTag.TURN_UP),
        _bar(),
        AccountState(consecutive_losses=2),
        consecutive_loss_limit=None,
    )
    assert decision.allowed
