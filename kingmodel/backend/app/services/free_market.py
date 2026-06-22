from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class FreeMarketError(RuntimeError):
    pass


class EastMoneyFreeClient:
    POOL_URL = "https://push2ex.eastmoney.com/getTopicZTPool"
    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    async def _get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, headers=self.HEADERS, follow_redirects=True) as client:
                    response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise FreeMarketError("免费接口返回值不是对象")
                return payload
            except (httpx.HTTPError, ValueError, FreeMarketError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.8 * (attempt + 1))
        raise FreeMarketError(f"免费接口连续失败：{last_error}") from last_error

    async def trade_dates(self, count: int = 10) -> list[str]:
        params = {
            "secid": "1.000001", "klt": "101", "fqt": "0", "lmt": str(max(20, count * 2)),
            "end": "20500101", "iscca": "1", "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        payload = await self._get_json(self.KLINE_URL, params)
        klines = (payload.get("data") or {}).get("klines") or []
        dates = [str(item).split(",", 1)[0].replace("-", "") for item in klines]
        dates = [item for item in dates if len(item) == 8 and item.isdigit()]
        if len(dates) < min(5, count):
            raise FreeMarketError("东方财富指数交易日数据不完整")
        return dates[-count:][::-1]

    async def limit_up_pool(self, trade_date: str) -> list[dict[str, Any]]:
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989", "dpt": "wz.ztzt", "Pageindex": "0",
            "pagesize": "10000", "sort": "fbt:asc", "date": trade_date,
        }
        payload = await self._get_json(self.POOL_URL, params)
        raw_rows = (payload.get("data") or {}).get("pool")
        if raw_rows is None and payload.get("data") is None:
            return []
        if not isinstance(raw_rows, list):
            raise FreeMarketError(f"{trade_date} 东方财富涨停池结构异常")
        return [
            {
                "code": str(row.get("c", "")),
                "name": str(row.get("n", "")),
                "change": float(row.get("zdp") or 0),
                "amount": float(row.get("amount") or 0),
                "turnover": float(row.get("hs") or 0),
                "first_limit_time": str(row.get("fbt") or ""),
                "last_limit_time": str(row.get("lbt") or ""),
                "failed_count": int(row.get("zbc") or 0),
                "industry": str(row.get("hybk") or "市场热点"),
                "vendor_ladder": int(row.get("lbc") or 1),
            }
            for row in raw_rows
            if str(row.get("c", "")).isdigit()
        ]

    async def recent_pools(self, count: int = 6) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
        pools: dict[str, list[dict[str, Any]]] = {}
        selected: list[str] = []
        today = datetime.now(timezone(timedelta(hours=8))).date()
        for offset in range(21):
            trade_date = (today - timedelta(days=offset)).strftime("%Y%m%d")
            result = await self.limit_up_pool(trade_date)
            if not result:
                continue
            selected.append(trade_date)
            pools[trade_date] = result
            if len(selected) >= count:
                break
            await asyncio.sleep(0.2)
        if len(selected) < count:
            raise FreeMarketError(f"最近21日仅取得{len(selected)}个有效涨停池")
        return selected, pools

    async def stock_bars(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        market = "1" if code.startswith(("5", "6", "9")) else "0"
        payload = await self._get_json(self.KLINE_URL, {
            "secid": f"{market}.{code}", "klt": "101", "fqt": "0", "lmt": str(limit),
            "end": "20500101", "iscca": "1", "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        })
        klines = (payload.get("data") or {}).get("klines") or []
        rows: list[dict[str, Any]] = []
        for item in klines:
            fields = str(item).split(",")
            if len(fields) < 10:
                continue
            try:
                close = float(fields[2])
                rows.append({
                    "trade_date": fields[0].replace("-", ""), "open": float(fields[1]),
                    "close": close, "high": float(fields[3]), "low": float(fields[4]),
                    "volume": float(fields[5]), "amount": float(fields[6]), "pre_close": close - float(fields[9]),
                })
            except ValueError:
                continue
        return rows
