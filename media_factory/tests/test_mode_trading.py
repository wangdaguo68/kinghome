import pytest
from mode_trading.parser import TradingParser, MarketData


class TestTradingParser:
    SAMPLE_DATA = """
    大盘指数：
    上证 3300.50 +0.83%
    深证 11050.25 +1.21%
    创业板 2250.30 +2.05%

    技术指标：
    MACD：日线金叉，红柱放大
    KDJ：K值82 D值75 J值96，高位钝化
    布林带：价格突破中轨，上轨压力在3360
    均线：5日线3280、10日线3250、20日线3200，多头排列
    量能：两市成交9877亿，较昨日放量12%

    支撑：3280 (5日线)、3250 (10日线)
    阻力：3360 (布林上轨)、3400 (前高)

    涨跌比：2850:1680
    北向资金：净流入42.5亿
    """

    def test_parse_indices(self):
        data = TradingParser.parse(self.SAMPLE_DATA)
        assert "上证" in data.indices
        assert "+0.83%" in data.indices["上证"]

    def test_parse_macd(self):
        data = TradingParser.parse(self.SAMPLE_DATA)
        assert "金叉" in data.macd_signal

    def test_parse_kdj(self):
        data = TradingParser.parse(self.SAMPLE_DATA)
        assert "钝化" in data.kdj_signal

    def test_parse_support_levels(self):
        data = TradingParser.parse(self.SAMPLE_DATA)
        assert "3280" in data.support_levels
        assert "3250" in data.support_levels

    def test_parse_breadth(self):
        data = TradingParser.parse(self.SAMPLE_DATA)
        assert "2850" in data.breadth or "2850:1680" in data.breadth

    def test_parse_north_flow(self):
        data = TradingParser.parse(self.SAMPLE_DATA)
        assert "42.5" in data.north_flow or "流入" in data.north_flow

    def test_parse_empty_input(self):
        data = TradingParser.parse("")
        assert data.macd_signal == "未检测到"
        assert data.kdj_signal == "未检测到"

    def test_market_data_dataclass(self):
        d = MarketData(raw_text="test", macd_signal="金叉")
        assert d.macd_signal == "金叉"
        assert d.indices == {}
