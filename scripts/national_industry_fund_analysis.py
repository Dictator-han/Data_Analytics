#!/usr/bin/env python3
"""筛选十大流通股东中含“国家”+“产业投资基金”的个股，并计算自2026年以来最高涨幅倍数。"""

from __future__ import annotations

import time
from pathlib import Path

import akshare as ak
import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REPORT_CANDIDATES = ["20260630", "20260331", "20251231"]
PRICE_START = "20260101"
PRICE_END = "20261231"


def fetch_latest_free_holders() -> tuple[pd.DataFrame, str]:
    """优先半年报，不可用或样本过少时回退到一季报。"""
    last_error = None
    for date in REPORT_CANDIDATES:
        try:
            print(f"Fetching free holders for {date} ...")
            df = ak.stock_gdfx_free_holding_detail_em(date=date)
            n_stocks = df["股票代码"].nunique()
            print(f"  got {len(df)} rows, {n_stocks} stocks")
            # 半年报若披露过少（<500只），回退到一季报
            if date.endswith("0630") and n_stocks < 500:
                print(f"  {date} disclosure incomplete ({n_stocks}<500), try next")
                continue
            return df, date
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"  failed: {exc}")
    raise RuntimeError(f"无法获取股东数据: {last_error}")


def filter_target_holders(df: pd.DataFrame) -> pd.DataFrame:
    name = df["股东名称"].astype(str)
    mask = name.str.contains("国家", regex=False) & name.str.contains(
        "产业投资基金", regex=False
    )
    cols = [
        "股票代码",
        "股票简称",
        "股东名称",
        "股东类型",
        "报告期",
        "期末持股-数量",
        "期末持股-数量变化",
        "期末持股-持股变动",
        "期末持股-流通市值",
        "公告日",
    ]
    out = df.loc[mask, cols].copy()
    out["股票代码"] = out["股票代码"].astype(str).str.zfill(6)
    # 东财偶发脱敏名称校正（新浪流通股东可核验）
    out["股东名称"] = out["股东名称"].replace(
        {
            "国家XXXX产业投资基金有限责任公司": "国家军民融合产业投资基金有限责任公司",
        }
    )
    return out.sort_values(["股票代码", "股东名称"]).reset_index(drop=True)


def _to_sina_symbol(symbol: str) -> str:
    code = str(symbol).zfill(6)
    if code.startswith(("5", "6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def fetch_max_multiple(symbol: str, retries: int = 3) -> dict:
    """最高涨幅倍数 = 2026年以来最高价 / 2026年首个交易日收盘价（前复权）。

    优先新浪日线（更稳定），失败再回退东方财富。
    """
    symbol = str(symbol).zfill(6)
    last_error = None
    hist = None

    for attempt in range(retries):
        try:
            hist = ak.stock_zh_a_daily(
                symbol=_to_sina_symbol(symbol),
                start_date=PRICE_START,
                end_date=PRICE_END,
                adjust="qfq",
            )
            if hist is not None and not hist.empty:
                break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.0 + attempt)
            try:
                hist = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=PRICE_START,
                    end_date=PRICE_END,
                    adjust="qfq",
                )
                if hist is not None and not hist.empty:
                    break
            except Exception as exc2:  # noqa: BLE001
                last_error = exc2
                time.sleep(1.0 + attempt)

    if hist is None or hist.empty:
        return {
            "股票代码": symbol,
            "起始日": None,
            "起始收盘价": None,
            "最高日": None,
            "最高价": None,
            "最高涨幅倍数": None,
            "最高涨幅%": None,
            "最新日": None,
            "最新收盘价": None,
            "现价相对起始倍数": None,
            "错误": str(last_error) if last_error else "无行情数据",
        }

    # 统一列名：新浪用英文，东财用中文
    rename = {
        "date": "日期",
        "open": "开盘",
        "high": "最高",
        "low": "最低",
        "close": "收盘",
    }
    hist = hist.rename(columns=rename)
    hist = hist.sort_values("日期").reset_index(drop=True)
    start_row = hist.iloc[0]
    high_idx = hist["最高"].astype(float).idxmax()
    high_row = hist.loc[high_idx]
    latest_row = hist.iloc[-1]

    start_close = float(start_row["收盘"])
    max_high = float(high_row["最高"])
    latest_close = float(latest_row["收盘"])
    multiple = max_high / start_close if start_close else None
    current_multiple = latest_close / start_close if start_close else None

    return {
        "股票代码": symbol,
        "起始日": str(start_row["日期"])[:10],
        "起始收盘价": round(start_close, 4),
        "最高日": str(high_row["日期"])[:10],
        "最高价": round(max_high, 4),
        "最高涨幅倍数": round(multiple, 4) if multiple is not None else None,
        "最高涨幅%": round((multiple - 1) * 100, 2) if multiple is not None else None,
        "最新日": str(latest_row["日期"])[:10],
        "最新收盘价": round(latest_close, 4),
        "现价相对起始倍数": round(current_multiple, 4)
        if current_multiple is not None
        else None,
        "错误": None,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    holders_raw, report_date = fetch_latest_free_holders()
    holders_raw.to_csv(
        DATA_DIR / f"free_holders_{report_date}.csv", index=False, encoding="utf-8-sig"
    )

    matched = filter_target_holders(holders_raw)
    matched.to_csv(
        OUTPUT_DIR / "matched_holders_detail.csv", index=False, encoding="utf-8-sig"
    )

    # 按股票汇总匹配股东
    stock_summary = (
        matched.groupby(["股票代码", "股票简称"], as_index=False)
        .agg(
            匹配股东数量=("股东名称", "nunique"),
            匹配股东=("股东名称", lambda s: "；".join(sorted(set(s.astype(str))))),
            报告期=("报告期", "first"),
        )
        .sort_values("股票代码")
        .reset_index(drop=True)
    )

    print(f"Matched holder rows: {len(matched)}")
    print(f"Matched stocks: {len(stock_summary)}")
    print("Unique holder names:")
    print(matched["股东名称"].value_counts().to_string())

    price_rows = []
    symbols = stock_summary["股票代码"].tolist()
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] price {symbol}")
        price_rows.append(fetch_max_multiple(symbol))
        time.sleep(0.25)

    price_df = pd.DataFrame(price_rows)
    result = stock_summary.merge(price_df, on="股票代码", how="left")
    result = result.sort_values("最高涨幅倍数", ascending=False, na_position="last")
    result.to_csv(
        OUTPUT_DIR / "national_industry_fund_stocks.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # 简要 markdown 报告
    lines = [
        "# 国家×产业投资基金 十大流通股东个股分析",
        "",
        "- 数据来源：东方财富十大流通股东 + 新浪前复权日线（akshare）",
        f"- 使用报告期：{report_date}（无完整最新半年报时回退一季报）",
        "- 筛选条件：十大流通股东名称同时包含“国家”与“产业投资基金”",
        "- 最高涨幅倍数 = 2026年以来最高价 ÷ 2026年首个交易日收盘价（前复权）",
        f"- 匹配个股数：{len(result)}",
        "",
        "## 匹配股东名称分布",
        "",
        matched["股东名称"].value_counts().to_markdown(),
        "",
        "## 个股最高涨幅倍数（降序）",
        "",
    ]
    show_cols = [
        "股票代码",
        "股票简称",
        "匹配股东",
        "起始收盘价",
        "最高价",
        "最高涨幅倍数",
        "最高涨幅%",
        "现价相对起始倍数",
        "最高日",
    ]
    lines.append(result[show_cols].to_markdown(index=False))
    report_path = OUTPUT_DIR / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n=== TOP by max multiple ===")
    print(
        result[
            [
                "股票代码",
                "股票简称",
                "最高涨幅倍数",
                "最高涨幅%",
                "匹配股东",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )
    print(f"\nSaved: {OUTPUT_DIR / 'national_industry_fund_stocks.csv'}")
    print(f"Saved: {report_path}")


if __name__ == "__main__":
    main()
