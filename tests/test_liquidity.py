from __future__ import annotations

import numpy as np
import pandas as pd

from market_structure.features.liquidity import detect_sweeps, liquidity_pools
from market_structure.features.swings import atr, detect_swings


def _make_sweep_frame() -> pd.DataFrame:
    """Build a path with an early swing low, later pierce below it, then reclaim."""
    n = 100
    close = np.full(n, 100.0)
    # gentle uptrend with a local low around i=20
    close[:30] = np.linspace(100, 102, 30)
    close[18:23] = [101.2, 100.4, 99.5, 100.6, 101.5]  # swing low ~99.5
    close[30:55] = np.linspace(102, 106, 25)
    # liquidity sweep of 99.5 then reclaim
    close[55:60] = [105.0, 104.0, 98.8, 100.2, 103.5]
    close[60:] = np.linspace(103.5, 108, n - 60)

    high = close + 0.35
    low = close - 0.35
    low[20] = 99.4
    low[57] = 98.5
    open_ = np.r_[close[0], close[:-1]]
    vol = np.full(n, 1000.0)
    vol[57] = 6000.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def test_sweep_reclaim_long_detected():
    df = _make_sweep_frame()
    swings = detect_swings(df, left=2, right=2)
    pools = liquidity_pools(swings, lookback=60)
    sweeps = detect_sweeps(df, pools, atr=atr(df, 10), buffer_atr=0.0, reclaim_bars=4)
    assert sweeps["pierce_low"].any()
    assert sweeps["sweep_reclaim_long"].any()
