from app.ml.modeling import LogisticModel, classification_metrics, evaluation_metrics, purged_walk_forward_dates
from app.ml.outcome_tracker import calculate_outcomes
from app.ml.training_pipeline import TrainingPipeline, classification_promotion_eligible, promotion_eligible


def feature_row(score: float, loss: float) -> dict[str, float]:
    return {
        "core_score": score, "change": score / 10, "money": score, "loss": loss,
        "trend": score, "speculation": 50, "ladder_height": score / 20, "recent_limit_count": score / 25,
    }


def test_logistic_model_trains_serializes_and_explains() -> None:
    rows = [feature_row(30 + index * 2, 80 - index * 2) for index in range(30)]
    labels = [0] * 15 + [1] * 15
    model = LogisticModel.fit(rows, labels)
    assert model.predict(rows[-1]) > model.predict(rows[0])
    restored = LogisticModel.from_dict(model.to_dict())
    assert abs(restored.predict(rows[-1]) - model.predict(rows[-1])) < 1e-9
    assert len(model.explain(rows[-1])) == 3


def test_walk_forward_has_ten_day_purge() -> None:
    dates = [f"202601{day:02d}" for day in range(1, 32)] + [f"202602{day:02d}" for day in range(1, 29)]
    train, test = purged_walk_forward_dates(dates, purge_days=10)
    ordered = sorted(set(dates))
    assert max(ordered.index(day) for day in train) + 10 < min(ordered.index(day) for day in test)
    assert train.isdisjoint(test)


def test_outcome_labels_start_at_next_open_and_cover_all_horizons() -> None:
    bars = [
        {"trade_date": f"202606{day:02d}", "open": 10.0, "close": 10 + day / 10, "high": 10.5 + day / 10,
         "low": 9.8, "volume": 1000, "pre_close": 9.9}
        for day in range(2, 12)
    ]
    outcomes = calculate_outcomes("600001", bars)
    assert [horizon for horizon, _ in outcomes] == [1, 3, 5, 10]
    assert outcomes[0][1]["entry_trade_date"] == "20260602"
    assert outcomes[-1][1]["exit_trade_date"] == "20260611"
    assert outcomes[-1][1]["net_return"] < outcomes[-1][1]["gross_return"]


def test_one_price_limit_is_not_counted_as_tradable_success() -> None:
    bars = [{"trade_date": "20260623", "open": 11.0, "close": 11.0, "high": 11.0, "low": 11.0, "volume": 1000, "pre_close": 10.0}]
    outcome = calculate_outcomes("600001", bars)[0][1]
    assert outcome["tradable"] is False
    assert outcome["net_return"] == 0


def test_model_promotion_waits_for_120_days_and_all_risk_gates() -> None:
    metrics = {"samples": 40.0, "win_rate": 0.4, "avg_win": 0.025, "avg_loss": 0.01, "payoff_ratio": 2.5,
               "expectancy": 0.004, "brier": 0.22, "max_drawdown": -0.12}
    assert not promotion_eligible(metrics, None, 119)
    assert promotion_eligible(metrics, None, 120)
    assert not promotion_eligible({**metrics, "brier": 0.3}, None, 120)
    assert not promotion_eligible({**metrics, "max_drawdown": -0.25}, None, 120)


def test_evaluation_reports_payoff_expectancy_calibration_and_drawdown() -> None:
    metrics = evaluation_metrics([0.8, 0.7, 0.2, 0.3], [
        {"net_return": 0.04}, {"net_return": 0.02}, {"net_return": -0.01}, {"net_return": -0.015},
    ])
    assert metrics["expectancy"] > 0
    assert metrics["payoff_ratio"] > 1.8
    assert 0 <= metrics["brier"] <= 1
    assert metrics["max_drawdown"] < 0


def test_market_and_sector_classification_gate_is_calibrated_and_time_gated() -> None:
    metrics = classification_metrics([0.8, 0.7, 0.2, 0.3] * 5, [1, 1, 0, 0] * 5)
    assert metrics["accuracy"] == 1
    assert not classification_promotion_eligible(metrics, None, 119)
    assert classification_promotion_eligible(metrics, None, 120)


def test_training_pipeline_creates_shadow_challengers_without_early_promotion(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "training.db"))
    get_settings.cache_clear()
    initialize()
    cycles = ["主升", "高位震荡", "混沌轮动", "退潮防守", "试错修复"]
    for index in range(60):
        trade_date = f"2026{index // 28 + 1:02d}{index % 28 + 1:02d}"
        strong = index % 2 == 0
        market = {
            "money": 75 if strong else 35, "loss": 25 if strong else 70,
            "trend": 72 if strong else 42, "speculation": 40 if strong else 75,
            "style": "趋势风格" if strong else "投机连板风格", "cycle": cycles[index % len(cycles)],
            "inputs": {"up_ratio": 65 if strong else 35, "median": 1 if strong else -1, "limit_up": 80,
                       "limit_down": 5, "ladder_count": 12, "max_height": 5},
        }
        sector = {"name": "算力", "score": 75 if strong else 50, "change": 3 if strong else -1, "tags": ["主线"], "role": "主线"}
        save_feature_snapshots(trade_date, "rule-v1", [("market", "ALL", market), ("sector", "算力", sector)], "2026-06-22T15:10:00+08:00")
    result = TrainingPipeline().train("integration-v1")
    assert result["status"] == "completed"
    status = model_system_status()
    assert status["stage"] == "rule_only"
    assert any(model["role"] == "challenger" for model in status["models"])
    assert not any(model["role"] == "champion" for model in status["models"])
    get_settings.cache_clear()
from app.config import get_settings
from app.db import initialize, model_system_status, save_feature_snapshots
