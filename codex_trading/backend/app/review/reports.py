from __future__ import annotations

from app.backtest.engine import BacktestResult
from app.data.schemas import CycleState


def render_daily_report(cycle: CycleState, result: BacktestResult) -> str:
    return "\n".join(
        [
            f"# {cycle.trade_date} 日复盘",
            "",
            f"- CycleTag：{cycle.tag}",
            f"- RedCount：{cycle.red_count}",
            f"- MA3/MA5：{cycle.ma3} / {cycle.ma5}",
            f"- 回测交易数：{int(result.metrics['trade_count'])}",
            f"- 总收益贡献：{result.metrics['total_return_pct']}%",
            f"- 风控拒绝信号：{len(result.rejected_signals)}",
        ]
    )

