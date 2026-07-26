"""Swing high / low and market-structure primitives."""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    tr = true_range(df["high"], df["low"], df["close"])
    return tr.rolling(window, min_periods=max(2, window // 2)).mean()


def detect_swings(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 3,
) -> pd.DataFrame:
    """Mark confirmed swing highs/lows using a fractal window."""
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    swing_high = np.full(n, np.nan)
    swing_low = np.full(n, np.nan)

    for i in range(left, n - right):
        h_window = high[i - left : i + right + 1]
        l_window = low[i - left : i + right + 1]
        if high[i] >= np.max(h_window) and high[i] > np.max(h_window[:left]):
            swing_high[i] = high[i]
        if low[i] <= np.min(l_window) and low[i] < np.min(l_window[:left]):
            swing_low[i] = low[i]

    out = pd.DataFrame(
        {
            "swing_high": swing_high,
            "swing_low": swing_low,
        },
        index=df.index,
    )
    out["is_swing_high"] = out["swing_high"].notna()
    out["is_swing_low"] = out["swing_low"].notna()
    return out


def last_confirmed_levels(swings: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill last confirmed swing levels for barrier tracking."""
    last_high = swings["swing_high"].ffill()
    last_low = swings["swing_low"].ffill()
    return pd.DataFrame(
        {
            "last_swing_high": last_high,
            "last_swing_low": last_low,
        },
        index=swings.index,
    )


def structure_breaks(df: pd.DataFrame, levels: pd.DataFrame) -> pd.DataFrame:
    """Break of structure / change of character proxies."""
    close = df["close"]
    prev_close = close.shift(1)
    bos_up = (prev_close <= levels["last_swing_high"]) & (close > levels["last_swing_high"])
    bos_down = (prev_close >= levels["last_swing_low"]) & (close < levels["last_swing_low"])
    return pd.DataFrame(
        {
            "bos_up": bos_up.fillna(False),
            "bos_down": bos_down.fillna(False),
        },
        index=df.index,
    )
