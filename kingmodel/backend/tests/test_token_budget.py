import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.config import get_settings
from app.db import (
    collection_status,
    initialize,
    latest_trusted_snapshot,
    reserve_tdx_call,
    save_snapshot,
)
from app.services import close_collector as close_module
from app.services.close_collector import CloseCollector


def configure_database(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "budget.db"))
    get_settings.cache_clear()
    initialize()


def test_tdx_budget_is_atomic_and_never_exceeds_daily_limit(monkeypatch, tmp_path) -> None:
    configure_database(monkeypatch, tmp_path)
    trade_date = "20260622"

    def reserve(index: int) -> bool:
        return reserve_tdx_call(trade_date, f"600{index:03d}", "limit_up_cause", datetime.now().isoformat(), 5)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(reserve, range(20)))

    assert sum(results) == 5
    assert collection_status(trade_date, 5)["tdx_calls_used"] == 5
    get_settings.cache_clear()


def test_same_stock_can_only_reserve_once_per_day(monkeypatch, tmp_path) -> None:
    configure_database(monkeypatch, tmp_path)
    assert reserve_tdx_call("20260622", "600353", "limit_up_cause", "2026-06-22T15:10:00+08:00", 5)
    assert not reserve_tdx_call("20260622", "600353", "limit_up_cause", "2026-06-22T15:11:00+08:00", 5)
    get_settings.cache_clear()


def test_degraded_snapshot_does_not_replace_published_snapshot(monkeypatch, tmp_path) -> None:
    configure_database(monkeypatch, tmp_path)
    published = {
        "meta": {"updated_at": "2026-06-22T15:10:00+08:00", "trade_date": "2026.06.22", "source": "free", "freshness": "live"},
        "ladder": [{"code": "600353"}],
        "planned_targets": [{"code": "600353"}],
    }
    degraded = {
        "meta": {"updated_at": "2026-06-22T15:11:00+08:00", "trade_date": "2026.06.22", "source": "failed", "freshness": "stale"},
        "ladder": [],
        "planned_targets": [],
    }
    save_snapshot(published, official=True)
    save_snapshot(degraded)
    assert json.dumps(latest_trusted_snapshot(), sort_keys=True) == json.dumps(published, sort_keys=True)
    get_settings.cache_clear()


def test_one_hundred_manual_refreshes_never_call_tdx(monkeypatch, tmp_path) -> None:
    configure_database(monkeypatch, tmp_path)
    monkeypatch.setenv("TDX_CLOSE_ENRICHMENT_ENABLED", "false")
    get_settings.cache_clear()

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 22, 16, 0, tzinfo=tz or timezone(timedelta(hours=8)))

    dates = ["20260622", "20260618", "20260617", "20260616", "20260615", "20260612"]
    pools = {
        date: [
            {"code": "600353", "name": "旭光电子", "change": 10.0, "industry": "电子", "first_limit_time": "093000"},
            {"code": "000811", "name": "冰轮环境", "change": 10.0, "industry": "数据中心", "first_limit_time": "094000"},
            {"code": "300001", "name": "弹性样本", "change": 20.0, "industry": "科技", "first_limit_time": "100000"},
            {"code": "600001", "name": "样本一", "change": 10.0, "industry": "制造", "first_limit_time": "101000"},
            {"code": "600002", "name": "样本二", "change": 10.0, "industry": "制造", "first_limit_time": "102000"},
        ]
        for date in dates
    }
    monkeypatch.setattr(close_module, "datetime", FixedDateTime)
    collector = CloseCollector()
    collector.free.recent_pools = AsyncMock(return_value=(dates, pools))
    collector.tdx._cause = AsyncMock(side_effect=AssertionError("manual refresh must not call TDX"))

    async def run_refreshes() -> None:
        for _ in range(100):
            await collector.refresh(allow_tdx=False)

    asyncio.run(run_refreshes())
    assert collector.tdx._cause.await_count == 0
    assert collector.free.recent_pools.await_count == 1
    assert collection_status("20260622", 5)["tdx_calls_used"] == 0
    get_settings.cache_clear()
