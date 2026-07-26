from __future__ import annotations

from pathlib import Path

import pandas as pd

from market_structure.data.synthetic import generate_wave_liquidity_series
from market_structure.features.pipeline import build_feature_frame
from market_structure.pipeline import load_config, run_validation
from market_structure.signals.fusion import build_signals
from market_structure.states.machine import annotate_states


def test_synthetic_shape():
    df = generate_wave_liquidity_series(bars=300, seed=1)
    assert len(df) == 300
    assert set(["open", "high", "low", "close", "volume", "latent_phase"]).issubset(df.columns)
    assert df["close"].gt(0).all()


def test_feature_and_state_pipeline():
    cfg = load_config()
    df = generate_wave_liquidity_series(bars=400, seed=2)
    feats = build_feature_frame(df, cfg)
    states = annotate_states(feats, cfg)
    sig = build_signals(states, cfg)
    assert "W2_END_CANDIDATE" in sig.columns
    assert "entry_signal" in sig.columns
    assert sig["efficiency"].notna().sum() > 50


def test_run_validation_artifacts(tmp_path: Path):
    cfg = load_config()
    cfg["data"]["source"] = "synthetic"
    cfg["data"]["synthetic_bars"] = 500
    cfg["data"]["synthetic_seed"] = 7
    cfg["output"]["dir"] = str(tmp_path / "out")
    cfg["output"]["save_plots"] = True
    result = run_validation(cfg)
    assert Path(result["paths"]["summary_json"]).exists()
    assert Path(result["paths"]["summary_md"]).exists()
    assert Path(result["paths"]["overview"]).exists()
    assert "backtest" in result["summary"]
    # event study should find some states on synthetic path
    summary = result["event_study"]["summary"]
    assert isinstance(summary, pd.DataFrame)
    assert not summary.empty
