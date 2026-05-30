from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import date, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.data.schemas import MarketDay, StockBar

TUSHARE_URL = "http://api.tushare.pro"
DAILY_FIELDS = "ts_code,trade_date,open,high,low,close,pre_close,pct_chg,amount"
CACHE_DIR = Path(__file__).resolve().parents[3] / "cache" / "tushare"


class TushareError(RuntimeError):
    pass


def token_available() -> bool:
    return bool(os.getenv("TUSHARE_TOKEN"))


def call_tushare(
    api_name: str,
    params: dict[str, Any] | None = None,
    fields: str = "",
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        raise TushareError("未配置 TUSHARE_TOKEN")

    payload = {"api_name": api_name, "token": token, "params": params or {}, "fields": fields}
    cache_path = _cache_path(api_name, params or {}, fields)
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    attempts = int(os.getenv("TUSHARE_RETRY_ATTEMPTS", "3"))
    result: dict[str, Any] | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            TUSHARE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            if cache_path.exists():
                return json.loads(cache_path.read_text(encoding="utf-8"))
            raise TushareError(f"Tushare {api_name} 网络请求失败：{exc}") from exc
        if result.get("code") == 0:
            break
        message = str(result.get("msg") or "")
        if "频率" not in message and "频次" not in message and "超限" not in message:
            break
        time.sleep(float(os.getenv("TUSHARE_RETRY_SLEEP", "1.4")) * (attempt + 1))

    if (result is None or result.get("code") != 0) and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    if result is None or result.get("code") != 0:
        raise TushareError((result or {}).get("msg") or f"Tushare {api_name} 调用失败")

    data = result["data"]
    if use_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


@lru_cache(maxsize=1)
def latest_trade_date_cached(cache_hour: str) -> date:
    return _latest_trade_date_uncached()


def latest_trade_date() -> date:
    return latest_trade_date_cached(datetime.now().strftime("%Y%m%d%H"))


def _latest_trade_date_uncached() -> date:
    today = date.today()
    try:
        data = call_tushare(
            "trade_cal",
            params={
                "exchange": "SSE",
                "start_date": _format_trade_date(today - timedelta(days=45)),
                "end_date": _format_trade_date(today),
                "is_open": "1",
            },
            fields="cal_date,is_open",
        )
        items = data.get("items") or []
        if items:
            return max(_parse_trade_date(str(item[0])) for item in items)
    except TushareError:
        pass

    data = call_tushare("daily", fields="trade_date", use_cache=False)
    items = data.get("items") or []
    if not items:
        raise TushareError("Tushare 未返回最近交易日")
    return max(_parse_trade_date(str(item[0])) for item in items)


def recent_open_dates(end_date: date, count: int) -> list[date]:
    dates: list[date] = []
    current = end_date
    max_scan_days = max(90, int(count * 1.8) + 30)
    while len(dates) < count and (end_date - current).days < max_scan_days:
        if _daily_rows(current):
            dates.append(current)
        current -= timedelta(days=1)
    return sorted(dates)


@lru_cache(maxsize=64)
def next_open_date(after_date: date) -> date:
    try:
        data = call_tushare(
            "trade_cal",
            params={
                "exchange": "SSE",
                "start_date": _format_trade_date(after_date + timedelta(days=1)),
                "end_date": _format_trade_date(after_date + timedelta(days=15)),
                "is_open": "1",
            },
            fields="cal_date,is_open",
        )
        items = data.get("items") or []
        if items:
            return min(_parse_trade_date(str(item[0])) for item in items)
    except TushareError as exc:
        if "频率" not in str(exc) and "频次" not in str(exc) and "超限" not in str(exc):
            raise
    return _next_weekday(after_date)


def fetch_recent_market_data(count: int = 250) -> tuple[list[MarketDay], list[StockBar]]:
    end_date = latest_trade_date()
    bar_limit = int(os.getenv("TUSHARE_STOCK_BAR_LIMIT", "500"))
    return _fetch_recent_market_data(count, end_date, bar_limit)


@lru_cache(maxsize=8)
def _fetch_recent_market_data(count: int, end_date: date, bar_limit: int) -> tuple[list[MarketDay], list[StockBar]]:
    dates = recent_open_dates(end_date, count)
    if len(dates) < count:
        raise TushareError(f"Tushare 只返回 {len(dates)} 个交易日，少于请求的 {count} 个交易日")

    names = stock_name_map()
    market_days: list[MarketDay] = []
    stock_bars: list[StockBar] = []
    consecutive_limits: dict[str, int] = {}

    for trade_date in dates:
        rows = _daily_rows(trade_date)
        stats_rows = [row for row in rows if _is_market_stat_symbol(str(row["ts_code"]), names.get(str(row["ts_code"]), ""))]
        red_count = sum(1 for row in rows if _float(row["pct_chg"]) > 0)
        turnover_100m = sum(_float(row["amount"]) / 100000 for row in rows)
        limit_up_count = sum(
            1
            for row in stats_rows
            if _is_limit_up_touch(
                symbol=str(row["ts_code"]),
                name=names.get(str(row["ts_code"]), ""),
                pre_close=_float(row["pre_close"]),
                high_price=_float(row["high"]),
            )
        )
        limit_down_count = sum(
            1
            for row in stats_rows
            if _is_limit_down_count(
                symbol=str(row["ts_code"]),
                name=names.get(str(row["ts_code"]), ""),
                pct_chg=_float(row["pct_chg"]),
            )
        )
        market_days.append(
            MarketDay(
                trade_date=trade_date,
                red_count=red_count,
                limit_up_count=limit_up_count,
                limit_down_count=limit_down_count,
                index_return=0,
                turnover_billion=round(turnover_100m, 2),
            )
        )

        eligible_rows = [
            row for row in rows if _is_tradeable_symbol(str(row["ts_code"]), names.get(str(row["ts_code"]), ""))
        ]
        limit_meta: dict[str, tuple[bool, int]] = {}
        for row in eligible_rows:
            symbol = str(row["ts_code"])
            name = names.get(symbol, "")
            limit_up = _is_limit_up(
                symbol=symbol,
                name=name,
                pre_close=_float(row["pre_close"]),
                high_price=_float(row["high"]),
                close_price=_float(row["close"]),
            )
            consecutive = consecutive_limits.get(symbol, 0) + 1 if limit_up else 0
            consecutive_limits[symbol] = consecutive
            limit_meta[symbol] = (limit_up, consecutive)

        ranked = sorted(eligible_rows, key=lambda row: _float(row["amount"]), reverse=True)
        for rank, row in enumerate(ranked[:bar_limit], start=1):
            symbol = str(row["ts_code"])
            pre_close = _float(row["pre_close"])
            open_price = _float(row["open"])
            high_price = _float(row["high"])
            low_price = _float(row["low"])
            close_price = _float(row["close"])
            close_pct = _float(row["pct_chg"])
            amount_100m = _float(row["amount"]) / 100000
            limit_up, consecutive = limit_meta[symbol]

            stock_bars.append(
                StockBar(
                    trade_date=trade_date,
                    symbol=symbol,
                    name=names.get(symbol, symbol),
                    open_price=round(open_price, 3),
                    high_price=round(high_price, 3),
                    low_price=round(low_price, 3),
                    close_price=round(close_price, 3),
                    pre_close=round(pre_close, 3),
                    open_pct=round(_pct(open_price, pre_close), 2),
                    close_pct=round(close_pct, 2),
                    high_pct=round(_pct(high_price, pre_close), 2),
                    low_pct=round(_pct(low_price, pre_close), 2),
                    amount_billion=round(amount_100m, 2),
                    auction_amount_million=0,
                    volume_ratio=0,
                    limit_up=limit_up,
                    first_limit=limit_up and consecutive == 1,
                    consecutive_limits=consecutive,
                    sector_rank=rank,
                )
            )
    return market_days, stock_bars


fetch_recent_market_data.cache_clear = _fetch_recent_market_data.cache_clear  # type: ignore[attr-defined]


@lru_cache(maxsize=1)
def stock_name_map() -> dict[str, str]:
    data = call_tushare(
        "stock_basic",
        params={"exchange": "", "list_status": "L"},
        fields="ts_code,name",
    )
    fields = data.get("fields", [])
    code_index = fields.index("ts_code")
    name_index = fields.index("name")
    return {str(item[code_index]): str(item[name_index]) for item in data.get("items", [])}


@lru_cache(maxsize=512)
def _daily_rows(trade_date: date) -> list[dict[str, Any]]:
    use_cache = trade_date < date.today() - timedelta(days=3)
    data = call_tushare(
        "daily",
        params={"trade_date": _format_trade_date(trade_date)},
        fields=DAILY_FIELDS,
        use_cache=use_cache,
    )
    fields = data["fields"]
    return [dict(zip(fields, item, strict=False)) for item in data.get("items", [])]


def _parse_trade_date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _format_trade_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _next_weekday(value: date) -> date:
    candidate = value + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _pct(price: float, base: float) -> float:
    if base <= 0:
        return 0.0
    return (price / base - 1) * 100


def _is_tradeable_symbol(symbol: str, name: str) -> bool:
    if not _is_non_st_symbol(symbol, name):
        return False
    if symbol.endswith(".SH"):
        return symbol.startswith(("600", "601", "603", "605"))
    if symbol.endswith(".SZ"):
        return symbol.startswith(("000", "001", "002", "003", "300", "301"))
    return False


def _is_non_st_symbol(symbol: str, name: str) -> bool:
    if not name:
        return False
    upper_name = name.upper()
    if "ST" in upper_name or "退" in name:
        return False
    return symbol.endswith((".SH", ".SZ"))


def _is_market_stat_symbol(symbol: str, name: str) -> bool:
    if not _is_non_st_symbol(symbol, name):
        return False
    return "-U" not in name.upper()


def _is_limit_up(symbol: str, name: str, pre_close: float, high_price: float, close_price: float) -> bool:
    if pre_close <= 0 or not _is_non_st_symbol(symbol, name):
        return False
    ratio = 1.20 if symbol.startswith(("300", "301", "688")) else 1.10
    limit_price = round(pre_close * ratio + 1e-8, 2)
    return high_price >= limit_price and close_price >= limit_price


def _is_limit_down(symbol: str, name: str, pre_close: float, low_price: float, close_price: float) -> bool:
    if pre_close <= 0 or not _is_non_st_symbol(symbol, name):
        return False
    ratio = 0.80 if symbol.startswith(("300", "301", "688")) else 0.90
    limit_price = round(pre_close * ratio + 1e-8, 2)
    return low_price <= limit_price and close_price <= limit_price


def _is_limit_up_touch(symbol: str, name: str, pre_close: float, high_price: float) -> bool:
    if pre_close <= 0 or not _is_market_stat_symbol(symbol, name):
        return False
    ratio = 1.20 if symbol.startswith(("300", "301", "688")) else 1.30 if symbol.startswith(("8", "4", "9")) else 1.10
    limit_price = round(pre_close * ratio + 1e-8, 2)
    return high_price >= limit_price


def _is_limit_down_count(symbol: str, name: str, pct_chg: float) -> bool:
    if not _is_market_stat_symbol(symbol, name):
        return False
    threshold = -19.5 if symbol.startswith(("300", "301", "688")) else -29.5 if symbol.startswith(("8", "4", "9")) else -9.5
    return pct_chg <= threshold


def _cache_path(api_name: str, params: dict[str, Any], fields: str) -> Path:
    key = json.dumps(
        {"api_name": api_name, "params": params, "fields": fields},
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / api_name / f"{digest}.json"
