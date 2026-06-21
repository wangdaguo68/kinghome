import re
from typing import Any


TRADABLE_CODE = re.compile(r"^(000|001|002|003|300|301|600|601|603|605)")


def is_tradable(row: dict[str, Any]) -> bool:
    code = str(row.get("code", ""))
    name = str(row.get("name", ""))
    listing_days = int(row.get("listing_days", 0) or 0)
    return bool(TRADABLE_CODE.match(code)) and "ST" not in name.upper() and listing_days >= 60


def filter_tradable(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_tradable(row)]
