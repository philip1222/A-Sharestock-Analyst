#!/usr/bin/env python3
"""A small, agent-friendly entry point for common A-share lookups.

The script resolves the repository root from its own location, so it works when
called from Codex, Cursor, or Grok regardless of the terminal's current folder.
It does not place orders or make investment recommendations.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(
        description="Query A-share historical prices, latest quote, or company info."
    )
    parser.add_argument(
        "mode", choices=("history", "quote", "info"), help="Data to retrieve"
    )
    parser.add_argument("--symbol", required=True, help="Six-digit A-share code, e.g. 000001")
    parser.add_argument(
        "--start",
        default=(today - timedelta(days=30)).strftime("%Y%m%d"),
        help="Start date in YYYYMMDD (history only; default: 30 days ago)",
    )
    parser.add_argument(
        "--end",
        default=today.strftime("%Y%m%d"),
        help="End date in YYYYMMDD (history only; default: today)",
    )
    parser.add_argument(
        "--period",
        choices=("daily", "weekly", "monthly"),
        default="daily",
        help="K-line period (history only)",
    )
    parser.add_argument(
        "--adjust",
        choices=("", "qfq", "hfq"),
        default="qfq",
        help="Price adjustment: qfq, hfq, or empty string for none (history only)",
    )
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    return parser.parse_args()


def validate_symbol(symbol: str) -> str:
    if not (len(symbol) == 6 and symbol.isdigit()):
        raise ValueError("--symbol must be a six-digit A-share code, for example 000001.")
    return symbol


def load_akshare():
    if sys.version_info < (3, 11):
        raise RuntimeError(
            f"Python 3.11+ is required; current interpreter is {sys.version.split()[0]}. "
            "Create .venv with Python 3.11+ and run this script with .venv/bin/python."
        )
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        import akshare as ak
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "AKShare dependencies are not installed. Create the project's .venv, then install it with "
            "python -m pip install -e ."
        ) from exc
    return ak


def main() -> int:
    args = parse_args()
    symbol = validate_symbol(args.symbol)
    ak = load_akshare()

    if args.mode == "history":
        frame = ak.stock_zh_a_hist(
            symbol=symbol,
            period=args.period,
            start_date=args.start,
            end_date=args.end,
            adjust=args.adjust,
        )
    elif args.mode == "quote":
        frame = ak.stock_zh_a_spot_em()
        frame = frame.loc[frame["代码"].astype(str).str.zfill(6) == symbol]
    else:
        frame = ak.stock_individual_info_em(symbol=symbol)

    if frame.empty:
        print("No data returned. Verify the code, dates, market session, and data-source availability.")
        return 2

    print(frame.to_string(index=False))
    if args.csv:
        destination = args.csv.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(destination, index=False, encoding="utf-8-sig")
        print(f"\nSaved CSV: {destination}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
