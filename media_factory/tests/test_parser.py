from pathlib import Path

import pytest

from zen_trader.exceptions import ParseError
from zen_trader.models import MarketReview
from zen_trader.parser import parse_review


def test_parse_example_review():
    path = Path(__file__).parent.parent / "input" / "example_review.md"
    review = parse_review(path)
    assert isinstance(review, MarketReview)
    assert review.date == "2026-05-09"
    assert "上证指数" in review.market_indices
    assert review.market_indices["上证指数"] == pytest.approx(3312.45)
    assert "MACD" in review.technical_indicators
    assert len(review.key_observations) > 0
    assert len(review.specific_stocks) >= 2
    assert any("中芯国际" in s for s in review.specific_stocks)
    assert review.trader_sentiment in (
        "bullish", "slightly_bullish", "neutral", "slightly_bearish", "bearish"
    )
    assert len(review.raw_text) > 100


def test_parse_missing_file():
    with pytest.raises(ParseError):
        parse_review("/nonexistent/path.md")


def test_parse_empty_file(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("")
    with pytest.raises(ParseError):
        parse_review(empty)
