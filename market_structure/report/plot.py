"""Validation plots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_validation(
    frame: pd.DataFrame,
    backtest: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1.2, 1.4]})

    ax = axes[0]
    ax.plot(frame.index, frame["close"], color="#1f4e79", lw=1.2, label="close")
    entries = frame[frame["entry_signal"] != 0]
    longs = entries[entries["entry_signal"] > 0]
    shorts = entries[entries["entry_signal"] < 0]
    ax.scatter(longs.index, longs["close"], marker="^", c="#2a9d8f", s=28, label="long entry", zorder=3)
    ax.scatter(shorts.index, shorts["close"], marker="v", c="#e76f51", s=28, label="short entry", zorder=3)
    if "liq_high" in frame.columns:
        ax.plot(frame.index, frame["liq_high"], color="#adb5bd", lw=0.8, alpha=0.7, label="liq high")
        ax.plot(frame.index, frame["liq_low"], color="#ced4da", lw=0.8, alpha=0.7, label="liq low")
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_title("Market Structure + Liquidity Signal Overlay")

    ax = axes[1]
    ax.plot(frame.index, frame["efficiency"].fillna(0), color="#457b9d", lw=1.0, label="efficiency")
    ax.plot(frame.index, frame["imbalance"].fillna(0), color="#e9c46a", lw=1.0, label="imbalance")
    ax.axhline(0, color="#999", lw=0.5)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_ylabel("OF proxy")

    ax = axes[2]
    equity = backtest.get("equity")
    if equity is not None and len(equity):
        ax.plot(equity.index, equity.values, color="#264653", lw=1.2)
    ax.set_ylabel("Equity")
    ax.set_xlabel("Date")

    fig.tight_layout()
    p = out / "overview.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    paths["overview"] = p

    # state timeline
    if "primary_state" in frame.columns:
        fig, ax = plt.subplots(figsize=(12, 3.5))
        states = frame["primary_state"].astype(str)
        codes, uniques = pd.factorize(states)
        ax.scatter(frame.index, codes, c=codes, cmap="tab20", s=6, alpha=0.85)
        ax.set_yticks(range(len(uniques)))
        ax.set_yticklabels(list(uniques), fontsize=7)
        ax.set_title("Primary State Path")
        fig.tight_layout()
        p = out / "states.png"
        fig.savefig(p, dpi=140)
        plt.close(fig)
        paths["states"] = p

    return paths
