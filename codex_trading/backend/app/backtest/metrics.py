from __future__ import annotations

from app.data.schemas import Trade


def summarize_trades(trades: list[Trade]) -> dict[str, float]:
    if not trades:
        return {
            "trade_count": 0,
            "total_return_pct": 0,
            "win_rate_pct": 0,
            "average_return_pct": 0,
            "max_drawdown_pct": 0,
            "profit_loss_ratio": 0,
        }

    returns = [trade.pnl_pct * trade.position_pct / 100 for trade in trades]
    equity = 0.0
    peak = 0.0
    drawdowns: list[float] = []
    for value in returns:
        equity += value
        peak = max(peak, equity)
        drawdowns.append(equity - peak)

    wins = [trade.pnl_pct for trade in trades if trade.pnl_pct > 0]
    losses = [abs(trade.pnl_pct) for trade in trades if trade.pnl_pct < 0]
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    return {
        "trade_count": float(len(trades)),
        "total_return_pct": round(sum(returns), 2),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
        "average_return_pct": round(sum(trade.pnl_pct for trade in trades) / len(trades), 2),
        "max_drawdown_pct": round(min(drawdowns), 2),
        "profit_loss_ratio": round(avg_win / avg_loss, 2) if avg_loss else 0,
    }

