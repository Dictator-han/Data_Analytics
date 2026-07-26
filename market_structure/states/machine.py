"""Computable market-state machine (wave proxies via liquidity mechanisms).

Design principle:
- Do NOT assign "Elliott wave numbers" as subjective labels.
- Emit probabilistic / rule-based stage candidates from falsifiable conditions.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


STATE_COLS = [
    "ACCUMULATE",
    "SWEEP_RECLAIM_LONG",
    "SWEEP_RECLAIM_SHORT",
    "ABSORB",
    "TREND_EXPAND",
    "MANUFACTURE_LIQUIDITY",
    "W2_END_CANDIDATE",
    "W3_EXPAND",
    "W4_CLEANUP",
    "W5_EXHAUST",
    "A_DISTRIBUTE",
    "B_TRAP",
    "C_SWEEP",
]


def _score_w2_end(f: pd.DataFrame, cfg: dict[str, Any]) -> pd.Series:
    """Wave-2 end ≈ liquidity sweep of early buyers + reclaim + sell exhaustion.

    Conditions from research brief:
    - retrace in 0.5~0.618
    - pierce prior low (liquidity hunt)
    - volume expansion
    - quick reclaim
    - sell pressure exhaustion
    """
    recent_pierce = f["recent_pierce_low"] if "recent_pierce_low" in f.columns else f["pierce_low"]
    # soft fib band: allow 0.382-0.786 with full credit inside 0.5-0.618
    retr = f["retrace_ratio"]
    fib_soft = retr.between(0.382, 0.786).astype(float) * 0.15
    fib_core = f["in_fib_band"].astype(float) * 0.15

    score = pd.Series(0.0, index=f.index)
    score += fib_soft + fib_core
    score += recent_pierce.astype(float) * 0.20
    score += f["sweep_reclaim_long"].astype(float) * 0.25
    score += (f["volume_z"] > 0.8).astype(float) * 0.10
    score += f["sell_exhaust"].astype(float) * 0.10
    score += (f["impulse_dir"] == 1).astype(float) * 0.05
    score += (f["imbalance"] > 0).astype(float) * 0.05
    return score.clip(0, 1)


def _score_w3_expand(f: pd.DataFrame, cfg: dict[str, Any]) -> pd.Series:
    wcfg = cfg.get("wave_proxy", {})
    eff_min = float(wcfg.get("w3_efficiency_min", 0.55))
    min_impulse = float(wcfg.get("min_impulse_atr", 1.2))

    impulse_span = (f["impulse_high"] - f["impulse_low"]) / f["atr"].replace(0, np.nan)
    score = pd.Series(0.0, index=f.index)
    score += (f["efficiency"] >= eff_min).astype(float) * 0.30
    score += f["push_up"].astype(float) * 0.25
    score += f["bos_up"].astype(float) * 0.20
    score += (f["imbalance"] > 0.1).astype(float) * 0.15
    score += (impulse_span >= min_impulse).astype(float) * 0.10
    return score.clip(0, 1)


def _score_w5_exhaust(f: pd.DataFrame, cfg: dict[str, Any]) -> pd.Series:
    wcfg = cfg.get("wave_proxy", {})
    decline = float(wcfg.get("w5_vol_decline_ratio", 0.85))
    vol_ma = f["volume"].rolling(20, min_periods=5).mean()
    vol_ratio = vol_ma / vol_ma.shift(10)
    near_high = f["close"] >= f["close"].rolling(20, min_periods=5).max() * 0.998

    score = pd.Series(0.0, index=f.index)
    score += near_high.astype(float) * 0.30
    score += (vol_ratio < decline).astype(float) * 0.25
    score += f["bull_vol_divergence"].astype(float) * 0.25
    score += (f["efficiency"] < 0.45).astype(float) * 0.20
    return score.clip(0, 1)


def _score_abc(f: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    # A: first distribution after push — downside imbalance + volume
    a = (
        0.35 * f["push_down"].astype(float)
        + 0.25 * (f["imbalance"] < -0.1).astype(float)
        + 0.20 * (f["volume_z"] > 0.8).astype(float)
        + 0.20 * f["bos_down"].astype(float)
    ).clip(0, 1)

    # B: trap rally — bounce with weak efficiency after recent downside pressure
    recent_down = (f["imbalance"].rolling(8, min_periods=3).mean() < -0.05)
    weak_up = (f["close"].pct_change() > 0) & (f["efficiency"] < 0.35) & recent_down
    b = (
        0.40 * weak_up.astype(float)
        + 0.20 * (f["imbalance"].between(-0.05, 0.12)).astype(float)
        + 0.20 * (f["volume_z"] < 0.3).astype(float)
        + 0.20 * (f["retrace_ratio"].between(0.3, 0.7) & (f["impulse_dir"] == -1)).astype(float)
    ).clip(0, 1)

    # C: sweep of B buyers — recent pierce high + reclaim short / continuation down
    recent_ph = f["recent_pierce_high"] if "recent_pierce_high" in f.columns else f["pierce_high"]
    c = (
        0.30 * f["sweep_reclaim_short"].astype(float)
        + 0.25 * recent_ph.astype(float)
        + 0.25 * f["push_down"].astype(float)
        + 0.20 * f["bos_down"].astype(float)
    ).clip(0, 1)
    return a, b, c


def annotate_states(features: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Attach mechanism-layer state scores and discrete active state labels."""
    f = features
    min_score = float(cfg.get("signals", {}).get("min_score", 0.65))

    w2 = _score_w2_end(f, cfg)
    w3 = _score_w3_expand(f, cfg)
    w5 = _score_w5_exhaust(f, cfg)
    a, b, c = _score_abc(f)

    # generic microstructure cycle
    accumulate = (
        0.4 * f["absorption"].astype(float)
        + 0.3 * ((f["volume_z"] < 0) & (f["efficiency"] < 0.35)).astype(float)
        + 0.3 * ((f["imbalance"].abs() < 0.08)).astype(float)
    ).clip(0, 1)
    absorb = f["absorption"].astype(float)
    trend = ((f["push_up"] | f["push_down"]).astype(float) * 0.6 + f["efficiency"].fillna(0) * 0.4).clip(
        0, 1
    )
    manufacture = (
        (f["is_swing_high"] | f["is_swing_low"]).astype(float) * 0.5
        + ((f["volume_z"] > 0.5) & (f["efficiency"] < 0.4)).astype(float) * 0.5
    ).clip(0, 1)

    # W4 cleanup: shallow pullback after expansion (require recent push_up context)
    recent_push = f["push_up"].astype(bool).rolling(12, min_periods=1).max().astype(bool)
    no_deep_sweep = ~(
        f["recent_pierce_low"].astype(bool)
        if "recent_pierce_low" in f.columns
        else f["pierce_low"].astype(bool)
    )
    w4 = (
        0.30 * (f["retrace_ratio"].between(0.236, 0.45)).astype(float)
        + 0.25 * (f["impulse_dir"] == 1).astype(float)
        + 0.20 * recent_push.astype(float)
        + 0.15 * (f["volume_z"] < 0.5).astype(float)
        + 0.10 * no_deep_sweep.astype(float)
    ).clip(0, 1)

    scores = pd.DataFrame(
        {
            "score_ACCUMULATE": accumulate,
            "score_SWEEP_RECLAIM_LONG": f["sweep_reclaim_long"].astype(float),
            "score_SWEEP_RECLAIM_SHORT": f["sweep_reclaim_short"].astype(float),
            "score_ABSORB": absorb,
            "score_TREND_EXPAND": trend,
            "score_MANUFACTURE_LIQUIDITY": manufacture,
            "score_W2_END_CANDIDATE": w2,
            "score_W3_EXPAND": w3,
            "score_W4_CLEANUP": w4,
            "score_W5_EXHAUST": w5,
            "score_A_DISTRIBUTE": a,
            "score_B_TRAP": b,
            "score_C_SWEEP": c,
        },
        index=f.index,
    )

    # discrete active flags
    active = pd.DataFrame(index=f.index)
    for state in STATE_COLS:
        active[state] = scores[f"score_{state}"] >= min_score

    # primary state = argmax among scores (for plotting / regime path)
    primary = scores.idxmax(axis=1).str.replace("^score_", "", regex=True)
    primary_score = scores.max(axis=1)
    primary = primary.where(primary_score >= min_score, "NEUTRAL")

    out = f.copy()
    out = pd.concat([out, scores, active], axis=1)
    out["primary_state"] = primary
    out["primary_score"] = primary_score
    return out
