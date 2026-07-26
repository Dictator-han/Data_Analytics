"""Horizon-hold rule backtest on fused entry signals."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def run_rule_backtest(frame: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    vcfg = cfg.get("validation", {})
    cost = float(vcfg.get("cost_bps", 5)) / 10000.0
    side_mode = str(vcfg.get("side", "long_short"))
    hold_bars = int(vcfg.get("hold_bars", 5))

    entry = frame["entry_signal"].astype(int).copy()
    if side_mode == "long_only":
        entry = entry.clip(lower=0)
    elif side_mode == "short_only":
        entry = entry.clip(upper=0)

    position = _horizon_positions(entry, hold_bars=hold_bars)
    ret = frame["close"].pct_change().fillna(0.0)
    # execute from next bar
    strat_ret = position.shift(1).fillna(0) * ret
    turns = position.diff().abs().fillna(position.abs())
    costs = turns * cost
    net = strat_ret - costs

    equity = (1.0 + net).cumprod()
    dd = equity / equity.cummax() - 1.0

    trades = _trade_list(position, net)
    metrics = {
        "n_bars": int(len(frame)),
        "n_entries": int((entry != 0).sum()),
        "n_trades": int(len(trades)),
        "hold_bars": hold_bars,
        "total_return": float(equity.iloc[-1] - 1.0) if len(equity) else 0.0,
        "cagr_proxy": float(equity.iloc[-1] ** (252 / max(len(equity), 1)) - 1.0)
        if len(equity)
        else 0.0,
        "vol_ann": float(net.std(ddof=1) * np.sqrt(252)) if len(net) > 2 else 0.0,
        "sharpe": float((net.mean() / (net.std(ddof=1) + 1e-12)) * np.sqrt(252))
        if len(net) > 2
        else 0.0,
        "max_drawdown": float(dd.min()) if len(dd) else 0.0,
        "hit_rate": float((trades["trade_ret"] > 0).mean()) if len(trades) else np.nan,
        "avg_trade": float(trades["trade_ret"].mean()) if len(trades) else np.nan,
        "profit_factor": _profit_factor(trades["trade_ret"]) if len(trades) else np.nan,
    }
    return {
        "metrics": metrics,
        "equity": equity,
        "net_returns": net,
        "position": position,
        "trades": trades,
    }


def _horizon_positions(entry: pd.Series, hold_bars: int) -> pd.Series:
    """Enter on signal, hold fixed bars; later signal overrides."""
    pos = np.zeros(len(entry), dtype=float)
    side = 0
    remaining = 0
    vals = entry.to_numpy()
    for i, e in enumerate(vals):
        if e != 0:
            side = int(e)
            remaining = hold_bars
        if remaining > 0:
            pos[i] = side
            remaining -= 1
        else:
            side = 0
            pos[i] = 0
    return pd.Series(pos, index=entry.index, name="position")


def _trade_list(position: pd.Series, net: pd.Series) -> pd.DataFrame:
    rows = []
    pos = position.to_numpy()
    idx = position.index
    start = None
    cur = 0
    for i in range(len(pos)):
        if pos[i] != cur:
            if cur != 0 and start is not None:
                segment = net.iloc[start:i]
                rows.append(
                    {
                        "start": idx[start],
                        "end": idx[i - 1],
                        "side": int(cur),
                        "bars": int(i - start),
                        "trade_ret": float((1 + segment).prod() - 1),
                    }
                )
            start = i if pos[i] != 0 else None
            cur = int(pos[i])
    if cur != 0 and start is not None:
        segment = net.iloc[start:]
        rows.append(
            {
                "start": idx[start],
                "end": idx[-1],
                "side": int(cur),
                "bars": int(len(pos) - start),
                "trade_ret": float((1 + segment).prod() - 1),
            }
        )
    return pd.DataFrame(rows)


def _profit_factor(trade_rets: pd.Series) -> float:
    gains = trade_rets[trade_rets > 0].sum()
    losses = -trade_rets[trade_rets < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else np.nan
    return float(gains / losses)
