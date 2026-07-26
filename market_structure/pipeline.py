"""End-to-end validation pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from market_structure.data.loader import load_ohlcv
from market_structure.features.pipeline import build_feature_frame
from market_structure.report.plot import plot_validation
from market_structure.report.summary import write_report
from market_structure.signals.fusion import build_signals
from market_structure.states.machine import annotate_states
from market_structure.validation.backtest import run_rule_backtest
from market_structure.validation.event_study import run_event_study
from market_structure.validation.metrics import summarize_validation


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_validation(cfg: dict[str, Any] | None = None, config_path: str | Path | None = None) -> dict[str, Any]:
    cfg = cfg or load_config(config_path)
    ohlcv = load_ohlcv(cfg.get("data", {}))
    features = build_feature_frame(ohlcv, cfg)
    states = annotate_states(features, cfg)
    signals = build_signals(states, cfg)

    event_study = run_event_study(signals, cfg)
    backtest = run_rule_backtest(signals, cfg)
    summary = summarize_validation(event_study, backtest)

    out_cfg = cfg.get("output", {})
    out_dir = Path(out_cfg.get("dir", "artifacts/validation"))
    paths = write_report(
        out_dir,
        summary=summary,
        event_study=event_study,
        save_events_csv=bool(out_cfg.get("save_events_csv", True)),
    )
    if out_cfg.get("save_plots", True):
        plot_paths = plot_validation(signals, backtest, out_dir)
        paths.update(plot_paths)

    # persist annotated frame for further research
    frame_path = out_dir / "annotated_frame.csv"
    signals.to_csv(frame_path)
    paths["annotated_frame"] = frame_path

    return {
        "config": cfg,
        "frame": signals,
        "event_study": event_study,
        "backtest": backtest,
        "summary": summary,
        "paths": {k: str(v) for k, v in paths.items()},
    }
