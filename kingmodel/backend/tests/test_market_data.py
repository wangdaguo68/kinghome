import asyncio

import pytest

from app.services.market_validation import InvalidMarketData, is_trade_candidate, validate_breadth_totals, validate_result
from app.services.collector import _factor_type
from app.services.ladder import calculate_ladder_metrics, trade_dates_from_tdx_kline
from app.services.planning import build_planned_targets
from app.services.sector_linkage import build_sector_linkage
from app.services.capacity_core import build_capacity_cores, capacity_cores_as_candidates
from app.services.decision_context import build_event_signals, build_market_graph
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


@pytest.mark.parametrize(
    ("limit_dates", "expected_height", "expected_recent"),
    [
        (["2026-06-18", "2026-06-17", "2026-06-16", "2026-06-15", "2026-06-11"], 4, 4),
        (["2026-06-18", "2026-06-17", "2026-06-15", "2026-06-09"], 2, 3),
    ],
)
def test_ladder_uses_true_consecutive_trading_days(limit_dates: list[str], expected_height: int, expected_recent: int) -> None:
    trade_dates = ["20260618", "20260617", "20260616", "20260615", "20260612", "20260611"]
    metrics = calculate_ladder_metrics(limit_dates, trade_dates, "2026.06.18")
    assert metrics.consecutive == expected_height
    assert metrics.recent_limit_count == expected_recent
    assert metrics.recent_window_days == 5


def test_ladder_rejects_interval_board_as_consecutive() -> None:
    metrics = calculate_ladder_metrics(
        ["2026-06-18", "2026-06-16", "2026-06-15"],
        ["20260618", "20260617", "20260616", "20260615", "20260612"],
        "20260618",
    )
    assert metrics.consecutive == 1
    assert metrics.recent_limit_count == 3


def test_tdx_kline_dates_ignore_future_or_zero_volume_bar() -> None:
    payload = {
        "ListHead": {"ItemHead": ["Data", "Open", "Volume"]},
        "ListItem": [
            {"Item": ["20260617", "4074", "100"]},
            {"Item": ["20260618", "4094", "100"]},
            {"Item": ["20260622", "4090", "0"]},
        ],
    }
    assert trade_dates_from_tdx_kline(payload, "2026.06.18", 15) == ["20260618", "20260617"]


def test_planned_targets_are_ranked_deduplicated_and_exclude_unsupported_markets() -> None:
    cores = [
        {"name": "旭光电子", "code": "600353", "kind": "连板情绪核心", "score": 92, "evidence": "连续4板"},
        {"name": "旭光电子", "code": "600353", "kind": "趋势容量核心", "score": 85, "evidence": "容量重复"},
        {"name": "趋势样本", "code": "601138", "kind": "趋势容量核心", "score": 88, "evidence": "容量主动"},
        {"name": "弹性样本", "code": "300001", "kind": "创业板20cm弹性核心", "score": 89, "evidence": "20cm弹性"},
        {"name": "科创样本", "code": "688001", "kind": "趋势容量核心", "score": 99, "evidence": "排除"},
        {"name": "北交样本", "code": "920001", "kind": "趋势容量核心", "score": 99, "evidence": "排除"},
        {"name": "弱样本", "code": "600001", "kind": "趋势容量核心", "score": 79, "evidence": "不补足"},
    ]
    ladder = [{"code": "600353", "height": 4, "confidence": "高", "source": "通达信涨停分析", "concepts": ["可控核聚变"]}]
    targets = build_planned_targets(
        cores,
        ladder,
        cycle="主升",
        loss_score=30,
        freshness="live",
        mainline_names=["可控核聚变"],
    )
    assert [item["code"] for item in targets] == ["601138", "300001"]
    assert targets[0]["holding_period"] == "3–10日"
    assert targets[1]["holding_period"] == "1–3日"
    assert all(item["code"] != "600353" for item in targets)
    required_plan_fields = {
        "entry_preconditions", "entry_trigger", "no_buy_conditions", "position_plan",
        "stop_loss", "take_profit", "sell_plan",
    }
    for item in targets:
        assert required_plan_fields <= item.keys()
        assert all(item[field] for field in required_plan_fields)
    assert len({item["code"] for item in targets}) == len(targets)


def test_sector_linkage_feeds_planned_target_evidence() -> None:
    limit_rows = [
        {"code": "600100", "name": "核心龙头", "industry": "半导体", "change": 10, "amount": 3_000_000_000, "vendor_ladder": 2},
        {"code": "300100", "name": "弹性小弟", "industry": "半导体", "change": 20, "amount": 1_000_000_000, "vendor_ladder": 1},
        {"code": "002100", "name": "后排跟随", "industry": "半导体", "change": 10, "amount": 800_000_000, "vendor_ladder": 1},
        {"code": "600200", "name": "孤立高标", "industry": "纺织", "change": 10, "amount": 700_000_000, "vendor_ladder": 4},
    ]
    market_rows = [
        {"ts_code": "600100.SH", "industry": "半导体", "pct_chg": 10},
        {"ts_code": "300100.SZ", "industry": "半导体", "pct_chg": 20},
        {"ts_code": "002100.SZ", "industry": "半导体", "pct_chg": 10},
        {"ts_code": "002101.SZ", "industry": "半导体", "pct_chg": 6},
        {"ts_code": "600200.SH", "industry": "纺织", "pct_chg": 10},
        {"ts_code": "600201.SH", "industry": "纺织", "pct_chg": -2},
    ]

    linkage = build_sector_linkage(limit_rows, market_rows=market_rows)

    semiconductor = next(item for item in linkage if item["name"] == "半导体")
    textile = next(item for item in linkage if item["name"] == "纺织")
    assert semiconductor["score"] > textile["score"]
    assert semiconductor["elastic_count"] == 1
    assert semiconductor["follower_count"] == 2
    assert textile["isolated"] is True

    targets = build_planned_targets(
        [{"name": "核心龙头", "code": "600100", "kind": "连板情绪核心", "score": 86, "evidence": "板块核心", "concepts": ["半导体"]}],
        [{"code": "600100", "height": 2, "confidence": "中", "concepts": ["半导体"]}],
        cycle="高位震荡",
        loss_score=45,
        freshness="live",
        mainline_names=["半导体"],
        sector_linkage=linkage,
    )
    assert targets
    assert targets[0]["sector_linkage_level"] in {"强联动", "中联动"}
    assert targets[0]["sector_linkage_score"] == semiconductor["score"]
    assert targets[0]["sector_linkage_evidence"]
    assert "带动" in targets[0]["leader_effect"]


def test_capacity_cores_feed_trend_candidates_and_market_graph() -> None:
    market_rows = [
        {"ts_code": "601138.SH", "name": "工业富联", "industry": "元件", "pct_chg": 7.5, "amount": 33_000_000_000},
        {"ts_code": "688001.SH", "name": "科创样本", "industry": "元件", "pct_chg": 12.0, "amount": 30_000_000_000},
        {"ts_code": "600000.SH", "name": "容量跟随", "industry": "银行", "pct_chg": 1.0, "amount": 10_000_000_000},
    ]
    linkage = [{"name": "元件", "score": 82, "level": "强联动", "leader": "法拉电子", "follower_count": 6, "elastic_count": 2}]
    cores = build_capacity_cores(market_rows, mainlines=[{"name": "元件"}], sector_linkage=linkage)
    assert cores[0]["code"] == "601138"
    assert cores[0]["tradable"] is True
    assert any(item["code"] == "688001" and item["tradable"] is False for item in cores)

    candidates = capacity_cores_as_candidates(cores)
    assert candidates and candidates[0]["kind"] == "趋势容量核心"
    assert all(item["code"] != "688001" for item in candidates)

    payload = {
        "state": {"cycle": "主升", "structure": "趋势容量风格", "money": 75, "loss": 25},
        "breadth": {"up": 3000, "down": 2000},
        "capacity": {"sample": 100, "up": 70, "median": 2.4, "label": "容量正反馈"},
        "mainlines": [{"name": "元件", "score": 88, "flow": "容量主动进攻"}],
        "negative": [{"name": "地产", "change": -3.2}],
        "sector_linkage": [{"name": "元件", "score": 82, "level": "强联动", "leader": "法拉电子", "leader_code": "600563", "follower_count": 6, "elastic_count": 2, "limit_up_count": 7}],
        "capacity_cores": cores,
        "planned_targets": [{"name": "工业富联", "code": "601138", "score": 93, "priority": "A", "setup": "主线容量核心分歧回踩"}],
    }
    graph = build_market_graph(payload)
    assert any(node["type"] == "capacity_core" for node in graph["nodes"])
    assert any(edge["label"] == "交易计划" for edge in graph["edges"])


def test_capacity_core_normalizes_tushare_amount_and_reference_names() -> None:
    cores = build_capacity_cores(
        [{"ts_code": "603986.SH", "name": "", "industry": "", "pct_chg": 10, "amount": 39_944_848.281}],
        reference_rows=[{"code": "603986", "name": "兆易创新", "industry": "半导体"}],
        limit_codes={"603986"},
    )
    assert cores[0]["name"] == "兆易创新"
    assert cores[0]["industry"] == "半导体"
    assert cores[0]["amount"] == pytest.approx(39_944_848_281)
    assert cores[0]["amount_label"].endswith("亿")


def test_event_signals_affect_planned_target_validation() -> None:
    signals = build_event_signals(
        [{"topic": "元件", "heat": 80, "crowding": "中", "catalyst": "盘后复盘集中提及", "validation": "竞价容量确认"}],
        mainlines=[{"name": "元件", "score": 88, "change": 4, "flow": "容量主动"}],
        sector_linkage=[{"name": "元件", "score": 82, "level": "强联动"}],
    )
    targets = build_planned_targets(
        [{"name": "趋势核心", "code": "601138", "kind": "趋势容量核心", "score": 88, "evidence": "成交额主动", "concepts": ["元件"]}],
        [],
        cycle="主升",
        loss_score=25,
        freshness="live",
        mainline_names=["元件"],
        event_signals=signals,
    )
    assert targets
    assert targets[0]["event_signal_score"] is not None
    assert targets[0]["event_signals"][0]["validation"] == "竞价容量确认"


def test_planned_targets_do_not_fill_below_threshold() -> None:
    targets = build_planned_targets(
        [{"name": "弱样本", "code": "600001", "kind": "趋势容量核心", "score": 79, "evidence": "不足"}],
        [],
        cycle="高波动分歧",
        loss_score=60,
        freshness="live",
    )
    assert targets == []


def test_planned_targets_empty_when_market_data_is_incomplete() -> None:
    targets = build_planned_targets(
        [{"name": "强样本", "code": "601138", "kind": "趋势容量核心", "score": 98, "evidence": "容量主动"}],
        [],
        cycle="主升",
        loss_score=30,
        freshness="live",
        market_data_complete=False,
    )
    assert targets == []


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
