from app.config import get_settings
from app.db import feature_store_status, initialize, save_feature_snapshots, save_shadow_plans
from app.engine.framework import assess_market, build_feature_snapshots, build_market_permission
from app.engine.rule_selector import (
    FEATURE_VERSION,
    PLAN_VERSION,
    build_shadow_top3,
    expected_value,
    passes_expectancy_gate,
    required_payoff_ratio,
)


def sample_payload() -> dict:
    return {
        "breadth": {
            "eligible": 5200, "up": 3400, "median": 0.8, "limit_up": 85,
            "limit_down": 5, "failed_limit": 12,
        },
        "capacity": {"sample": 100, "up": 68, "median": 1.2},
        "mainlines": [{"name": "算力", "score": 88}],
        "negative": [{"name": "地产", "score": 72}],
        "ladder": [
            {"code": "600001", "height": 5, "confidence": "高"},
            {"code": "600002", "height": 3, "confidence": "中"},
        ],
        "cores": [
            {"code": "600001", "name": "甲", "kind": "连板情绪核心", "score": 96, "change": 10, "confidence": "高"},
            {"code": "600002", "name": "乙", "kind": "趋势容量核心", "score": 91, "change": 4, "confidence": "中"},
            {"code": "300001", "name": "丙", "kind": "创业板20cm弹性核心", "score": 87, "change": 20, "confidence": "中"},
            {"code": "600003", "name": "丁", "kind": "趋势容量核心", "score": 70, "change": 2, "confidence": "低"},
        ],
    }


def test_market_assessment_has_explicit_style_cycle_and_scores() -> None:
    result = assess_market(sample_payload())
    assert result["style"] in {"趋势投机共振", "趋势风格", "投机连板风格", "混合轮动"}
    assert result["cycle"] in {"主升", "高位震荡", "退潮防守", "试错修复", "混沌轮动"}
    assert all(0 <= result[key] <= 100 for key in ("money", "loss", "trend", "speculation"))


def test_market_permission_hard_caps_high_loss_feedback() -> None:
    permission = build_market_permission(
        {"cycle": "高位震荡", "money": 67, "loss": 88, "trend": 38, "speculation": 99}
    )
    assert permission["label"] == "防守观察"
    assert permission["position_limit"] == 20
    assert "追涨" in permission["forbidden"]


def test_speculation_score_is_capped_by_limit_down_feedback() -> None:
    payload = sample_payload()
    payload["breadth"].update({
        "eligible": 5196,
        "up": 2549,
        "down": 2544,
        "flat": 103,
        "median": 0.0,
        "limit_up": 94,
        "limit_down": 39,
        "failed_limit": 50,
    })
    payload["capacity"] = {"sample": 100, "up": 28, "down": 72, "median": -3.2623}
    payload["ladder"] = [{"code": f"600{i:03d}", "height": 5 if i == 0 else 2, "confidence": "中"} for i in range(20)]
    payload["cores"] = [
        {"code": f"300{i:03d}", "name": f"弹性{i}", "kind": "创业板20cm弹性核心", "score": 92, "change": 20, "confidence": "中"}
        for i in range(7)
    ]
    result = assess_market(payload)
    assert result["speculation"] <= 65
    assert result["inputs"]["spec_hard_cap"] == 65
    assert result["inputs"]["spec_activity"] > result["inputs"]["spec_quality"]
    assert result["inputs"]["spec_risk"] >= 50


def test_market_permission_allows_attack_only_when_loss_is_low() -> None:
    permission = build_market_permission(
        {"cycle": "主升", "money": 75, "loss": 35, "trend": 72, "speculation": 80}
    )
    assert permission["label"] == "顺风进攻"
    assert permission["position_limit"] == 75


def test_shadow_top3_is_strictly_ranked_but_never_live_before_validation() -> None:
    payload = sample_payload()
    shadow = build_shadow_top3(payload, assess_market(payload))
    plans = shadow["plans"]
    assert len(plans) == 3
    assert [item["rank"] for item in plans] == [1, 2, 3]
    assert all(left["score"] > right["score"] for left, right in zip(plans, plans[1:]))
    assert all(0 <= item["score"] <= 100 for item in plans)
    assert all(item["score_breakdown"]["expectancy_payoff"] == 0 for item in plans)
    assert all(item["eligible_for_live"] is False for item in plans)


def test_retreat_cycle_returns_empty_plan() -> None:
    result = build_shadow_top3(sample_payload(), {"style": "混合轮动", "cycle": "退潮防守", "loss": 85})
    assert result["plans"] == []
    assert result["status"] == "empty"


def test_payoff_gate_requires_positive_expectancy_and_safety_margin() -> None:
    assert expected_value(0.40, 2.2, 1.0) > 0
    assert required_payoff_ratio(0.40) == 2.2
    assert passes_expectancy_gate(0.40, 2.2, 1.0)
    assert required_payoff_ratio(0.30) >= 3.0
    assert passes_expectancy_gate(0.30, 3.0, 1.0)
    assert not passes_expectancy_gate(0.70, 0.2, 1.0)


def test_feature_store_is_versioned_and_idempotent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "features.db"))
    get_settings.cache_clear()
    initialize()
    payload = sample_payload()
    assessment = assess_market(payload)
    features = build_feature_snapshots(payload, assessment)
    save_feature_snapshots("20260622", FEATURE_VERSION, features, "2026-06-22T15:10:00+08:00")
    save_feature_snapshots("20260622", FEATURE_VERSION, features, "2026-06-22T15:11:00+08:00")
    shadow = build_shadow_top3(payload, assessment)
    save_shadow_plans("20260622", PLAN_VERSION, shadow["plans"], "2026-06-22T15:11:00+08:00")
    status = feature_store_status()
    assert status == {
        "feature_days": 1,
        "outcome_days": 0,
        "latest_trade_date": "20260622",
        "feature_version": FEATURE_VERSION,
    }
    get_settings.cache_clear()
