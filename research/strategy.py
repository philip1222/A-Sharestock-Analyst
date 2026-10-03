#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""单只 A 股的交易计划入口。取近 1、7、15、30 个交易日并套用章节规则。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from research.factors.scoring import now_iso
from research.strategy_rules import evaluate
from research.symbols import bare_symbol


def resolve_symbol(symbol: str, table: pd.DataFrame | None = None) -> str:
    """6 位代码直接用。中文名称查 A 股列表，唯一命中才返回代码。"""
    text = symbol.strip()
    if not any("\u4e00" <= char <= "\u9fff" for char in text):
        return bare_symbol(text)
    names = _load_name_table() if table is None else table
    return code_from_name(text, names)


def code_from_name(name: str, table: pd.DataFrame) -> str:
    label = name.strip()
    names = table["name"].astype(str)
    exact = table[names == label]
    chosen = exact if not exact.empty else table[names.str.contains(label, regex=False)]
    if len(chosen) == 1:
        return str(chosen.iloc[0]["code"]).zfill(6)
    if chosen.empty:
        raise ValueError(f"找不到 A 股名称: {label}")
    shown = "、".join(
        f"{row.code} {row.name}" for row in chosen.head(8).itertuples(index=False)
    )
    raise ValueError(f"名称 {label} 匹配到多只股票: {shown}")


def _load_name_table() -> pd.DataFrame:
    import akshare as ak

    return ak.stock_info_a_code_name()


BOOKS = (
    "L1_01_trade-your-way-to-financial-freedom_van-k-tharp.pdf",
    "L1_02_the-new-trading-for-a-living_alexander-elder.pdf",
    "L1_03_the-black-swan_nassim-n-taleb.pdf",
    "L1_04_antifragile_nassim-n-taleb.pdf",
    "L1_05_risk-management-and-financial-institutions_john-c-hull.pdf",
    "L2_06_security-analysis_graham-dodd.pdf",
    "L2_07_the-intelligent-investor_benjamin-graham.pdf",
    "L2_08_berkshire-hathaway-shareholder-letters_warren-buffett.pdf",
    "L2_09_valuation_mckinsey-koller.pdf",
    "L2_10_financial-statement-analysis-and-security-valuation_penman.pdf",
    "L3_11_how-to-make-money-in-stocks_william-j-oneil.pdf",
    "L3_12_technical-analysis-of-the-financial-markets_john-j-murphy.pdf",
    "L3_13_japanese-candlestick-charting-techniques_steve-nison.pdf",
    "L3_14_way-of-the-turtle_curtis-faith.pdf",
    "L3_15_mastering-the-market-cycle_howard-marks.pdf",
    "L4_16_shou-ba-shou-du-cai-bao_tangchao.pdf",
    "L4_17_jia-zhi-tou-zi-shi-zhan-shou-ce_tangchao.pdf",
    "L4_18_tou-zi-zhong-zui-jian-dan-de-shi_qiuguolu.pdf",
)
LOOKBACK_DAYS = 160


def books_dir() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / ".cursor"
        / "skills"
        / "a-share-stock-analysis"
        / "references"
        / "books_pdf"
    )


def missing_books(directory: Path | None = None) -> list[str]:
    folder = books_dir() if directory is None else directory
    present = {path.name for path in folder.glob("*.pdf")} if folder.exists() else set()
    return [name for name in BOOKS if name not in present]


def load_history(symbol: str, asof: date) -> tuple[pd.DataFrame, str | None]:
    from openbb import obb

    frame = obb.akshare.historical(
        symbol=symbol,
        start_date=(asof - timedelta(days=LOOKBACK_DAYS)).isoformat(),
        end_date=asof.isoformat(),
        adjust="",
    ).to_dataframe()
    source = None
    if frame is not None and "source" in frame.columns and not frame.empty:
        source = str(frame["source"].iloc[-1])
    return frame, source


def load_valuation(symbol: str, asof: date) -> dict[str, Any]:
    import akshare as ak

    pe = _latest_indicator(ak, symbol, "市盈率(TTM)", asof)
    pb = _latest_indicator(ak, symbol, "市净率", asof)
    return {
        "pe_ttm": pe[0],
        "pe_percentile": pe[1],
        "pb": pb[0],
        "pb_percentile": pb[1],
        "source": "baidu",
    }


def _latest_indicator(
    ak, symbol: str, indicator: str, asof: date
) -> tuple[float | None, float | None]:
    frame = ak.stock_zh_valuation_baidu(
        symbol=symbol, indicator=indicator, period="近三年"
    )
    if frame is None or frame.empty or "value" not in frame.columns:
        return None, None
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data = data.dropna(subset=["value"])
    data = data[data["date"].dt.date <= asof].sort_values("date")
    if data.empty:
        return None, None
    last = float(data["value"].iloc[-1])
    percentile = None
    if len(data) >= 60:
        percentile = round(float((data["value"] <= last).mean()), 4)
    return round(last, 4), percentile


def build(symbol: str, asof: date, horizon: str) -> dict[str, Any]:
    code = resolve_symbol(symbol)
    history, source = load_history(code, asof)
    valuation = None
    try:
        valuation = load_valuation(code, asof)
    except Exception:
        valuation = None
    absent = missing_books()
    return evaluate(
        history,
        symbol=code,
        asof=asof.isoformat(),
        horizon=horizon,
        valuation=valuation,
        references_ready=not absent,
        missing_books=absent,
        source=source,
        observed_at=now_iso(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="给出一只 A 股的研究用交易计划")
    parser.add_argument(
        "--symbol", required=True, help="6 位 A 股代码，可带 sh/sz/bj 前缀"
    )
    parser.add_argument("--asof", default=None, help="观察日 YYYY-MM-DD，默认今天")
    parser.add_argument(
        "--horizon",
        default="swing",
        choices=("swing", "short", "value"),
        help="swing 波段，short 短线，value 长线，默认 swing",
    )
    args = parser.parse_args(argv)
    asof = date.fromisoformat(args.asof) if args.asof else date.today()
    try:
        payload = build(args.symbol, asof, args.horizon)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except KeyError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
