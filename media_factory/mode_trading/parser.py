import re
from dataclasses import dataclass, field


@dataclass
class MarketData:
    raw_text: str = ""
    indices: dict[str, str] = field(default_factory=dict)
    macd_signal: str = ""
    kdj_signal: str = ""
    bollinger_signal: str = ""
    ma_signal: str = ""
    volume_signal: str = ""
    support_levels: str = ""
    resistance_levels: str = ""
    breadth: str = ""
    north_flow: str = ""
    key_signal: str = ""
    market_summary: str = ""


class TradingParser:

    @classmethod
    def parse(cls, raw_text: str) -> MarketData:
        data = MarketData(raw_text=raw_text)
        data.market_summary = raw_text[:500]

        cls._extract_indices(data, raw_text)
        cls._extract_indicators(data, raw_text)
        cls._extract_levels(data, raw_text)
        cls._extract_sentiment(data, raw_text)
        cls._extract_key_signal(data, raw_text)

        return data

    @classmethod
    def _extract_indices(cls, data: MarketData, text: str):
        for m in re.finditer(r"(上证|深证|创业板|科创\s*50|沪深\s*300)\s*(\d+\.?\d*)\s*([+-]\d+\.?\d*%)", text):
            data.indices[m.group(1)] = f"{m.group(2)} {m.group(3)}"

    @classmethod
    def _extract_indicators(cls, data: MarketData, text: str):
        patterns = {
            "macd": r"MACD[：:]\s*(.+?)(?:\n|$)",
            "kdj": r"KDJ[：:]\s*(.+?)(?:\n|$)",
            "bollinger": r"布林(?:带)?[：:]\s*(.+?)(?:\n|$)",
            "ma": r"均线[：:]\s*(.+?)(?:\n|$)",
            "volume": r"量能[：:]\s*(.+?)(?:\n|$)",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
            else:
                val = cls._guess_indicator(key, text)
            setattr(data, f"{key}_signal", val)

    @classmethod
    def _guess_indicator(cls, key: str, text: str) -> str:
        keywords = {
            "macd": r"(MACD\s*(金叉|死叉|顶背离|底背离|多头|空头))",
            "kdj": r"(KDJ\s*(金叉|死叉|超买|超卖|钝化|高位|低位))",
            "bollinger": r"(布林(?:带)?\s*(开口|收口|上轨|下轨|中轨|突破))",
            "ma": r"((?:5|10|20|30|60|120|250)日(?:均线).*?(?:突破|跌破|支撑|压制|多头|空头))",
            "volume": r"((?:放量|缩量|地量|天量|量能).*?(?:上涨|下跌|突破|萎缩|放大))",
        }
        pattern = keywords.get(key)
        if pattern:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return "未检测到"

    @classmethod
    def _extract_levels(cls, data: MarketData, text: str):
        data.support_levels = ", ".join(cls._find_levels(text, "支撑"))
        data.resistance_levels = ", ".join(cls._find_levels(text, "阻力"))
        if not data.support_levels:
            data.support_levels = "未明确"
        if not data.resistance_levels:
            data.resistance_levels = "未明确"

    @staticmethod
    def _find_levels(text: str, label: str) -> list[str]:
        m = re.search(rf"{label}(?:位)?[：:]\s*(.+)", text)
        if not m:
            return []
        return re.findall(r"(\d{3,5}\.?\d*)", m.group(1))

    @classmethod
    def _extract_sentiment(cls, data: MarketData, text: str):
        breadth_m = re.search(r"涨跌比[：:]?\s*(\d+\s*[:：]\s*\d+)", text)
        data.breadth = breadth_m.group(1) if breadth_m else "未检测到"

        north_m = re.search(r"北向(?:资金)?[：:]?\s*(.+(?:流入|流出|净买入|净卖出)\s*\d+\.?\d*\s*亿)", text)
        data.north_flow = north_m.group(1) if north_m else "未检测到"

    @classmethod
    def _extract_key_signal(cls, data: MarketData, text: str):
        signals = []
        for indicator in ["macd", "kdj", "bollinger", "ma", "volume"]:
            val = getattr(data, f"{indicator}_signal", "")
            if val and val != "未检测到":
                signals.append(f"{indicator.upper()}: {val}")
        data.key_signal = "；".join(signals[:3]) if signals else "今日未检测到明确技术信号"
