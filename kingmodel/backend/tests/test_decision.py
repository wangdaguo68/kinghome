from app.engine.decision import MarketInputs, classify_cycle, position_limit, score_market


def test_high_dispersion_market() -> None:
    scores = score_market(
        MarketInputs(
            up_ratio=34.56,
            median_change=-0.83,
            limit_up=82,
            limit_down=12,
            failed_limit=40,
            continuation_rate=12.5,
            trend_strength=72,
            speculation_strength=61,
        )
    )
    assert scores["loss"] > scores["money"]
    assert classify_cycle({**scores, "money": 61, "loss": 68}) == "高波动分歧"
    assert position_limit("高波动分歧", 68) == 40


def test_risk_gate_caps_position() -> None:
    assert position_limit("主升", 80) == 20
