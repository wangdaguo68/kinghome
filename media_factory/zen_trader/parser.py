import re
from pathlib import Path

from zen_trader.exceptions import ParseError
from zen_trader.models import MarketReview


def parse_review(filepath: str | Path) -> MarketReview:
    filepath = Path(filepath)
    if not filepath.exists():
        raise ParseError(f"File not found: {filepath}")
    try:
        raw_text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        raise ParseError(f"Cannot read file {filepath}: {e}")

    if not raw_text.strip():
        raise ParseError(f"File is empty: {filepath}")

    return MarketReview(
        source_file=str(filepath),
        date=_extract_date(raw_text),
        market_indices=_extract_indices(raw_text),
        technical_indicators=_extract_technical_indicators(raw_text),
        volume_data=_extract_volume_data(raw_text),
        key_observations=_extract_observations(raw_text),
        trader_sentiment=_classify_sentiment(raw_text),
        specific_stocks=_extract_stocks(raw_text),
        raw_text=raw_text,
    )


def _extract_section(text: str, *headings: str) -> str:
    pattern = "|".join(re.escape(h) for h in headings)
    m = re.search(rf"^#{{1,3}}\s*({pattern})\s*$(.*?)(?=^#{{1,3}}\s|\Z)",
                  text, re.MULTILINE | re.DOTALL)
    return m.group(2).strip() if m else ""


def _extract_date(text: str) -> str | None:
    m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", text)
    if m:
        return m.group(1)
    section = _extract_section(text, "日期", "交易日期", "Date")
    if section:
        return section.strip().split("\n")[0].strip()
    return None


def _extract_indices(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    section = _extract_section(text, "大盘指数", "指数", "盘面数据", "市场概况", "Indices")
    for line in section.split("\n") if section else []:
        m = re.search(
            r"(沪深300|中证[5５]00|科创[5５]0|上证[5５]0|上证指数|上证|深证成指|深证|创业板|恒生|A50)\D*([\d,.]+)",
            line,
        )
        if m:
            name = m.group(1).strip()
            try:
                val = float(m.group(2).replace(",", ""))
                result[name] = val
            except ValueError:
                pass
    return result


def _extract_technical_indicators(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    section = _extract_section(text, "技术指标", "技术面", "技术分析", "Technical")
    if not section:
        return result
    for line in section.split("\n"):
        line = line.strip()
        m = re.match(r"[-*•]\s*(.+?)[：:]\s*(.+)", line)
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result


def _extract_volume_data(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    section = _extract_section(text, "成交量", "量能", "成交", "Volume")
    if not section:
        return result
    for line in section.split("\n"):
        line = line.strip()
        m = re.match(r"[-*•]\s*(.+?)[：:]\s*(.+)", line)
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result


def _extract_observations(text: str) -> list[str]:
    section = _extract_section(text, "关键观察", "盘面特征", "复盘笔记", "Observations")
    observations: list[str] = []
    if not section:
        return observations
    for line in section.split("\n"):
        line = line.strip()
        if re.match(r"^[-*•\d]+[、.)]", line):
            observations.append(re.sub(r"^[-*•\d]+[、.)]\s*", "", line).strip())
        elif line and not line.startswith("#"):
            observations.append(line)
    return observations


def _extract_stocks(text: str) -> list[str]:
    section = _extract_section(text, "个股", "关注股票", "持仓", "Stocks")
    stocks: list[str] = []
    if not section:
        return stocks
    for line in section.split("\n"):
        line = line.strip()
        m = re.match(r"[-*•\d]+\s*(.+)", line)
        if m:
            stocks.append(m.group(1).strip())
    return stocks


def _classify_sentiment(text: str) -> str:
    bullish = len(re.findall(r"(看多|做多|突破|放量上涨|牛市|反弹|大涨)", text))
    bearish = len(re.findall(r"(看空|做空|破位|缩量下跌|熊市|暴跌|恐慌)", text))
    if bullish > bearish * 2:
        return "bullish"
    if bearish > bullish * 2:
        return "bearish"
    if bullish > bearish:
        return "slightly_bullish"
    if bearish > bullish:
        return "slightly_bearish"
    return "neutral"
