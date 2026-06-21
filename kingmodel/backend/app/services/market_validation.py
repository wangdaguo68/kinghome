from typing import Any


class InvalidMarketData(ValueError):
    pass


def field_value(row: dict[str, Any], *prefixes: str, default: Any = "") -> Any:
    for prefix in prefixes:
        for field, value in row.items():
            if str(field).startswith(prefix):
                return value
    return default


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return default


def row_change(row: dict[str, Any]) -> float:
    return number(field_value(row, "chg", "涨幅", "涨跌幅", default=0))


def result_total(result: dict[str, Any]) -> int:
    try:
        return int(result.get("meta", {}).get("total", 0))
    except (TypeError, ValueError) as exc:
        raise InvalidMarketData("总数不是整数") from exc


def result_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = result.get("data", [])
    if not isinstance(rows, list):
        raise InvalidMarketData("data 不是列表")
    return [row for row in rows if isinstance(row, dict)]


def _limit_threshold(code: str) -> float:
    if code.startswith(("4", "8", "9")):
        return 29.5
    if code.startswith(("30", "68")):
        return 19.5
    return 9.5


def validate_result(key: str, result: dict[str, Any]) -> None:
    total = result_total(result)
    rows = result_rows(result)
    if total < 0:
        raise InvalidMarketData(f"{key} 总数小于零")
    if total and not rows:
        raise InvalidMarketData(f"{key} 有总数但没有样本")

    samples = rows[:10]
    if key == "up" and (total < 100 or any(row_change(row) <= 0 for row in samples)):
        raise InvalidMarketData("上涨家数或样本方向异常")
    if key == "down" and (total < 100 or any(row_change(row) >= 0 for row in samples)):
        raise InvalidMarketData("下跌家数或样本方向异常")
    if key == "flat" and (total > 500 or any(abs(row_change(row)) > 0.001 for row in samples)):
        raise InvalidMarketData("平盘样本方向异常")
    if key == "limit_up":
        for row in samples:
            code = str(row.get("sec_code", ""))
            if row_change(row) < _limit_threshold(code):
                raise InvalidMarketData("涨停列表包含非涨停样本")
    if key == "limit_down":
        for row in samples:
            code = str(row.get("sec_code", ""))
            if row_change(row) > -_limit_threshold(code):
                raise InvalidMarketData("跌停列表包含非跌停样本")
    if key == "failed_limit" and total > 500:
        raise InvalidMarketData("炸板家数异常")
    if key == "continuous" and total:
        if not any(number(field_value(row, "几板", "连板", default=0)) >= 2 for row in samples):
            raise InvalidMarketData("连板列表缺少连板高度")
    if key == "amount_top" and total:
        if not samples or not all(number(field_value(row, "成交额", default=0)) > 0 for row in samples):
            raise InvalidMarketData("成交额排序缺少成交额字段")
    if key in {"sector_top", "sector_bottom"} and total:
        valid = [row for row in samples if str(row.get("sec_code", "")).startswith(("880", "881"))]
        if len(valid) < min(2, len(samples)):
            raise InvalidMarketData("板块列表包含非行业指数样本")


def validate_breadth_totals(up: int, down: int, flat: int) -> None:
    eligible = up + down + flat
    if not 4_000 <= eligible <= 7_000:
        raise InvalidMarketData(f"全市场样本数异常：{eligible}")


def is_trade_candidate(code: str) -> bool:
    return str(code).startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605"))
