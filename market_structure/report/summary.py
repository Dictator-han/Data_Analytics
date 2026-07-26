"""Write JSON / Markdown validation reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_report(
    out_dir: str | Path,
    summary: dict[str, Any],
    event_study: dict[str, Any],
    save_events_csv: bool = True,
) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    json_path = out / "summary.json"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    paths["summary_json"] = json_path

    md = _to_markdown(summary)
    md_path = out / "summary.md"
    md_path.write_text(md, encoding="utf-8")
    paths["summary_md"] = md_path

    es = event_study.get("summary")
    if isinstance(es, pd.DataFrame) and not es.empty:
        p = out / "event_study.csv"
        es.to_csv(p, index=False)
        paths["event_study_csv"] = p

    phase = event_study.get("phase_alignment")
    if isinstance(phase, pd.DataFrame) and not phase.empty:
        p = out / "phase_alignment.csv"
        phase.to_csv(p, index=False)
        paths["phase_alignment_csv"] = p

    if save_events_csv:
        ev_dir = out / "events"
        ev_dir.mkdir(exist_ok=True)
        for state, table in event_study.get("events", {}).items():
            if isinstance(table, pd.DataFrame) and not table.empty:
                p = ev_dir / f"{state}.csv"
                table.to_csv(p)
                paths[f"events_{state}"] = p

    return paths


def _to_markdown(summary: dict[str, Any]) -> str:
    bt = summary.get("backtest", {})
    lines = [
        "# Market Structure Validation Report",
        "",
        "## Verdict",
        "",
        str(summary.get("verdict", "")),
        "",
        "## Backtest",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for k, v in bt.items():
        if isinstance(v, float):
            lines.append(f"| {k} | {v:.4f} |")
        else:
            lines.append(f"| {k} | {v} |")

    lines += ["", "## Top States (event study)", ""]
    tops = summary.get("top_states") or []
    if not tops:
        lines.append("_No state events_")
    else:
        lines.append("| state | n | side | net_mean_5 | hit_5 |")
        lines.append("|---|---:|---:|---:|---:|")
        for r in tops:
            lines.append(
                "| {state} | {n_events} | {side} | {net_mean_5} | {hit_5} |".format(
                    state=r.get("state"),
                    n_events=r.get("n_events"),
                    side=r.get("side"),
                    net_mean_5=_fmt(r.get("net_mean_5")),
                    hit_5=_fmt(r.get("hit_5")),
                )
            )

    lines += ["", "## Latent Phase Alignment (synthetic)", ""]
    phase = summary.get("phase_alignment") or []
    if not phase:
        lines.append("_Not available (needs synthetic latent labels)_")
    else:
        lines.append("| state | target | n | hit | baseline | lift |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for r in phase:
            lines.append(
                f"| {r.get('state')} | {r.get('target_phase')} | {r.get('n')} | "
                f"{_fmt(r.get('exact_hit_rate'))} | {_fmt(r.get('baseline'))} | "
                f"{_fmt(r.get('lift'))} |"
            )

    lines += [
        "",
        "## Framework",
        "",
        "- 波浪层：可计算阶段候选（非主观数浪）",
        "- 流动性层：池 / 清扫 / 收回",
        "- 订单流层：失衡 / 吸收 / 效率 / 背离代理",
        "- 验证层：事件研究 + 规则回测",
        "",
    ]
    return "\n".join(lines)


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)
