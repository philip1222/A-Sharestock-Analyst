#!/usr/bin/env python3
"""Run the mandatory 18-book plus double-breakout recommendation workflow."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.a_share_recommender.adapters import (  # noqa: E402
    AkshareMarketDataProvider,
    ResearchBookStrategyProvider,
)
from tools.a_share_recommender.double_breakout import DoubleBreakoutMatcher  # noqa: E402
from tools.a_share_recommender.pipeline import RecommendationPipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the bound 18-book and double-breakout workflow."
    )
    parser.add_argument(
        "--book-candidate",
        action="append",
        default=[],
        help="Candidate selected by the 18-book stage; repeat for multiple stocks",
    )
    parser.add_argument("--sector", help="Optional Eastmoney industry-board name")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Analysis date in YYYY-MM-DD",
    )
    parser.add_argument(
        "--horizon",
        choices=("short", "swing", "value"),
        default="swing",
        help="18-book strategy horizon",
    )
    parser.add_argument(
        "--minimum-fit", type=float, default=75.0, help="Minimum template score"
    )
    parser.add_argument(
        "--max-universe",
        type=int,
        default=50,
        help="Maximum recent limit-up symbols scanned in the fallback route",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import akshare as ak

    books = ResearchBookStrategyProvider(
        args.book_candidate,
        as_of=args.as_of,
        horizon=args.horizon,
    )
    market = AkshareMarketDataProvider(
        ak,
        as_of=args.as_of,
        max_universe=args.max_universe,
    )
    matcher = DoubleBreakoutMatcher.from_template(
        PROJECT_ROOT / "tools" / "strategy_templates" / "yin_yang_double_breakout.json"
    )
    pipeline = RecommendationPipeline(
        market,
        books,
        matcher,
        minimum_fit_score=args.minimum_fit,
    )
    payload = pipeline.run(sector=args.sector).to_dict()
    payload["as_of"] = args.as_of.isoformat()
    payload["data_sources"] = ["AKShare", "research.strategy 18-book rules"]
    payload["disclaimer"] = (
        "研究用选股与价位测算，不构成下单指令，也不代表应当买入或卖出。"
    )
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        destination = args.output.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"{output}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
