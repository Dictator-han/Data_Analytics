"""Synthetic OHLCV paths that embed wave-like phases and liquidity sweeps."""

from __future__ import annotations

import numpy as np
import pandas as pd


PHASES = (
    "W1",
    "W2",
    "W3",
    "W4",
    "W5",
    "A",
    "B",
    "C",
)


def _segment_returns(
    n: int,
    drift: float,
    vol: float,
    rng: np.random.Generator,
    sweep_at: int | None = None,
    sweep_shock: float = 0.0,
) -> np.ndarray:
    rets = rng.normal(drift, vol, size=n)
    if sweep_at is not None and 0 <= sweep_at < n:
        rets[sweep_at] += sweep_shock
        # quick reclaim / continuation after sweep
        if sweep_at + 1 < n:
            rets[sweep_at + 1] -= 0.55 * sweep_shock
        if sweep_at + 2 < n:
            rets[sweep_at + 2] -= 0.25 * sweep_shock
    return rets


def generate_wave_liquidity_series(
    bars: int = 1200,
    seed: int = 42,
    start_price: float = 30.0,
) -> pd.DataFrame:
    """Generate a multi-cycle synthetic series with labeled latent phases.

    Latent labels are for validation only — detectors never see them at inference.
    """
    rng = np.random.default_rng(seed)
    cycle_specs = [
        # (phase, n, drift, vol, sweep_frac, sweep_shock, vol_mult)
        ("W1", 40, 0.0022, 0.011, None, 0.0, 1.4),
        ("W2", 38, -0.0018, 0.013, 0.72, -0.045, 1.8),
        ("W3", 70, 0.0038, 0.009, None, 0.0, 1.9),
        ("W4", 30, -0.0009, 0.010, 0.60, -0.022, 1.1),
        ("W5", 45, 0.0010, 0.012, None, 0.0, 0.80),
        ("A", 30, -0.0028, 0.013, None, 0.0, 1.5),
        ("B", 25, 0.0016, 0.011, None, 0.0, 1.0),
        ("C", 42, -0.0032, 0.014, 0.68, -0.048, 1.8),
    ]

    closes: list[float] = []
    volumes: list[float] = []
    phases: list[str] = []
    cycle_ids: list[int] = []

    price = float(start_price)
    cycle = 0
    while len(closes) < bars:
        for phase, n, drift, vol, sweep_frac, sweep_shock, vol_mult in cycle_specs:
            # mild non-stationarity across cycles
            scale = 1.0 + 0.08 * np.sin(cycle / 2.0)
            seg_n = max(12, int(n * rng.uniform(0.85, 1.15)))
            sweep_at = None
            if sweep_frac is not None:
                sweep_at = int(seg_n * sweep_frac)
            rets = _segment_returns(
                seg_n,
                drift=drift * scale,
                vol=vol * scale,
                rng=rng,
                sweep_at=sweep_at,
                sweep_shock=sweep_shock,
            )
            base_vol = rng.lognormal(mean=10.5, sigma=0.25)
            for i, r in enumerate(rets):
                price = max(1.0, price * (1.0 + float(r)))
                # volume signature: sweeps & impulses louder; W5 quieter
                shock = abs(r)
                vol_i = base_vol * vol_mult * (1.0 + 8.0 * shock)
                if phase == "W5":
                    vol_i *= 0.75
                if sweep_at is not None and abs(i - sweep_at) <= 1:
                    vol_i *= 2.2
                closes.append(price)
                volumes.append(float(vol_i))
                phases.append(phase)
                cycle_ids.append(cycle)
                if len(closes) >= bars:
                    break
            if len(closes) >= bars:
                break
        cycle += 1

    close = np.asarray(closes[:bars], dtype=float)
    volume = np.asarray(volumes[:bars], dtype=float)
    phase = np.asarray(phases[:bars])
    cycle_id = np.asarray(cycle_ids[:bars])

    # Build OHLC around close path
    noise = rng.uniform(0.001, 0.006, size=bars)
    open_ = np.empty(bars)
    open_[0] = start_price
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) * (1.0 + noise)
    low = np.minimum(open_, close) * (1.0 - noise)

    # Plant explicit liquidity pools then pierce them during W2/C.
    # Early local low in phase, later deeper spike, then reclaim close.
    for ph, pierce_side in (("W2", "low"), ("C", "high"), ("W4", "low")):
        idx = np.where(phase == ph)[0]
        if len(idx) < 12:
            continue
        # split contiguous phase runs
        runs: list[list[int]] = [[int(idx[0])]]
        for j in idx[1:]:
            if j == runs[-1][-1] + 1:
                runs[-1].append(int(j))
            else:
                runs.append([int(j)])
        for run in runs:
            if len(run) < 12:
                continue
            pool_i = run[max(3, len(run) // 5)]
            sweep_i = run[min(len(run) - 4, int(len(run) * 0.72))]
            if pierce_side == "low":
                pool_px = float(low[pool_i])
                low[pool_i] = min(low[pool_i], close[pool_i] * 0.992)
                low[sweep_i] = min(low[sweep_i], pool_px * 0.978)
                # reclaim within 2 bars
                if sweep_i + 1 < bars:
                    close[sweep_i + 1] = max(close[sweep_i + 1], pool_px * 1.002)
                    open_[sweep_i + 1] = close[sweep_i]
                volume[sweep_i] *= 2.5
            else:
                pool_px = float(high[pool_i])
                high[pool_i] = max(high[pool_i], close[pool_i] * 1.008)
                high[sweep_i] = max(high[sweep_i], pool_px * 1.022)
                if sweep_i + 1 < bars:
                    close[sweep_i + 1] = min(close[sweep_i + 1], pool_px * 0.998)
                    open_[sweep_i + 1] = close[sweep_i]
                volume[sweep_i] *= 2.5

    idx = pd.date_range("2018-01-02", periods=bars, freq="B")
    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "latent_phase": phase,
            "latent_cycle": cycle_id,
        },
        index=idx,
    )
    df.index.name = "datetime"
    return df
