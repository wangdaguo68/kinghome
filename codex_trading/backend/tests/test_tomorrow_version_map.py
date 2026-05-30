from app import main
from app.data.schemas import MarketDay

from datetime import date


def test_tomorrow_version_map_selects_current_eligible_candidate(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "load_current_strategy_versions",
        lambda _days, _bars: {
            "groups": [
                {
                    "base_id": "balanced",
                    "recommended_version": {
                        "version_id": "balanced-tighter",
                        "eligible": True,
                    },
                }
            ]
        },
    )

    _, selected = main.tomorrow_version_map([], [])

    assert selected["balanced"].id == "balanced-tighter"


def test_tomorrow_version_map_ignores_stale_candidate_id(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "load_current_strategy_versions",
        lambda _days, _bars: {
            "groups": [
                {
                    "base_id": "balanced",
                    "recommended_version": {
                        "version_id": "balanced-old-parameter",
                        "eligible": True,
                    },
                }
            ]
        },
    )

    _, selected = main.tomorrow_version_map([], [])

    assert "balanced" not in selected


def test_load_current_strategy_versions_accepts_cached_date_string(monkeypatch) -> None:
    payload = {
        "segments": {"recent": {"end": "2026-01-01"}},
        "cache_key": "same-key",
        "groups": [],
    }

    monkeypatch.setattr(main, "load_broker_fee_model", lambda: object())
    monkeypatch.setattr(main, "backtest_capital", lambda: 100000)
    monkeypatch.setattr(main, "strategy_version_context", lambda *_args: {"ctx": "same"})
    monkeypatch.setattr(main, "strategy_version_fingerprint", lambda _context: "same-key")
    monkeypatch.setattr(main, "read_strategy_version_cache", lambda: payload)
    monkeypatch.setattr(
        main,
        "build_strategy_versions",
        lambda *_args: (_ for _ in ()).throw(AssertionError("cache should be reused")),
    )

    result = main.load_current_strategy_versions([MarketDay(date(2026, 1, 1), 1, 1, 0, 0, 1)], [])

    assert result is payload
