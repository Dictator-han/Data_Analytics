"""Event study: forward returns conditional on state events."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from market_structure.states.machine import STATE_COLS


def _forward_returns(close: pd.Series, horizons: list[int]) -> pd.DataFrame:
    out = {}
    for h in horizons:
        out[f"fwd_ret_{h}"] = close.shift(-h) / close - 1.0
    return pd.DataFrame(out, index=close.index)


def run_event_study(frame: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    vcfg = cfg.get("validation", {})
    horizons = list(vcfg.get("horizons", [1, 3, 5, 10, 20]))
    min_events = int(vcfg.get("min_events", 8))
    cost = float(vcfg.get("cost_bps", 5)) / 10000.0

    fwd = _forward_returns(frame["close"], horizons)
    data = pd.concat([frame, fwd], axis=1)

    rows = []
    event_tables = {}

    # state activation edges (False -> True)
    for state in STATE_COLS:
        if state not in data.columns:
            continue
        active = data[state].astype(bool)
        edge = active & ~active.shift(1).fillna(False).astype(bool)
        events = data.loc[edge].copy()
        if events.empty:
            continue

        # direction hypothesis
        longish = state in {
            "SWEEP_RECLAIM_LONG",
            "W2_END_CANDIDATE",
            "W3_EXPAND",
            "TREND_EXPAND",
            "ABSORB",
            "ACCUMULATE",
        }
        shortish = state in {
            "SWEEP_RECLAIM_SHORT",
            "W5_EXHAUST",
            "A_DISTRIBUTE",
            "C_SWEEP",
            "B_TRAP",
        }
        side = 1 if longish and not shortish else (-1 if shortish and not longish else 0)

        stats = {"state": state, "n_events": int(len(events)), "side": side}
        for h in horizons:
            col = f"fwd_ret_{h}"
            raw = events[col].dropna()
            if raw.empty:
                stats[f"mean_{h}"] = np.nan
                stats[f"hit_{h}"] = np.nan
                stats[f"net_mean_{h}"] = np.nan
                continue
            signed = raw * (side if side != 0 else 1)
            # if side=0, report unsigned mean separately later
            if side == 0:
                signed = raw
            net = signed - cost
            stats[f"mean_{h}"] = float(signed.mean())
            stats[f"hit_{h}"] = float((signed > 0).mean())
            stats[f"net_mean_{h}"] = float(net.mean())
            stats[f"tstat_{h}"] = float(
                signed.mean() / (signed.std(ddof=1) / np.sqrt(len(signed)) + 1e-12)
            )
        stats["enough_events"] = int(len(events) >= min_events)
        rows.append(stats)
        event_tables[state] = events[
            ["close", "primary_state", "primary_score"]
            + [f"fwd_ret_{h}" for h in horizons]
            + (["latent_phase"] if "latent_phase" in events.columns else [])
        ]

    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values("n_events", ascending=False)

    # latent-phase alignment (synthetic only)
    phase_align = None
    if "latent_phase" in data.columns:
        phase_align = _phase_alignment(data, min_events=min_events)

    return {
        "summary": summary,
        "events": event_tables,
        "phase_alignment": phase_align,
        "horizons": horizons,
    }


def _phase_alignment(data: pd.DataFrame, min_events: int = 8) -> pd.DataFrame:
    """How often detected states co-occur with latent synthetic phases."""
    # reclaim often prints on the first bars of the next phase — allow neighbors
    mapping = {
        "W2_END_CANDIDATE": {"W2", "W3"},
        "W3_EXPAND": {"W3"},
        "W4_CLEANUP": {"W4"},
        "W5_EXHAUST": {"W5"},
        "A_DISTRIBUTE": {"A"},
        "B_TRAP": {"B"},
        "C_SWEEP": {"C", "A"},
        "SWEEP_RECLAIM_LONG": {"W2", "W3"},
        "SWEEP_RECLAIM_SHORT": {"C", "A"},
    }
    rows = []
    for state, phases in mapping.items():
        if state not in data.columns:
            continue
        edge = data[state].astype(bool) & ~data[state].astype(bool).shift(1).fillna(False).astype(bool)
        if edge.sum() < min_events:
            continue
        target = sorted(phases)[0]
        hit = data.loc[edge, "latent_phase"].isin(phases).mean()
        baseline = data["latent_phase"].isin(phases).mean()
        rows.append(
            {
                "state": state,
                "target_phase": "|".join(sorted(phases)),
                "n": int(edge.sum()),
                "exact_hit_rate": float(hit),
                "baseline": float(baseline),
                "lift": float(hit / max(baseline, 1e-9)),
            }
        )
    return pd.DataFrame(rows)
