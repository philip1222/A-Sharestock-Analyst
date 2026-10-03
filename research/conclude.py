#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""研究结论入口。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from research.registry import FACTORS, get_model
from research.symbols import bare_symbol
from research.types import FactorContext


def build(symbol: str, asof: date, model_name: str) -> dict:
    code = bare_symbol(symbol)
    ctx = FactorContext(symbol=code, asof=asof)
    results = [factor.evaluate(ctx) for factor in FACTORS]
    model = get_model(model_name)
    return model.run(code, asof.isoformat(), results).as_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="汇总跨市场因子，输出一只 A 股的研究结论"
    )
    parser.add_argument(
        "--symbol", required=True, help="6 位 A 股代码，可带 sh/sz/bj 前缀"
    )
    parser.add_argument("--model", default="rules_v1", help="模型名，默认 rules_v1")
    parser.add_argument("--asof", default=None, help="观察日 YYYY-MM-DD，默认今天")
    args = parser.parse_args(argv)
    asof = date.fromisoformat(args.asof) if args.asof else date.today()
    try:
        payload = build(args.symbol, asof, args.model)
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
