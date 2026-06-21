from app.engine.universe import is_tradable


def test_universe_filter() -> None:
    assert is_tradable({"code": "300001", "name": "示例股份", "listing_days": 100})
    assert not is_tradable({"code": "688001", "name": "科创样本", "listing_days": 100})
    assert not is_tradable({"code": "600001", "name": "ST样本", "listing_days": 100})
    assert not is_tradable({"code": "600001", "name": "次新样本", "listing_days": 20})
