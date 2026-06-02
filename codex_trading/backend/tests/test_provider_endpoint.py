from datetime import date

import pytest

from app import main


def test_provider_uses_lightweight_mysql_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TUSHARE_RECENT_DAYS", "250")
    monkeypatch.setenv("TUSHARE_STOCK_BAR_LIMIT", "500")
    monkeypatch.setattr(
        main,
        "load_provider_summary",
        lambda recent_days, bar_limit: {
            "source": "tushare",
            "market_days": recent_days,
            "stock_bars": recent_days * bar_limit,
            "latest_date": date(2026, 6, 2),
        },
    )
    monkeypatch.setattr(main, "load_market_data", lambda: (_ for _ in ()).throw(AssertionError("provider should stay lightweight")))

    assert main.provider() == {
        "source": "tushare",
        "market_days": 250,
        "stock_bars": 125000,
        "latest_date": date(2026, 6, 2),
    }
