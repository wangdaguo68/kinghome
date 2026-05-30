from datetime import date
from pathlib import Path

from app.data.schemas import StockBar
from app.live import tracker
from app.live.tracker import refresh_tracking, sync_tomorrow_signals, tracked_signals


TEST_TRACK_FILE = Path(__file__).resolve().parents[1] / "cache" / "test_signal_tracks.json"


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_text(self, text: str) -> dict[str, object]:
        self.messages.append(text)
        return {"sent": True, "message_id": str(len(self.messages))}


def _plan() -> dict[str, object]:
    return {
        "plans": [
            {
                "id": "balanced",
                "name": "平衡版",
                "version_id": "balanced-tighter",
                "version_eligible": True,
                "signals": [
                    {
                        "signal_date": "2026-05-29",
                        "planned_entry_date": "2026-06-01",
                        "symbol": "000001.SZ",
                        "name": "平安银行",
                        "pattern": "FirstLimit",
                        "cycle_tag": "TurnUp",
                        "close_price": 10.0,
                        "planned_position_pct": 6,
                        "stop_loss_pct": -5,
                        "execution_rule": "开盘承接不弱时人工确认",
                        "reason": "测试信号",
                    }
                ],
            }
        ]
    }


def _bar(high: float, low: float, close: float) -> StockBar:
    return StockBar(
        trade_date=date(2026, 6, 1),
        symbol="000001.SZ",
        name="平安银行",
        open_price=10,
        high_price=high,
        low_price=low,
        close_price=close,
        pre_close=10,
        open_pct=0,
        close_pct=0,
        high_pct=0,
        low_pct=0,
        amount_billion=5,
        auction_amount_million=100,
        volume_ratio=1,
        limit_up=False,
        first_limit=False,
        consecutive_limits=0,
        sector_rank=1,
    )


def test_sync_tomorrow_signals_deduplicates_and_notifies(monkeypatch) -> None:
    TEST_TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_TRACK_FILE.unlink(missing_ok=True)
    monkeypatch.setattr(tracker, "TRACK_FILE", TEST_TRACK_FILE)
    notifier = FakeNotifier()

    try:
        first = sync_tomorrow_signals(_plan(), notifier)
        second = sync_tomorrow_signals(_plan(), notifier)

        assert first["new_count"] == 1
        assert second["new_count"] == 0
        assert len(notifier.messages) == 1
        assert tracked_signals()["active_count"] == 1
    finally:
        TEST_TRACK_FILE.unlink(missing_ok=True)


def test_refresh_tracking_marks_take_profit(monkeypatch) -> None:
    TEST_TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_TRACK_FILE.unlink(missing_ok=True)
    monkeypatch.setattr(tracker, "TRACK_FILE", TEST_TRACK_FILE)
    notifier = FakeNotifier()

    try:
        sync_tomorrow_signals(_plan(), notifier)
        result = refresh_tracking([_bar(high=10.9, low=10.1, close=10.8)], notifier)

        assert result["changed_count"] == 1
        assert result["tracks"][0]["status"] == "take_profit"
    finally:
        TEST_TRACK_FILE.unlink(missing_ok=True)
