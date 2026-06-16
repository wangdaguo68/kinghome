from app.safety import has_safety_risk


def test_safety_risk_detects_self_harm_words() -> None:
    assert has_safety_risk("我真的不想活了")
    assert has_safety_risk("感觉活不下去")


def test_safety_risk_ignores_normal_low_mood() -> None:
    assert not has_safety_risk("今天很累，也有点委屈")

