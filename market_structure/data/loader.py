"""OHLCV loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .synthetic import generate_wave_liquidity_series


REQUIRED_COLS = ("open", "high", "low", "close", "volume")


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for need in REQUIRED_COLS:
        if need in df.columns:
            continue
        if need in colmap:
            rename[colmap[need]] = need
        else:
            # common aliases
            aliases = {
                "open": ["o", "开盘", "开盘价"],
                "high": ["h", "最高", "最高价"],
                "low": ["l", "最低", "最低价"],
                "close": ["c", "收盘", "收盘价", "adj close", "adj_close"],
                "volume": ["v", "vol", "成交量"],
            }
            for alias in aliases[need]:
                if alias in colmap:
                    rename[colmap[alias]] = need
                    break
    out = df.rename(columns=rename).copy()
    missing = [c for c in REQUIRED_COLS if c not in out.columns]
    if missing:
        raise ValueError(f"OHLCV missing columns: {missing}")

    if not isinstance(out.index, pd.DatetimeIndex):
        for cand in ("datetime", "date", "time", "timestamp", "日期"):
            if cand in out.columns:
                out[cand] = pd.to_datetime(out[cand])
                out = out.set_index(cand)
                break
            if cand in {c.lower() for c in out.columns}:
                # already handled by lower map above if renamed
                pass
        if not isinstance(out.index, pd.DatetimeIndex):
            out.index = pd.to_datetime(out.index)

    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    for c in REQUIRED_COLS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=list(REQUIRED_COLS))
    if out.empty:
        raise ValueError("OHLCV is empty after cleaning")
    return out


def load_from_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return _normalize_ohlcv(df)


def load_from_yfinance(symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "yfinance is required for market data. Install with: pip install yfinance"
        ) from exc

    raw = yf.download(
        symbol,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if raw.empty:
        raise ValueError(f"No yfinance data for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]
    raw = raw.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    return _normalize_ohlcv(raw)


def load_ohlcv(cfg: dict[str, Any]) -> pd.DataFrame:
    """Load OHLCV according to config.data section."""
    source = str(cfg.get("source", "synthetic")).lower()
    if source == "synthetic":
        return generate_wave_liquidity_series(
            bars=int(cfg.get("synthetic_bars", 1200)),
            seed=int(cfg.get("synthetic_seed", 42)),
        )
    if source == "csv":
        path = cfg.get("csv_path")
        if not path:
            raise ValueError("data.csv_path is required when source=csv")
        return load_from_csv(path)
    if source == "yfinance":
        symbol = cfg.get("yfinance_symbol") or cfg.get("symbol")
        if not symbol:
            raise ValueError("data.yfinance_symbol is required when source=yfinance")
        return load_from_yfinance(
            symbol=str(symbol),
            start=str(cfg.get("start", "2018-01-01")),
            end=cfg.get("end"),
        )
    raise ValueError(f"Unknown data source: {source}")
