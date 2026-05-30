from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATEMENT = ROOT / "data" / "king.xls"


@dataclass(frozen=True)
class BrokerFeeModel:
    source: str
    sample_count: int
    min_commission: float
    commission_rate: float
    commission_rate_upper_bound: float
    stamp_tax_rate: float
    transfer_fee_rate: float

    def estimate_fee(self, symbol: str, buy_amount: float, sell_amount: float) -> float:
        buy_commission = max(self.min_commission, buy_amount * self.commission_rate)
        sell_commission = max(self.min_commission, sell_amount * self.commission_rate)
        stamp_tax = sell_amount * self.stamp_tax_rate
        transfer_fee = 0.0
        if symbol.endswith(".SH") or symbol.startswith(("600", "601", "603", "605")):
            transfer_fee = (buy_amount + sell_amount) * self.transfer_fee_rate
        return round(buy_commission + sell_commission + stamp_tax + transfer_fee, 4)


NO_FEE_MODEL = BrokerFeeModel(
    source="none",
    sample_count=0,
    min_commission=0,
    commission_rate=0,
    commission_rate_upper_bound=0,
    stamp_tax_rate=0,
    transfer_fee_rate=0,
)


def load_broker_fee_model(path: Path = DEFAULT_STATEMENT) -> BrokerFeeModel:
    if not path.exists():
        return NO_FEE_MODEL

    rows = _load_stock_trade_rows(path)
    if not rows:
        return NO_FEE_MODEL

    min_commission = min(row["commission"] for row in rows if row["commission"] > 0)
    commission_over_min = [row for row in rows if row["commission"] > min_commission]
    if commission_over_min:
        commission_rate = _weighted_rate(commission_over_min, "commission")
        commission_upper_bound = commission_rate
    else:
        commission_rate = 0.0
        commission_upper_bound = min(float(min_commission / row["amount"]) for row in rows if row["amount"] > 0)

    sell_rows = [row for row in rows if row["operation"] == "证券卖出" and row["stamp_tax"] > 0]
    transfer_rows = [row for row in rows if row["other_fee"] > 0]
    return BrokerFeeModel(
        source=str(path),
        sample_count=len(rows),
        min_commission=float(min_commission),
        commission_rate=float(commission_rate),
        commission_rate_upper_bound=float(commission_upper_bound),
        stamp_tax_rate=float(_weighted_rate(sell_rows, "stamp_tax")) if sell_rows else 0,
        transfer_fee_rate=float(_weighted_rate(transfer_rows, "other_fee")) if transfer_rows else 0,
    )


def _load_stock_trade_rows(path: Path) -> list[dict[str, Decimal | str]]:
    rows: list[dict[str, Decimal | str]] = []
    with path.open(encoding="gbk", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            operation = row.get("操作", "")
            if operation not in {"证券买入", "证券卖出"}:
                continue
            code = row.get("证券代码", "")
            if not _is_a_share_code(code):
                continue
            amount = abs(Decimal(row["成交金额"]))
            if amount <= 0:
                continue
            rows.append(
                {
                    "operation": operation,
                    "amount": amount,
                    "commission": Decimal(row["手续费"]),
                    "stamp_tax": Decimal(row["印花税"]),
                    "other_fee": Decimal(row["其他杂费"]),
                }
            )
    return rows


def _is_a_share_code(code: str) -> bool:
    return code.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605"))


def _weighted_rate(rows: list[dict[str, Decimal | str]], field: str) -> Decimal:
    if not rows:
        return Decimal("0")
    amount = sum(row["amount"] for row in rows if isinstance(row["amount"], Decimal))
    fee = sum(row[field] for row in rows if isinstance(row[field], Decimal))
    if amount <= 0:
        return Decimal("0")
    return fee / amount
