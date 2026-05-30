from datetime import date
from pathlib import Path

from app.data.schemas import StockBar
from app.live.intraday import IntradayQuote, load_intraday_quotes, scan_intraday_quotes
from app.live.tracker import sync_intraday_signals


TEST_TRACK_FILE = Path(__file__).resolve().parents[1] / "cache" / "test_intraday_tracks.json"


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_text(self, text: str) -> dict[str, object]:
        self.messages.append(text)
        return {"sent": True}


def test_intraday_scan_finds_first_limit_reseal() -> None:
    quote = IntradayQuote(
        symbol="000001.SZ",
        name="平安银行",
        price=11.0,
        pre_close=10.0,
        high=11.0,
        low=10.1,
        pct=10.0,
        amount_billion=6,
        sector_rank=50,
        source="test",
    )

    result = scan_intraday_quotes([quote], "TurnUp")

    assert result["signal_count"] == 1
    assert result["signals"][0]["pattern"] == "IntradayFirstLimit"


def test_intraday_scan_blocks_star_market_symbol() -> None:
    quote = IntradayQuote(
        symbol="688001.SH",
        name="科创样本",
        price=22.0,
        pre_close=20.0,
        high=22.0,
        low=20.1,
        pct=10.0,
        amount_billion=8,
        sector_rank=1,
    )

    result = scan_intraday_quotes([quote], "TurnUp")

    assert result["signal_count"] == 0


def test_intraday_loader_does_not_use_daily_fallback_by_default(monkeypatch) -> None:
    monkeypatch.delenv("INTRADAY_ALLOW_DAILY_FALLBACK", raising=False)
    bar = StockBar(
        trade_date=date(2026, 5, 29),
        symbol="000001.SZ",
        name="平安银行",
        open_price=10,
        high_price=11,
        low_price=10,
        close_price=11,
        pre_close=10,
        open_pct=0,
        close_pct=10,
        high_pct=10,
        low_pct=0,
        amount_billion=6,
        auction_amount_million=100,
        volume_ratio=1,
        limit_up=True,
        first_limit=True,
        consecutive_limits=1,
        sector_rank=10,
    )

    status, quotes = load_intraday_quotes([bar])

    assert not status["ready"]
    assert quotes == []


def test_intraday_signal_deduplicates(monkeypatch) -> None:
    from app.live import tracker

    TEST_TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_TRACK_FILE.unlink(missing_ok=True)
    monkeypatch.setattr(tracker, "TRACK_FILE", TEST_TRACK_FILE)
    scan = {
        "signals": [
            {
                "scanned_at": "2026-05-29T10:00:00",
                "symbol": "000001.SZ",
                "name": "平安银行",
                "pattern": "IntradayFirstLimit",
                "trigger": "盘中触板/回封",
                "cycle_tag": "TurnUp",
                "price": 11,
                "pct": 10,
                "amount_billion": 6,
                "sector_rank": 10,
                "planned_position_pct": 6,
                "stop_loss_pct": -5,
                "execution_rule": "人工确认",
                "source": "test",
            }
        ]
    }
    notifier = FakeNotifier()

    try:
        first = sync_intraday_signals(scan, notifier)
        second = sync_intraday_signals(scan, notifier)

        assert first["new_count"] == 1
        assert second["new_count"] == 0
        assert len(notifier.messages) == 1
    finally:
        TEST_TRACK_FILE.unlink(missing_ok=True)
