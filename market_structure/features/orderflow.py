"""Order-flow proxies from OHLCV (no L2 required).

True order flow needs tick/L2 data. Here we use microstructure proxies that
are still falsifiable on daily/intraday bars:
- signed volume / imbalance
- price efficiency
- absorption (high volume, compressed range)
- momentum / volume divergence
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def signed_volume(df: pd.DataFrame) -> pd.Series:
    """Approximate buy/sell volume using close location in bar range."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / rng
    clv = clv.fillna(0.0).clip(-1, 1)
    return clv * df["volume"]


def orderflow_features(
    df: pd.DataFrame,
    volume_ma: int = 20,
    efficiency_window: int = 10,
    imbalance_window: int = 5,
    absorption_volume_z: float = 1.5,
    absorption_range_pctile: float = 0.35,
) -> pd.DataFrame:
    vol = df["volume"].astype(float)
    ret = df["close"].pct_change()
    bar_range = (df["high"] - df["low"]).astype(float)
    sv = signed_volume(df)

    vol_ma = vol.rolling(volume_ma, min_periods=max(3, volume_ma // 3)).mean()
    vol_std = vol.rolling(volume_ma, min_periods=max(3, volume_ma // 3)).std()
    vol_z = (vol - vol_ma) / vol_std.replace(0, np.nan)

    imbalance = sv.rolling(imbalance_window, min_periods=2).sum()
    imbalance_norm = imbalance / vol.rolling(imbalance_window, min_periods=2).sum().replace(
        0, np.nan
    )

    # Kaufman-like efficiency: net move / path length
    net = df["close"].diff(efficiency_window).abs()
    path = df["close"].diff().abs().rolling(efficiency_window, min_periods=2).sum()
    efficiency = (net / path.replace(0, np.nan)).clip(0, 1)

    range_pct = bar_range.rolling(volume_ma, min_periods=5).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1],
        raw=False,
    )
    absorption = (vol_z >= absorption_volume_z) & (range_pct <= absorption_range_pctile)

    # sell exhaustion (no lookahead): prior down-shock bar, current bounce
    down_shock = ((ret < 0) & (vol_z > 1.0)).fillna(False)
    sell_exhaust = (
        down_shock.shift(1).fillna(False).astype(bool)
        & (ret >= 0)
        & (efficiency < 0.45)
        & (vol_z.shift(1) > 1.0)
    )

    # W5-style divergence proxy: price near local high, volume declining
    roll_high = df["close"].rolling(efficiency_window, min_periods=3).max()
    near_high = df["close"] >= roll_high * 0.995
    vol_ratio = vol_ma / vol_ma.shift(efficiency_window)
    bull_div_vol = near_high & (vol_ratio < 0.85) & (efficiency < 0.5)

    push = (efficiency > 0.55) & (imbalance_norm > 0.15) & (vol_z > 0.5)
    push_down = (efficiency > 0.55) & (imbalance_norm < -0.15) & (vol_z > 0.5)

    return pd.DataFrame(
        {
            "signed_volume": sv,
            "volume_z": vol_z,
            "imbalance": imbalance_norm,
            "efficiency": efficiency,
            "absorption": absorption.fillna(False),
            "sell_exhaust": sell_exhaust.fillna(False),
            "bull_vol_divergence": bull_div_vol.fillna(False),
            "push_up": push.fillna(False),
            "push_down": push_down.fillna(False),
            "range_pctile": range_pct,
        },
        index=df.index,
    )
