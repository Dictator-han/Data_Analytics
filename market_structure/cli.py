"""CLI entrypoint: mslab validate --config configs/default.yaml"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_structure.pipeline import load_config, run_validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mslab",
        description="Market Structure + Liquidity + Order Flow validation lab",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Run end-to-end validation")
    p_val.add_argument("--config", type=str, default=None, help="Path to YAML config")
    p_val.add_argument("--source", type=str, default=None, help="Override data.source")
    p_val.add_argument("--symbol", type=str, default=None, help="Override yfinance symbol")
    p_val.add_argument("--csv", type=str, default=None, help="CSV path when source=csv")
    p_val.add_argument("--out", type=str, default=None, help="Output directory")
    p_val.add_argument("--seed", type=int, default=None, help="Synthetic seed")
    p_val.add_argument("--bars", type=int, default=None, help="Synthetic bars")

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        cfg = load_config(args.config)
        data = cfg.setdefault("data", {})
        output = cfg.setdefault("output", {})
        if args.source:
            data["source"] = args.source
        if args.symbol:
            data["yfinance_symbol"] = args.symbol
            data["symbol"] = args.symbol
        if args.csv:
            data["source"] = "csv"
            data["csv_path"] = args.csv
        if args.seed is not None:
            data["synthetic_seed"] = args.seed
        if args.bars is not None:
            data["synthetic_bars"] = args.bars
        if args.out:
            output["dir"] = args.out

        result = run_validation(cfg)
        summary = result["summary"]
        print(json.dumps(
            {
                "verdict": summary.get("verdict"),
                "backtest": summary.get("backtest"),
                "paths": result["paths"],
            },
            ensure_ascii=False,
            indent=2,
        ))
        # also echo markdown path
        md = result["paths"].get("summary_md")
        if md and Path(md).exists():
            print("\n--- summary.md ---\n")
            print(Path(md).read_text(encoding="utf-8"))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
