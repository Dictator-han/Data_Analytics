"""Aggregate validation summary for reports / CLI."""

from __future__ import annotations

from typing import Any

import pandas as pd


def summarize_validation(
    event_study: dict[str, Any],
    backtest: dict[str, Any],
) -> dict[str, Any]:
    summary = event_study.get("summary")
    phase = event_study.get("phase_alignment")
    bt = backtest.get("metrics", {})

    top_states = []
    if isinstance(summary, pd.DataFrame) and not summary.empty:
        # prefer horizon 5 if present
        col = "net_mean_5" if "net_mean_5" in summary.columns else None
        if col is None:
            mean_cols = [c for c in summary.columns if c.startswith("net_mean_")]
            col = mean_cols[0] if mean_cols else None
        view = summary.copy()
        if col:
            view = view.sort_values(col, ascending=False)
        top_states = view.head(8).to_dict(orient="records")

    phase_rows = []
    if isinstance(phase, pd.DataFrame) and not phase.empty:
        phase_rows = phase.sort_values("lift", ascending=False).to_dict(orient="records")

    verdict = _verdict(bt, phase_rows, top_states)
    return {
        "backtest": bt,
        "top_states": top_states,
        "phase_alignment": phase_rows,
        "verdict": verdict,
    }


def _verdict(bt: dict[str, Any], phase_rows: list[dict], top_states: list[dict]) -> str:
    parts = []
    sharpe = bt.get("sharpe")
    if sharpe is not None and sharpe == sharpe:
        if sharpe > 0.8:
            parts.append("规则回测风险调整收益为正且较强")
        elif sharpe > 0.2:
            parts.append("规则回测略偏正，需样本外复核")
        else:
            parts.append("规则回测风险调整收益偏弱")

    if phase_rows:
        best = phase_rows[0]
        if best.get("lift", 0) > 1.5 and best.get("exact_hit_rate", 0) > 0.25:
            parts.append(
                f"合成潜变量对齐最好的是 {best['state']}→{best['target_phase']} "
                f"(lift={best['lift']:.2f})"
            )
        else:
            parts.append("合成潜变量对齐一般，状态定义仍需收紧")

    if top_states:
        s0 = top_states[0]
        parts.append(f"事件研究头部状态: {s0.get('state')} (n={s0.get('n_events')})")

    return "；".join(parts) if parts else "样本不足，暂无明确结论"
