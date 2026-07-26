"""Assemble structure / liquidity / order-flow feature frame."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .fibonacci import impulse_retracement, in_fib_band
from .liquidity import detect_sweeps, liquidity_pools
from .orderflow import orderflow_features
from .swings import atr, detect_swings, last_confirmed_levels, structure_breaks


def build_feature_frame(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    scfg = cfg.get("structure", {})
    ocfg = cfg.get("orderflow", {})
    wcfg = cfg.get("wave_proxy", {})

    swings = detect_swings(
        df,
        left=int(scfg.get("swing_left", 3)),
        right=int(scfg.get("swing_right", 3)),
    )
    levels = last_confirmed_levels(swings)
    breaks = structure_breaks(df, levels)
    atr_s = atr(df, window=int(scfg.get("atr_window", 14)))
    pools = liquidity_pools(swings, lookback=int(scfg.get("liquidity_lookback", 80)))
    sweeps = detect_sweeps(
        df,
        pools,
        atr=atr_s,
        buffer_atr=float(scfg.get("sweep_atr_buffer", 0.05)),
        reclaim_bars=int(scfg.get("reclaim_bars", 5)),
    )
    fib = impulse_retracement(
        df,
        swings,
        lookback=int(scfg.get("liquidity_lookback", 80)),
    )
    of = orderflow_features(
        df,
        volume_ma=int(ocfg.get("volume_ma", 20)),
        efficiency_window=int(ocfg.get("efficiency_window", 10)),
        imbalance_window=int(ocfg.get("imbalance_window", 5)),
        absorption_volume_z=float(ocfg.get("absorption_volume_z", 1.5)),
        absorption_range_pctile=float(ocfg.get("absorption_range_pctile", 0.35)),
    )

    fib_ok = in_fib_band(
        fib["retrace_ratio"],
        lo=float(wcfg.get("fib_min", 0.5)),
        hi=float(wcfg.get("fib_max", 0.618)),
    )

    out = pd.concat(
        [
            df[["open", "high", "low", "close", "volume"]],
            swings,
            levels,
            breaks,
            pools,
            sweeps,
            fib,
            of,
            atr_s.rename("atr"),
            fib_ok.rename("in_fib_band"),
        ],
        axis=1,
    )
    # preserve latent labels if present (synthetic validation only)
    for col in ("latent_phase", "latent_cycle"):
        if col in df.columns:
            out[col] = df[col]
    return out
