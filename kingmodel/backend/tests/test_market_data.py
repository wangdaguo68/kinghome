import asyncio

import pytest

from app.services.market_validation import InvalidMarketData, is_trade_candidate, validate_breadth_totals, validate_result
from app.services.collector import _factor_type
from app.services.tushare_fallback import TushareFallback


def result(total: int, rows: list[dict]) -> dict:
    return {"meta": {"total": total}, "data": rows}


def test_semantic_validation_rejects_wrong_direction() -> None:
    with pytest.raises(InvalidMarketData):
        validate_result("up", result(1, [{"sec_code": "000001", "chg0#": "-2.41"}]))


def test_semantic_validation_accepts_market_shape() -> None:
    validate_result("up", result(2_000, [{"sec_code": "000001", "chg": "1.20"}]))
    validate_result("limit_up", result(91, [{"sec_code": "600000", "chg": "10.01"}, {"sec_code": "300001", "chg": "20.00"}]))
    validate_result("amount_top", result(5_500, [{"sec_code": "601138", "chg": "7.49", "成交额": "33063390000"}]))
    validate_breadth_totals(1_958, 3_139, 90)


def test_trade_candidate_excludes_star_and_beijing() -> None:
    assert is_trade_candidate("300001") is True
    assert is_trade_candidate("600000") is True
    assert is_trade_candidate("688001") is False
    assert is_trade_candidate("920001") is False


def test_factor_type_prioritizes_primary_catalyst() -> None:
    assert _factor_type("可控核聚变+定增受理", "工信部：加强高端器件研发|公司拥有相关产能") == "政策"


def test_tushare_snapshot_computes_capacity(monkeypatch) -> None:
    client = TushareFallback("token", "https://example.invalid")

    async def fake_query(api_name: str, params: dict, fields: list[str]) -> list[dict]:
        if api_name == "stock_basic":
            return [
                {"ts_code": "600000.SH", "name": "浦发银行", "list_date": "19991110"},
                {"ts_code": "300001.SZ", "name": "特锐德", "list_date": "20091030"},
                {"ts_code": "920001.BJ", "name": "北交样本", "list_date": "20200101"},
            ]
        assert api_name == "daily"
        return [
            {"ts_code": "600000.SH", "trade_date": "20260618", "high": 11, "close": 11, "pre_close": 10, "pct_chg": 10, "amount": 300},
            {"ts_code": "300001.SZ", "trade_date": "20260618", "high": 12, "close": 11, "pre_close": 10, "pct_chg": 10, "amount": 200},
            {"ts_code": "920001.BJ", "trade_date": "20260618", "high": 9, "close": 9, "pre_close": 10, "pct_chg": -10, "amount": 100},
        ]

    monkeypatch.setattr(client, "_query", fake_query)
    snapshot = asyncio.run(client.market_snapshot("20260618"))
    assert snapshot["breadth"]["eligible"] == 3
    assert snapshot["breadth"]["limit_up"] == 1
    assert snapshot["capacity"] == {"sample": 3, "up": 2, "down": 1, "median": 10.0}
