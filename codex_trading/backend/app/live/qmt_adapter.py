from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    name: str
    side: str
    position_pct: float
    strategy: str
    signal_date: str
    planned_entry_date: str | None
    execution_rule: str


class QmtAdapter:
    def status(self) -> dict[str, object]:
        return {
            "enabled": False,
            "mode": "模拟准备",
            "broker": "兴业证券",
            "message": "QMT 实盘下单未启用；当前只生成订单意图和飞书提醒。",
        }

    def submit_order(self, intent: OrderIntent) -> dict[str, object]:
        return {
            "submitted": False,
            "intent": asdict(intent),
            "reason": "QMT 实盘权限未接入，已阻止真实下单。",
        }
