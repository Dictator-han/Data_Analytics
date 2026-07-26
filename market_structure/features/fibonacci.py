"""Fibonacci retracement utilities for wave-proxy gates."""

from __future__ import annotations

import numpy as np
import pandas as pd


def impulse_retracement(
    df: pd.DataFrame,
    swings: pd.DataFrame,
    lookback: int = 80,
) -> pd.DataFrame:
    """Compute retracement of the latest impulse leg.

    For each bar, find the most recent swing low then subsequent swing high
    (bullish impulse), and measure how far price has retraced that leg.
    """
    n = len(df)
    close = df["close"].to_numpy()
    sh = swings["swing_high"].to_numpy()
    sl = swings["swing_low"].to_numpy()

    impulse_low = np.full(n, np.nan)
    impulse_high = np.full(n, np.nan)
    retrace = np.full(n, np.nan)
    impulse_dir = np.zeros(n, dtype=int)  # +1 bullish impulse, -1 bearish

    high_idx = [i for i in range(n) if not np.isnan(sh[i])]
    low_idx = [i for i in range(n) if not np.isnan(sl[i])]

    for i in range(n):
        # nearest swing low then later swing high within lookback
        lows = [j for j in low_idx if i - lookback <= j < i]
        highs = [j for j in high_idx if i - lookback <= j < i]
        if len(lows) >= 1 and len(highs) >= 1:
            # bullish impulse: low then high
            l = lows[-1]
            later_highs = [j for j in highs if j > l]
            if later_highs:
                h = later_highs[-1]
                lo = sl[l]
                hi = sh[h]
                if hi > lo:
                    impulse_low[i] = lo
                    impulse_high[i] = hi
                    retrace[i] = (hi - close[i]) / (hi - lo)
                    impulse_dir[i] = 1
                    continue
            # bearish impulse: high then low
            h = highs[-1]
            later_lows = [j for j in lows if j > h]
            if later_lows:
                l = later_lows[-1]
                hi = sh[h]
                lo = sl[l]
                if hi > lo:
                    impulse_low[i] = lo
                    impulse_high[i] = hi
                    retrace[i] = (close[i] - lo) / (hi - lo)
                    impulse_dir[i] = -1

    return pd.DataFrame(
        {
            "impulse_low": impulse_low,
            "impulse_high": impulse_high,
            "retrace_ratio": retrace,
            "impulse_dir": impulse_dir,
        },
        index=df.index,
    )


def in_fib_band(retrace: pd.Series, lo: float = 0.5, hi: float = 0.618) -> pd.Series:
    return retrace.between(lo, hi)
