import json
import asyncio
from copy import deepcopy
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
    collector.free.market_breadth = AsyncMock(return_value={
        "trade_date": "20260622",
        "breadth": {"eligible": 5200, "up": 2600, "down": 2500, "flat": 100, "median": 0, "limit_up": 5, "limit_down": 5, "failed_limit": 10},
        "capacity": {"sample": 100, "up": 50, "down": 50, "median": 0},
    })
    collector.tdx._cause = AsyncMock(side_effect=AssertionError("manual refresh must not call TDX"))

    async def run_refreshes() -> None:
        for _ in range(100):
            await collector.refresh(allow_tdx=False)

    asyncio.run(run_refreshes())
    assert collector.tdx._cause.await_count == 0
    assert collector.free.recent_pools.await_count == 1
    assert collection_status("20260622", 5)["tdx_calls_used"] == 0
    get_settings.cache_clear()


def test_close_snapshot_uses_same_day_free_breadth_instead_of_previous_official(monkeypatch, tmp_path) -> None:
    configure_database(monkeypatch, tmp_path)
    monkeypatch.setenv("TUSHARE_TOKEN", "token")
    get_settings.cache_clear()

    previous = {
        "meta": {
            "updated_at": "2026-06-22T15:10:00+08:00",
            "trade_date": "2026.06.22",
            "source": "previous",
            "freshness": "live",
        },
        "permission": {"label": "顺风进攻", "position_limit": 75, "allowed": "旧许可", "forbidden": "旧禁止"},
        "state": {"cycle": "主升", "structure": "旧结构", "money": 70, "loss": 20, "trend": 70, "speculation": 70},
        "breadth": {
            "eligible": 5510, "up": 2916, "down": 2468, "flat": 126,
            "median": 0.2427, "limit_up": 137, "limit_down": 3, "failed_limit": 33, "continuous": 10,
        },
        "capacity": {"sample": 100, "up": 78, "down": 22, "median": 4.2988, "source": "Tushare上一日", "label": "容量正反馈"},
        "mainlines": [{"name": "昨日主线", "score": 88, "role": "主线", "change": 8.0, "flow": "", "tags": []}],
        "negative": [{"name": "昨日负反馈", "change": -1.0, "severity": "medium"}],
        "alerts": [],
        "ladder": [{"name": "旧票", "code": "600000", "height": 2, "change": 10.0, "concepts": ["旧"], "primary_factor": "旧", "factor_type": "旧", "confidence": "中", "evidence": "旧", "source": "旧"}],
        "cores": [],
        "planned_targets": [],
        "data_quality": {},
        "sentiment": [],
        "checkpoints": [],
    }
    save_snapshot(previous, official=True)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 23, 16, 0, tzinfo=tz or timezone(timedelta(hours=8)))

    dates = ["20260623", "20260622", "20260618", "20260617", "20260616", "20260615"]
    pools = {
        "20260623": [
            {"code": "600397", "name": "江钨装备", "change": 9.99, "industry": "专用设备", "amount": 4_000_000_000, "first_limit_time": "092502"},
            {"code": "002167", "name": "东方锆业", "change": 9.98, "industry": "小金属", "amount": 1_900_000_000, "first_limit_time": "092500"},
            {"code": "002674", "name": "兴业科技", "change": 10.0, "industry": "纺织制造", "amount": 19_000_000, "first_limit_time": "092500"},
            {"code": "300085", "name": "银之杰", "change": 20.0, "industry": "软件开发", "amount": 4_600_000_000, "first_limit_time": "093415"},
            {"code": "600172", "name": "黄河旋风", "change": 9.99, "industry": "通用设备", "amount": 5_400_000_000, "first_limit_time": "093342"},
            {"code": "601869", "name": "长飞光纤", "change": 10.0, "industry": "通信设备", "amount": 12_900_000_000, "first_limit_time": "102625"},
            {"code": "000070", "name": "特发信息", "change": 10.0, "industry": "通信设备", "amount": 1_200_000_000, "first_limit_time": "093257"},
        ],
        "20260622": [
            {"code": "600397", "name": "江钨装备", "change": 10.0, "industry": "专用设备", "amount": 2_000_000_000, "first_limit_time": "093000"},
            {"code": "002167", "name": "东方锆业", "change": 10.0, "industry": "小金属", "amount": 1_000_000_000, "first_limit_time": "093000"},
            {"code": "002674", "name": "兴业科技", "change": 10.0, "industry": "纺织制造", "amount": 18_000_000, "first_limit_time": "093000"},
        ],
    }
    for date in dates[2:]:
        pools[date] = []

    monkeypatch.setattr(close_module, "datetime", FixedDateTime)
    collector = CloseCollector()
    collector.free.recent_pools = AsyncMock(return_value=(dates, pools))
    collector.free.market_breadth = AsyncMock(return_value={
        "trade_date": "20260623",
        "breadth": {
            "eligible": 5196, "up": 2549, "down": 2544, "flat": 103,
            "median": 0.0, "limit_up": 7, "limit_down": 39, "failed_limit": 50,
        },
        "capacity": {"sample": 100, "up": 28, "down": 72, "median": -3.2623},
    })
    collector.tdx._cause = AsyncMock(side_effect=AssertionError("manual refresh must not call TDX"))

    result = asyncio.run(collector.refresh(allow_tdx=False))

    assert result["meta"]["trade_date"] == "2026.06.23"
    assert result["breadth"]["up"] == 2549
    assert result["breadth"]["down"] == 2544
    assert result["breadth"]["limit_down"] == 39
    assert result["breadth"]["failed_limit"] == 50
    assert result["breadth"]["limit_up"] == 7
    assert result["capacity"]["up"] == 28
    assert result["capacity"]["median"] == -3.2623
    assert result["capacity"]["label"] == "容量负反馈"
    assert result["permission"]["label"] == "防守观察"
    assert result["permission"]["position_limit"] == 20
    assert result["negative"][0]["name"] == "容量前100负反馈"
    assert result["mainlines"][0]["source"] == "东方财富免费涨停池行业聚合"
    assert result["data_quality"]["breadth"]["source"] == "东方财富全A行情列表"
    assert collector.tdx._cause.await_count == 0
    assert collector.free.market_breadth.await_count == 1
    assert collection_status("20260623", 5)["tdx_calls_used"] == 0
    get_settings.cache_clear()


def test_market_snapshot_falls_back_to_tushare_with_manual_breadth_override(monkeypatch) -> None:
    monkeypatch.setenv("TUSHARE_TOKEN", "token")
    get_settings.cache_clear()
    collector = CloseCollector()
    collector.free.market_breadth = AsyncMock(side_effect=RuntimeError("eastmoney clist down"))
    collector.tushare.market_snapshot = AsyncMock(return_value={
        "trade_date": "20260623",
        "breadth": {
            "eligible": 5513, "up": 2764, "down": 2644, "flat": 105,
            "median": 0.0481, "limit_up": 97, "limit_down": 41, "failed_limit": 59,
        },
        "capacity": {"sample": 100, "up": 28, "down": 72, "median": -3.2623},
        "negative_sectors": [],
    })

    snapshot, error = asyncio.run(collector._same_day_market_snapshot("20260623", 94))

    assert error == ""
    assert snapshot is not None
    assert snapshot["source"] == "人工校准广度 + Tushare容量"
    assert snapshot["calibrated_breadth"] is True
    assert snapshot["breadth"]["eligible"] == 5196
    assert snapshot["breadth"]["up"] == 2549
    assert snapshot["breadth"]["down"] == 2544
    assert snapshot["breadth"]["flat"] == 103
    assert snapshot["breadth"]["limit_up"] == 94
    assert snapshot["breadth"]["limit_down"] == 39
    assert snapshot["breadth"]["failed_limit"] == 50
    assert snapshot["capacity"]["median"] == -3.2623
    assert collector.free.market_breadth.await_count == 1
    assert collector.tushare.market_snapshot.await_count == 1
    get_settings.cache_clear()


def test_missing_same_day_market_uses_previous_reliable_context_without_publishing(monkeypatch, tmp_path) -> None:
    configure_database(monkeypatch, tmp_path)
    monkeypatch.setenv("TUSHARE_TOKEN", "token")
    get_settings.cache_clear()

    previous = {
        "meta": {
            "updated_at": "2026-06-24T15:10:00+08:00",
            "trade_date": "2026.06.24",
            "source": "previous",
            "freshness": "live",
        },
        "permission": {"label": "顺风进攻", "position_limit": 75, "allowed": "旧允许", "forbidden": "旧禁止"},
        "state": {"cycle": "主升", "structure": "趋势风格", "money": 70, "loss": 20, "trend": 70, "speculation": 55},
        "breadth": {
            "eligible": 5510, "up": 3000, "down": 2300, "flat": 210,
            "median": 0.21, "limit_up": 80, "limit_down": 9, "failed_limit": 24, "continuous": 12,
        },
        "capacity": {"sample": 100, "up": 68, "down": 32, "median": 1.82, "source": "previous", "label": "容量正反馈"},
        "capacity_cores": [
            {"name": "旧容量核心", "code": "600519", "kind": "趋势容量核心", "score": 88, "change": 2.1, "confidence": "高"}
        ],
        "mainlines": [{"name": "旧主线", "score": 88, "role": "主线", "change": 3.0, "flow": "", "tags": []}],
        "negative": [{"name": "旧负反馈", "change": -1.2, "severity": "medium"}],
        "alerts": [],
        "ladder": [],
        "cores": [],
        "planned_targets": [{"code": "600519"}],
        "data_quality": {},
        "sentiment": [],
        "checkpoints": [],
    }
    same_day_bad = deepcopy(previous)
    same_day_bad["meta"] = {
        "updated_at": "2026-06-25T15:10:00+08:00",
        "trade_date": "2026.06.25",
        "source": "bad",
        "freshness": "live",
    }
    same_day_bad["breadth"] = {"eligible": 0, "up": 0, "down": 0, "flat": 0, "median": 0, "limit_up": 85, "limit_down": 0, "failed_limit": 0}
    same_day_bad["capacity"] = {"sample": 0, "up": 0, "down": 0, "median": 0}
    save_snapshot(previous, official=True)
    save_snapshot(same_day_bad, official=True)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 6, 25, 16, 0, tzinfo=tz or timezone(timedelta(hours=8)))

    dates = ["20260625", "20260624", "20260623", "20260622", "20260619", "20260618"]
    today_rows = [
        {"code": "600001", "name": "样本一", "change": 10.0, "industry": "机器人", "amount": 1_000_000_000, "first_limit_time": "093000"},
        {"code": "600002", "name": "样本二", "change": 10.0, "industry": "机器人", "amount": 900_000_000, "first_limit_time": "094000"},
        {"code": "000001", "name": "样本三", "change": 10.0, "industry": "消费", "amount": 800_000_000, "first_limit_time": "095000"},
        {"code": "000002", "name": "样本四", "change": 10.0, "industry": "消费", "amount": 700_000_000, "first_limit_time": "100000"},
        {"code": "300001", "name": "弹性一", "change": 20.0, "industry": "软件", "amount": 600_000_000, "first_limit_time": "101000"},
        {"code": "300002", "name": "弹性二", "change": 20.0, "industry": "软件", "amount": 500_000_000, "first_limit_time": "102000"},
    ]
    pools = {date: [] for date in dates}
    pools["20260625"] = today_rows
    pools["20260624"] = today_rows[:2]

    monkeypatch.setattr(close_module, "datetime", FixedDateTime)
    collector = CloseCollector()
    collector.free.recent_pools = AsyncMock(return_value=(dates, pools))
    collector.free.market_breadth = AsyncMock(side_effect=RuntimeError("eastmoney clist down"))
    collector.tushare.market_snapshot = AsyncMock(side_effect=RuntimeError("tushare daily empty"))
    collector.tdx._cause = AsyncMock(side_effect=AssertionError("manual refresh must not call TDX"))

    result = asyncio.run(collector.refresh(allow_tdx=False))

    assert result["meta"]["trade_date"] == "2026.06.25"
    assert result["meta"]["freshness"] == "stale"
    assert result["meta"]["version_label"] == "今日部分收盘版"
    assert result["breadth"]["eligible"] == 5510
    assert result["breadth"]["up"] == 3000
    assert result["breadth"]["limit_up"] == 6
    assert result["breadth"]["continuous"] == 2
    assert result["capacity"]["sample"] == 100
    assert result["capacity"]["median"] == 1.82
    assert result["negative"][0]["name"] == "旧负反馈"
    assert result["capacity_cores"][0]["code"] == "600519"
    assert result["planned_targets"] == []
    assert result["data_quality"]["breadth"]["status"] == "stale_fallback"
    assert result["data_quality"]["capacity_cores"]["status"] == "stale_fallback"
    assert result["collection_status"]["job"]["status"] == "failed"
    assert collection_status("20260625", 5)["tdx_calls_used"] == 0
    assert collector.tdx._cause.await_count == 0
    assert collector.free.market_breadth.await_count == 1
    assert collector.tushare.market_snapshot.await_count == 1
    get_settings.cache_clear()
