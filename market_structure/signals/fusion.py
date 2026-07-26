"""Fuse structure + liquidity + order-flow states into tradeable events."""

from __future__ import annotations

from typing import Any

import pandas as pd


def build_signals(states: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    scfg = cfg.get("signals", {})
    long_states = list(scfg.get("long_states", ["W2_END_CANDIDATE", "SWEEP_RECLAIM_LONG"]))
    short_states = list(scfg.get("short_states", ["W5_EXHAUST", "C_SWEEP", "SWEEP_RECLAIM_SHORT"]))
    min_score = float(scfg.get("min_score", 0.65))

    long_score = pd.Series(0.0, index=states.index)
    for s in long_states:
        col = f"score_{s}"
        if col in states.columns:
            long_score = long_score.combine(states[col], max)
        elif s in states.columns:
            long_score = long_score.combine(states[s].astype(float), max)

    short_score = pd.Series(0.0, index=states.index)
    for s in short_states:
        col = f"score_{s}"
        if col in states.columns:
            short_score = short_score.combine(states[col], max)
        elif s in states.columns:
            short_score = short_score.combine(states[s].astype(float), max)

    # conflict resolution: keep stronger side
    signal = pd.Series(0, index=states.index, dtype=int)
    long_hit = long_score >= min_score
    short_hit = short_score >= min_score
    signal = signal.mask(long_hit & (long_score >= short_score), 1)
    signal = signal.mask(short_hit & (short_score > long_score), -1)

    # event = first bar of a new non-zero regime (avoid holding every bar)
    prev = signal.shift(1).fillna(0)
    entry = signal.where(signal != prev, 0)

    reason = []
    for i in range(len(states)):
        if entry.iloc[i] > 0:
            reason.append(states["primary_state"].iloc[i])
        elif entry.iloc[i] < 0:
            reason.append(states["primary_state"].iloc[i])
        else:
            reason.append("")

    out = states.copy()
    out["long_score"] = long_score
    out["short_score"] = short_score
    out["position_signal"] = signal
    out["entry_signal"] = entry.astype(int)
    out["signal_reason"] = reason
    return out
