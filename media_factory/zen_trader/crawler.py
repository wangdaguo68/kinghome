import os
import time
from datetime import date as date_type
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests

from zen_trader.exceptions import CrawlerError
from zen_trader.models import CrawlerData

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://quote.eastmoney.com/",
}

# 绕过系统代理
_HTTP_SESSION = requests.Session()
_HTTP_SESSION.trust_env = False
_HTTP_SESSION.headers.update(HEADERS)


# ============================================================
# 技术指标计算 (numpy)
# ============================================================

def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    result = np.zeros_like(arr)
    result[0] = arr[0]
    multiplier = 2.0 / (period + 1)
    for i in range(1, len(arr)):
        result[i] = (arr[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def calc_macd(close: np.ndarray, fast=12, slow=26, signal=9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    macd_bar = 2 * (dif - dea)
    return dif, dea, macd_bar


def calc_kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray, period=9):
    n = len(close)
    if n < period:
        return 50.0, 50.0, 50.0
    k_vals = np.zeros(n)
    d_vals = np.zeros(n)
    for i in range(period - 1, n):
        hh = high[i - period + 1:i + 1].max()
        ll = low[i - period + 1:i + 1].min()
        rsv = ((close[i] - ll) / (hh - ll)) * 100 if hh != ll else 50.0
        if i == period - 1:
            k_vals[i] = (2.0 / 3) * 50 + (1.0 / 3) * rsv
            d_vals[i] = (2.0 / 3) * 50 + (1.0 / 3) * k_vals[i]
        else:
            k_vals[i] = (2.0 / 3) * k_vals[i - 1] + (1.0 / 3) * rsv
            d_vals[i] = (2.0 / 3) * d_vals[i - 1] + (1.0 / 3) * k_vals[i]
    j = 3 * k_vals[-1] - 2 * d_vals[-1]
    return round(float(k_vals[-1]), 1), round(float(d_vals[-1]), 1), round(float(j), 1)


def calc_rsi(close: np.ndarray, period=14):
    n = len(close)
    if n < period + 1:
        return 50.0
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = gains[-period:].mean()
    avg_loss = losses[-period:].mean()
    if avg_loss == 0:
        return 100.0
    return round(float(100 - 100 / (1 + avg_gain / avg_loss)), 1)


def calc_bollinger(close: np.ndarray, period=20, std_mult=2):
    if len(close) < period:
        period = len(close)
    ma = close[-period:].mean()
    std = close[-period:].std()
    upper = float(ma + std_mult * std)
    lower = float(ma - std_mult * std)
    bandwidth = float((upper - lower) / ma * 100)
    return round(upper, 2), round(float(ma), 2), round(lower, 2), round(bandwidth, 2)


def calc_ma(close: np.ndarray, periods=(5, 10, 20, 60)):
    result = {}
    for p in periods:
        if len(close) >= p:
            result[f"MA{p}"] = round(float(close[-p:].mean()), 2)
        else:
            result[f"MA{p}"] = None
    return result


# ============================================================
# K线数据 — akshare 为主
# ============================================================

def fetch_index_kline(symbol: str = "sh000001", days: int = 120) -> dict:
    last_err = None
    for attempt in range(3):
        try:
            old_env = {}
            for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                old_env[k] = os.environ.pop(k, None)
            try:
                import akshare as ak
                df = ak.stock_zh_index_daily(symbol=symbol)
            finally:
                for k, v in old_env.items():
                    if v is not None:
                        os.environ[k] = v

            if df is not None and not df.empty:
                df = df.tail(days)
                volumes = df["volume"].astype(float).to_numpy()
                # 新浪源 volume 是股数，转成手；没有 amount 字段，用 close * volume 估算
                return {
                    "dates": df["date"].astype(str).tolist(),
                    "open": df["open"].astype(float).to_numpy(),
                    "close": df["close"].astype(float).to_numpy(),
                    "high": df["high"].astype(float).to_numpy(),
                    "low": df["low"].astype(float).to_numpy(),
                    "volume": volumes,
                    "turnover": df["close"].astype(float).to_numpy() * volumes,
                }
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2)

    raise CrawlerError(f"获取K线失败 ({symbol}): {last_err}")


# ============================================================
# 实时行情 — 东方财富 API
# ============================================================

def _fetch_json(url: str, timeout=15) -> dict:
    resp = _HTTP_SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_index_spot() -> dict:
    codes = ["1.000001", "0.399001", "0.399006", "1.000688", "0.000300"]
    code_str = ",".join(codes)
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        "?fltt=2&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18"
        f"&secids={code_str}"
    )
    data = _fetch_json(url)
    result = {}
    name_map = {"1.000001": "上证指数", "0.399001": "深证成指",
                 "0.399006": "创业板指", "1.000688": "科创50", "0.000300": "沪深300"}
    if data.get("data") and data["data"].get("diff"):
        for item in data["data"]["diff"]:
            name = name_map.get(item.get("f12", ""), item.get("f14", ""))
            result[name] = {
                "price": item.get("f2", "-"),
                "change_pct": item.get("f3", 0),
                "change_amount": item.get("f4", 0),
                "volume": item.get("f5", 0),
                "turnover": item.get("f6", 0),
                "high": item.get("f15", "-"),
                "low": item.get("f16", "-"),
                "open": item.get("f17", "-"),
                "prev_close": item.get("f18", "-"),
                "amplitude": item.get("f7", 0),
            }
    return result


def fetch_market_breadth() -> dict:
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get"
        "?pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3"
        "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        "&fields=f2,f3,f12,f14"
    )
    try:
        data = _fetch_json(url)
        result = {"up": 0, "down": 0, "flat": 0}
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                chg = item.get("f3", 0)
                if chg > 0:
                    result["up"] += 1
                elif chg < 0:
                    result["down"] += 1
                else:
                    result["flat"] += 1
        return result
    except requests.RequestException:
        return {"up": 0, "down": 0, "flat": 0}


def fetch_north_bound() -> dict:
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/kamt.kline/get"
            "?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54"
            "&klt=101&lmt=5"
        )
        data = _fetch_json(url)
        result = {"today_net": "--", "recent_days": []}
        if data.get("data") and data["data"].get("klines"):
            for line in data["data"]["klines"]:
                parts = line.split(",")
                if len(parts) >= 3:
                    result["recent_days"].append({
                        "date": parts[0],
                        "net_flow": float(parts[2]) if parts[2] != "-" else 0,
                    })
            if result["recent_days"]:
                last = result["recent_days"][-1]
                amt = abs(last["net_flow"])
                direction = "净流入" if last["net_flow"] > 0 else "净流出"
                result["today_net"] = f"{direction} {_fmt_amt(amt)}"
        return result
    except requests.RequestException:
        return {"today_net": "数据获取失败", "recent_days": []}


def fetch_limit_data() -> dict:
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get"
            "?pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3"
            "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
            "&fields=f2,f3,f8,f10,f12,f14"
        )
        data = _fetch_json(url)
        result = {"limit_up": 0, "limit_down": 0, "top_stocks": []}
        if data.get("data") and data["data"].get("diff"):
            items = data["data"]["diff"]
            for item in items:
                chg = item.get("f3", 0)
                if chg >= 9.9:
                    result["limit_up"] += 1
                elif chg <= -9.9:
                    result["limit_down"] += 1
            top = sorted(items, key=lambda x: x.get("f3", 0), reverse=True)[:3]
            for item in top:
                name = _anonymize_stock(item.get("f14", ""))
                result["top_stocks"].append(
                    f"{name}({item.get('f12', '')}) {item.get('f3', 0):.2f}%"
                )
        return result
    except requests.RequestException:
        return {"limit_up": 0, "limit_down": 0, "top_stocks": []}


# ============================================================
# 工具函数
# ============================================================

def _fmt_amt(amount: float) -> str:
    if abs(amount) >= 1e12:
        return f"{amount / 1e12:.2f}万亿"
    if abs(amount) >= 1e8:
        return f"{amount / 1e8:.2f}亿"
    if abs(amount) >= 1e4:
        return f"{amount / 1e4:.2f}万"
    return f"{amount:.0f}"


def _anonymize_stock(name: str) -> str:
    if not name:
        return name
    if len(name) == 3:
        return "某" + name[1:]
    if len(name) >= 4:
        return name[:2] + "某" + name[3:]
    return name


def _diag_macd(dif, dea, bar):
    ld, le, lb = float(dif[-1]), float(dea[-1]), float(bar[-1])
    diag = "金叉多头" if ld > le and lb > 0 else ("死叉空头" if ld < le and lb < 0 else "震荡")
    if len(dif) >= 3:
        if dif[-1] > dif[-2] and dif[-2] < dif[-3]:
            diag += "，DIF拐头向上"
        elif dif[-1] < dif[-2] and dif[-2] > dif[-3]:
            diag += "，DIF拐头向下"
    if len(bar) >= 3 and abs(bar[-3]) > 0.001:
        if abs(bar[-1]) > abs(bar[-2]) > abs(bar[-3]):
            diag += "，动能增强"
        elif abs(bar[-1]) < abs(bar[-2]) < abs(bar[-3]):
            diag += "，动能衰减"
    return diag


def _diag_kdj(k, d, j):
    j = float(j)
    if j > 100:
        return f"K={k} D={d} J={j:.0f} — 严重超买"
    if j < 0:
        return f"K={k} D={d} J={j:.0f} — 严重超卖"
    if k > 80 and d > 80:
        return f"K={k} D={d} J={j:.0f} — 高位钝化"
    if k < 20 and d < 20:
        return f"K={k} D={d} J={j:.0f} — 低位钝化"
    if k > d:
        return f"K={k} D={d} J={j:.0f} — 多头向上"
    return f"K={k} D={d} J={j:.0f} — 空头向下"


def _diag_rsi(rsi):
    if rsi > 80:
        return f"{rsi} — 严重超买"
    if rsi > 70:
        return f"{rsi} — 超买区"
    if rsi < 20:
        return f"{rsi} — 严重超卖"
    if rsi < 30:
        return f"{rsi} — 超卖区"
    return f"{rsi} — 中性区"


def _diag_bb(close, upper, mid, lower):
    last = float(close[-1])
    if last > upper:
        return f"价格{last:.2f}突破上轨{upper:.2f}"
    if last < lower:
        return f"价格{last:.2f}跌破下轨{lower:.2f}"
    pos = (last - lower) / (upper - lower) * 100 if upper != lower else 50
    return f"价格{last:.2f}通道内(偏上{pos:.0f}%)"


def _diag_ma(close, mas):
    last = float(close[-1])
    above = sum(1 for v in mas.values() if v is not None and last > v)
    total = sum(1 for v in mas.values() if v is not None)
    if total == 0:
        return "数据不足"
    if above == total:
        return "多头排列"
    if above == 0:
        return "空头排列"
    return f"均线交织(站上{above}/{total}条)"


# ============================================================
# 主入口
# ============================================================

def fetch_market_data() -> CrawlerData:
    indices = fetch_index_spot()
    kline = fetch_index_kline("sh000001", days=120)
    close = kline["close"]
    high = kline["high"]
    low = kline["low"]

    dif, dea, bar = calc_macd(close)
    k_val, d_val, j_val = calc_kdj(high, low, close)
    rsi = calc_rsi(close)
    upper, mid, lower, bw = calc_bollinger(close)
    mas = calc_ma(close)

    breadth = fetch_market_breadth()
    north = fetch_north_bound()
    limits = fetch_limit_data()

    up = breadth.get("up", 0)
    down = breadth.get("down", 0)
    if up + down == 0:
        sentiment = "neutral"
    else:
        ratio = up / max(down, 1)
        if ratio > 4:
            sentiment = "bullish"
        elif ratio > 1.5:
            sentiment = "slightly_bullish"
        elif ratio < 0.25:
            sentiment = "bearish"
        elif ratio < 0.67:
            sentiment = "slightly_bearish"
        else:
            sentiment = "neutral"

    summary_parts = []
    for name, info in indices.items():
        chg = info.get("change_pct", 0)
        arrow = "↑" if chg > 0 else ("↓" if chg < 0 else "→")
        summary_parts.append(
            f"{name}: {info['price']} {arrow}{chg:+.2f}%  "
            f"成交额{_fmt_amt(info.get('turnover', 0))}"
        )
    summary_parts.append(f"涨跌比 {up}:{down}")
    summary_parts.append(f"涨停 {limits['limit_up']} 家 / 跌停 {limits['limit_down']} 家")
    if limits["top_stocks"]:
        summary_parts.append(f"涨幅前三: {', '.join(limits['top_stocks'])}")
    summary_parts.append(f"北向资金: {north['today_net']}")

    tech = {
        "macd": {
            "dif": round(float(dif[-1]), 4),
            "dea": round(float(dea[-1]), 4),
            "bar": round(float(bar[-1]), 4),
            "diagnosis": _diag_macd(dif, dea, bar),
        },
        "kdj": {
            "k": k_val, "d": d_val, "j": j_val,
            "diagnosis": _diag_kdj(k_val, d_val, j_val),
        },
        "rsi": {"value": rsi, "diagnosis": _diag_rsi(rsi)},
        "bollinger": {
            "upper": upper, "mid": mid, "lower": lower,
            "bandwidth": bw,
            "diagnosis": _diag_bb(close, upper, mid, lower),
        },
        "ma": {
            "values": [f"{k}={v:.2f}" for k, v in mas.items() if v is not None],
            "diagnosis": _diag_ma(close, mas),
        },
    }

    return CrawlerData(
        date=date_type.today().isoformat(),
        limit_up_count=limits["limit_up"],
        limit_down_count=limits["limit_down"],
        advance_decline_ratio=f"{up}:{down}",
        total_volume_yuan=_fmt_amt(float(kline["turnover"][-1])) if len(kline["turnover"]) > 0 else "--",
        north_bound_flow_yuan=north["today_net"],
        market_sentiment=sentiment,
        raw_summary="\n".join(summary_parts),
        technical_indicators=tech,
        index_spot=indices,
    )


def crawler_to_markdown(data: CrawlerData) -> str:
    tech = data.technical_indicators
    lines = [
        "# A股市场深度复盘\n",
        f"## 日期\n{data.date}\n",
        "## 指数行情",
    ]
    for name, info in data.index_spot.items():
        chg = info.get("change_pct", 0)
        arrow = "↑" if chg > 0 else ("↓" if chg < 0 else "→")
        lines.append(
            f"- {name}: {info['price']} {arrow}{chg:+.2f}%  "
            f"开 {info.get('open', '-')} 高 {info.get('high', '-')} 低 {info.get('low', '-')}"
        )

    lines += [
        "",
        "## 技术指标（上证指数日K线计算）",
        "",
        f"### MACD (12,26,9)",
        f"- DIF: {tech.get('macd', {}).get('dif', '-')}",
        f"- DEA: {tech.get('macd', {}).get('dea', '-')}",
        f"- MACD柱: {tech.get('macd', {}).get('bar', '-')}",
        f"- 研判: {tech.get('macd', {}).get('diagnosis', '-')}",
        "",
        f"### KDJ (9,3,3)",
        f"- 研判: {tech.get('kdj', {}).get('diagnosis', '-')}",
        "",
        f"### RSI (14)",
        f"- 研判: {tech.get('rsi', {}).get('diagnosis', '-')}",
        "",
        f"### 布林带 (20,2)",
        f"- 上轨: {tech.get('bollinger', {}).get('upper', '-')}",
        f"- 中轨: {tech.get('bollinger', {}).get('mid', '-')}",
        f"- 下轨: {tech.get('bollinger', {}).get('lower', '-')}",
        f"- 研判: {tech.get('bollinger', {}).get('diagnosis', '-')}",
        "",
        f"### 均线系统",
        f"- {' | '.join(tech.get('ma', {}).get('values', []))}",
        f"- 研判: {tech.get('ma', {}).get('diagnosis', '-')}",
        "",
        "## 市场宽度",
        f"- 涨跌比: {data.advance_decline_ratio}",
        f"- 涨停 {data.limit_up_count} 家 / 跌停 {data.limit_down_count} 家",
        f"- 北向资金: {data.north_bound_flow_yuan}",
        f"- 市场情绪: {data.market_sentiment}",
        "",
        "## 盘面特征",
        data.raw_summary,
        "",
        f"> 本报告由 Zen Trader 爬虫自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return "\n".join(lines)


def save_crawler_output(data: CrawlerData, output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"auto_fetch_{data.date}.md"
    filepath = output_dir / filename
    filepath.write_text(crawler_to_markdown(data), encoding="utf-8")
    return filepath
