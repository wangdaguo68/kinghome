from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Any

import httpx


class TushareError(RuntimeError):
    pass


class TushareFallback:
    def __init__(self, token: str, api_url: str, timeout: float = 45.0) -> None:
        self.token = token
        self.api_url = api_url
        self.timeout = timeout
        self._basic_cache: dict[str, dict[str, str]] | None = None
        self._trade_calendar_cache: dict[tuple[str, int], list[str]] = {}

    @property
    def configured(self) -> bool:
        return bool(self.token)

    async def _query(self, api_name: str, params: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
        if not self.configured:
            raise TushareError("Tushare Token 未配置")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.api_url,
                json={"api_name": api_name, "token": self.token, "params": params, "fields": ",".join(fields)},
            )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise TushareError(str(payload.get("msg") or "Tushare 请求失败"))
        data = payload.get("data", {})
        names = data.get("fields", [])
        return [dict(zip(names, values, strict=False)) for values in data.get("items", [])]

    async def latest_trade_date(self) -> str:
        end = date.today()
        start = end - timedelta(days=14)
        rows = await self._query(
            "trade_cal",
            {"exchange": "SSE", "start_date": start.strftime("%Y%m%d"), "end_date": end.strftime("%Y%m%d")},
            ["cal_date", "is_open"],
        )
        dates = [str(row["cal_date"]) for row in rows if int(row.get("is_open", 0)) == 1]
        if not dates:
            raise TushareError("最近两周没有可用交易日")
        return max(dates)

    async def recent_trade_dates(self, end_date: str, count: int = 15) -> list[str]:
        target = end_date.replace("-", "").replace(".", "")
        cache_key = (target, count)
        if cache_key in self._trade_calendar_cache:
            return self._trade_calendar_cache[cache_key]
        target_date = date(int(target[:4]), int(target[4:6]), int(target[6:8]))
        start = target_date - timedelta(days=max(35, count * 3))
        rows = await self._query(
            "trade_cal",
            {"exchange": "SSE", "start_date": start.strftime("%Y%m%d"), "end_date": target},
            ["cal_date", "is_open"],
        )
        dates = sorted(
            {str(row["cal_date"]) for row in rows if int(row.get("is_open", 0)) == 1 and str(row["cal_date"]) <= target},
            reverse=True,
        )[:count]
        if not dates or dates[0] != target:
            raise TushareError(f"{target} 交易日历不可用")
        self._trade_calendar_cache[cache_key] = dates
        return dates

    async def _basic(self) -> dict[str, dict[str, str]]:
        if self._basic_cache is None:
            rows = await self._query("stock_basic", {"exchange": "", "list_status": "L"}, ["ts_code", "name", "list_date"])
            self._basic_cache = {str(row["ts_code"]): row for row in rows}
        return self._basic_cache

    @staticmethod
    def _price_limit(code: str, pre_close: float, direction: str) -> float:
        if code.endswith(".BJ"):
            factor = "1.30" if direction == "up" else "0.70"
        elif code.startswith(("300", "301", "688")):
            factor = "1.20" if direction == "up" else "0.80"
        else:
            factor = "1.10" if direction == "up" else "0.90"
        value = Decimal(str(pre_close)) * Decimal(factor)
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    async def market_snapshot(self, trade_date: str | None = None) -> dict[str, Any]:
        target = (trade_date or await self.latest_trade_date()).replace("-", "").replace(".", "")
        fields = ["ts_code", "trade_date", "high", "close", "pre_close", "pct_chg", "amount"]
        rows = await self._query("daily", {"trade_date": target}, fields)
        if not rows:
            raise TushareError(f"{target} 日线结果为空")

        try:
            basic = await self._basic()
        except (TushareError, httpx.HTTPError):
            basic = {}
        cutoff = (date(int(target[:4]), int(target[4:6]), int(target[6:8])) - timedelta(days=10)).strftime("%Y%m%d")
        for row in rows:
            for field in ("high", "close", "pre_close", "pct_chg", "amount"):
                row[field] = float(row.get(field) or 0)
            info = basic.get(str(row["ts_code"]), {})
            row["name"] = str(info.get("name", ""))
            row["list_date"] = str(info.get("list_date", ""))
        changes = [row["pct_chg"] for row in rows]
        amount_top = sorted(rows, key=lambda row: row["amount"], reverse=True)[:100]
        limit_up = []
        limit_down = []
        failed_limit = []
        for row in rows:
            code = str(row["ts_code"])
            if ("ST" in row["name"].upper() or "退" in row["name"]) or (row["list_date"] and row["list_date"] > cutoff):
                continue
            up_price = self._price_limit(code, row["pre_close"], "up")
            down_price = self._price_limit(code, row["pre_close"], "down")
            if abs(row["close"] - up_price) < 0.001:
                limit_up.append(row)
            elif row["high"] >= up_price - 0.011:
                failed_limit.append(row)
            if abs(row["close"] - down_price) < 0.001:
                limit_down.append(row)

        return {
            "trade_date": target,
            "rows": rows,
            "breadth": {
                "eligible": len(rows),
                "up": sum(value > 0 for value in changes),
                "down": sum(value < 0 for value in changes),
                "flat": sum(value == 0 for value in changes),
                "median": round(float(median(changes)), 4),
                "limit_up": len(limit_up),
                "limit_down": len(limit_down),
                "failed_limit": len(failed_limit),
            },
            "capacity": {
                "sample": len(amount_top),
                "up": sum(row["pct_chg"] > 0 for row in amount_top),
                "down": sum(row["pct_chg"] < 0 for row in amount_top),
                "median": round(float(median(row["pct_chg"] for row in amount_top)), 4),
            },
        }
