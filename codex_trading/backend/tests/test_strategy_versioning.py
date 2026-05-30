from datetime import date, timedelta
from pathlib import Path

from app.backtest import versioning
from app.backtest.fees import NO_FEE_MODEL
from app.backtest.versioning import (
    read_strategy_version_cache,
    split_market_days,
    strategy_version_context,
    strategy_version_fingerprint,
    version_decision,
    write_strategy_version_cache,
)
from app.data.schemas import MarketDay
from app.strategies.experiment import PRESETS, StrategyPreset


TEST_CACHE = Path(__file__).resolve().parents[1] / "cache" / "test_strategy_versions.json"


def _days(count: int) -> list[MarketDay]:
    start = date(2026, 1, 1)
    return [MarketDay(start + timedelta(days=index), 1000, 10, 2, 0, 900) for index in range(count)]


def test_split_market_days_keeps_recent_observation_segment() -> None:
    train, validation, recent = split_market_days(_days(250))

    assert len(train) == 158
    assert len(validation) == 69
    assert len(recent) == 23
    assert train[-1].trade_date < validation[0].trade_date < recent[0].trade_date


def test_split_market_days_does_not_overlap_short_sample() -> None:
    train, validation, recent = split_market_days(_days(60))

    assert train
    assert validation
    assert recent
    assert set(train).isdisjoint(validation)
    assert set(train).isdisjoint(recent)
    assert set(validation).isdisjoint(recent)


def test_version_decision_accepts_positive_train_validation_and_recent() -> None:
    result = version_decision(
        {"trade_count": 80, "total_return_pct": 10, "max_drawdown_pct": -3},
        {"trade_count": 20, "total_return_pct": 4, "max_drawdown_pct": -2},
        {"trade_count": 8, "total_return_pct": 1, "max_drawdown_pct": -1},
    )

    assert result["eligible"]
    assert result["verdict"] == "可进入明日策略候选"


def test_version_decision_rejects_failed_validation() -> None:
    result = version_decision(
        {"trade_count": 80, "total_return_pct": 10, "max_drawdown_pct": -3},
        {"trade_count": 20, "total_return_pct": -1, "max_drawdown_pct": -2},
        {"trade_count": 8, "total_return_pct": 1, "max_drawdown_pct": -1},
    )

    assert not result["eligible"]
    assert any("验证段" in reason for reason in result["reasons"])


def test_strategy_version_cache_recovers_from_invalid_json(monkeypatch) -> None:
    TEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TEST_CACHE.unlink(missing_ok=True)
    monkeypatch.setattr(versioning, "VERSION_CACHE", TEST_CACHE)
    versioning.VERSION_CACHE.write_text("{broken", encoding="utf-8")

    try:
        assert read_strategy_version_cache() is None
    finally:
        TEST_CACHE.unlink(missing_ok=True)


def test_strategy_version_cache_writes_readable_json(monkeypatch) -> None:
    TEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TEST_CACHE.unlink(missing_ok=True)
    monkeypatch.setattr(versioning, "VERSION_CACHE", TEST_CACHE)
    payload = {"cache_key": "abc", "groups": []}

    try:
        write_strategy_version_cache(payload)
        assert read_strategy_version_cache() == payload
    finally:
        TEST_CACHE.unlink(missing_ok=True)


def test_strategy_version_fingerprint_changes_with_capital() -> None:
    def candidates(base: StrategyPreset) -> list[StrategyPreset]:
        return [base]

    def settings(preset: StrategyPreset) -> dict[str, object]:
        return {"id": preset.id}

    first = strategy_version_context(PRESETS, NO_FEE_MODEL, 100000, candidates, settings)
    second = strategy_version_context(PRESETS, NO_FEE_MODEL, 200000, candidates, settings)

    assert strategy_version_fingerprint(first) != strategy_version_fingerprint(second)
