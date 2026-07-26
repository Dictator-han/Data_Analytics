"""Liquidity pool, sweep, and reclaim detectors."""

from __future__ import annotations

import numpy as np
import pandas as pd


def liquidity_pools(
    swings: pd.DataFrame,
    lookback: int = 80,
) -> pd.DataFrame:
    """Prior swing highs/lows as resting liquidity magnets."""
    sh = swings["swing_high"]
    sl = swings["swing_low"]
    # use rolling max/min of confirmed swings (NaNs ignored)
    pool_high = sh.rolling(lookback, min_periods=1).max()
    pool_low = sl.rolling(lookback, min_periods=1).min()
    # shift so we only use already-known pools
    return pd.DataFrame(
        {
            "liq_high": pool_high.shift(1),
            "liq_low": pool_low.shift(1),
        },
        index=swings.index,
    )


def detect_sweeps(
    df: pd.DataFrame,
    pools: pd.DataFrame,
    atr: pd.Series,
    buffer_atr: float = 0.05,
    reclaim_bars: int = 5,
) -> pd.DataFrame:
    """Sweep = pierce liquidity then reclaim within N bars.

    Bullish sweep (for long continuation): take out lows then close back above.
    Bearish sweep: take out highs then close back below.
    """
    n = len(df)
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    close = df["close"].to_numpy()
    liq_low = pools["liq_low"].to_numpy()
    liq_high = pools["liq_high"].to_numpy()
    atr_v = atr.to_numpy()

    pierce_low = np.zeros(n, dtype=bool)
    pierce_high = np.zeros(n, dtype=bool)
    sweep_reclaim_long = np.zeros(n, dtype=bool)
    sweep_reclaim_short = np.zeros(n, dtype=bool)
    sweep_depth_atr = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(atr_v[i]) or atr_v[i] <= 0:
            continue
        buf = buffer_atr * atr_v[i]
        if not np.isnan(liq_low[i]) and low[i] < liq_low[i] - buf:
            pierce_low[i] = True
            sweep_depth_atr[i] = (liq_low[i] - low[i]) / atr_v[i]
            # reclaim: close back above pool within reclaim_bars
            end = min(n, i + reclaim_bars + 1)
            for j in range(i, end):
                if close[j] > liq_low[i]:
                    sweep_reclaim_long[j] = True
                    break
        if not np.isnan(liq_high[i]) and high[i] > liq_high[i] + buf:
            pierce_high[i] = True
            sweep_depth_atr[i] = (high[i] - liq_high[i]) / atr_v[i]
            end = min(n, i + reclaim_bars + 1)
            for j in range(i, end):
                if close[j] < liq_high[i]:
                    sweep_reclaim_short[j] = True
                    break

    out = pd.DataFrame(
        {
            "pierce_low": pierce_low,
            "pierce_high": pierce_high,
            "sweep_reclaim_long": sweep_reclaim_long,
            "sweep_reclaim_short": sweep_reclaim_short,
            "sweep_depth_atr": sweep_depth_atr,
        },
        index=df.index,
    )
    # pierce and reclaim rarely share the same bar — keep a short memory
    out["recent_pierce_low"] = (
        out["pierce_low"].astype(bool).rolling(reclaim_bars, min_periods=1).max().astype(bool)
    )
    out["recent_pierce_high"] = (
        out["pierce_high"].astype(bool).rolling(reclaim_bars, min_periods=1).max().astype(bool)
    )
    return out
